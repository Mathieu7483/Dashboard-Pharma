from sqlalchemy import inspect, or_
from database.data_manager import db
from models.product import ProductModel
from models.client import ClientModel
from models.doctor import DoctorModel
from models.sale import SaleModel
from models.interaction import InteractionModel
from core.chatbot.NLUProcessor import NLUProcessor

class ChatBotEngine:
    """
    Core engine that orchestrates the chatbot logic:
    Analysis (NLU) -> Routing -> Database Query -> Markdown Formatting.
    """

    def __init__(self):
        self.nlu = NLUProcessor()
        # Model mapping for standard search intents
        self.search_models = {
            "get_product": ProductModel,
            "get_client": ClientModel,
            "get_doctor": DoctorModel
        }

    def process_query(self, user_text):
        """
        Main entry point for processing user messages.
        """
        analysis = self.nlu.analyze(user_text)
        intent = analysis.get("intent")
        
        # We now prioritize the list of entities found by the NLU
        entities = analysis.get("entity_list", [])

        # 1. SPECIALIZED HANDLERS (Non-standard search)
        if intent == "get_stock_alerts":
            return self._handle_stock_alerts()
        
        if intent == "get_sales_summary":
            return self._handle_sales_summary()
        
        if intent == "check_interaction":
            return self._handle_interaction_check(entities)

        # 2. STANDARD SEARCH LOGIC
        if not entities:
            return "❓ **Please specify a name.** (e.g., 'Search Advil' or 'Show sales')"

        # We use the first found entity for standard search
        return self._execute_standard_search(intent, entities[0])

    def _execute_standard_search(self, intent, main_entity):
        """
        Performs a database search based on the detected intent, 
        with a fallback system to other models.
        """
        primary_model = self.search_models.get(intent)
        results = self._search_database(primary_model, main_entity)

        # Smart Fallback: If no results in the primary category, check others
        if not results:
            for model_key, model_class in self.search_models.items():
                if model_class == primary_model:
                    continue
                results = self._search_database(model_class, main_entity)
                if results:
                    intent = model_key
                    break

        return self._format_results(results, intent)

    def _search_database(self, model, search_term):
        """
        Executes a SQL query using ILIKE for flexible matching.
        """
        if not model: return []
        
        if model == ProductModel:
            condition = model.name.ilike(f"%{search_term}%")
        else:
            condition = or_(
                model.last_name.ilike(f"%{search_term}%"),
                model.first_name.ilike(f"%{search_term}%")
            )
        
        query = db.select(model).where(condition)
        return db.session.execute(query).scalars().all()

    def _handle_interaction_check(self, entity_list):
        """
        Logic for checking drug-drug interactions via active ingredients.
        Uses the InteractionModel table.
        """
        if len(entity_list) < 2:
            return "⚠️ **Please mention at least two products** to verify compatibility."

        # 1. Resolve product names to active ingredients
        resolved_ingredients = []
        found_names = []
        
        for name in entity_list:
            # We search the Product table to find the molecule
            product = db.session.execute(
                db.select(ProductModel).where(ProductModel.name.ilike(f"%{name}%"))
            ).scalar()
            
            if product:
                resolved_ingredients.append(product.active_ingredient)
                found_names.append(product.name)
            else:
                # If not in Product table, assume the user typed the ingredient directly
                resolved_ingredients.append(name.capitalize())
                found_names.append(name.capitalize())

        # 2. Query the interactions table for pairs (Direction A->B or B->A)
        query = db.select(InteractionModel).where(
            or_(
                (InteractionModel.ingredient_a.in_(resolved_ingredients)) & 
                (InteractionModel.ingredient_b.in_(resolved_ingredients)),
                (InteractionModel.ingredient_b.in_(resolved_ingredients)) & 
                (InteractionModel.ingredient_a.in_(resolved_ingredients))
            )
        )
        
        conflicts = db.session.execute(query).scalars().all()

        if not conflicts:
            return f"✅ **No known interactions** found between **{', '.join(found_names)}**."

        # 3. Format the danger report
        output = [f"## 🚨 DRUG INTERACTION WARNING"]
        output.append(f"Analysis for: **{', '.join(found_names)}**\n")
        
        for c in conflicts:
            output.append(f"### ⚠️ Conflict: {c.ingredient_a} + {c.ingredient_b}")
            output.append(f"**Severity**: {c.severity}")
            output.append(f"**Clinical Note**: {c.description}")
            output.append("---")

        return "\n".join(output)

    def _handle_stock_alerts(self):
        """
        Reports products with low stock levels (< 10).
        """
        threshold = 10
        query = db.select(ProductModel).where(ProductModel.stock < threshold)
        results = db.session.execute(query).scalars().all()
        
        if not results:
            return "✅ **All stock levels are correct.**"
        
        output = [f"## ⚠️ Low Stock Alerts (< {threshold})"]
        for p in results:
            output.append(f"- **{p.name}**: {p.stock} units (Ingredient: {p.active_ingredient})")
        return "\n".join(output)

    def _handle_sales_summary(self):
        """
        Returns a high-level summary of store revenue.
        """
        sales = db.session.execute(db.select(SaleModel)).scalars().all()
        if not sales:
            return "📊 **No sales data available yet.**"
            
        total = sum(s.total_price for s in sales if s.total_price)
        return (f"## 📈 Sales Performance\n"
                f"- **Total Sales**: {len(sales)}\n"
                f"- **Cumulative Revenue**: {total:.2f} €")

    def _format_results(self, records, intent):
        """
        Converts SQLAlchemy records into structured Markdown cards.
        """
        if not records:
            return "❌ **No matches found.** Please check the spelling."

        search_type = intent.split('_')[1].upper() if '_' in intent else "INFO"
        output = [f"## 📋 Results: {search_type}"]
        
        for record in records[:3]: # Security limit
            title = getattr(record, 'name', 
                    f"{getattr(record, 'first_name', '')} {getattr(record, 'last_name', '')}".strip())
            
            output.append(f"### 🔹 {title}")
            output.append("---")
            
            mapper = inspect(record).mapper
            for column in mapper.attrs:
                key = column.key
                if key in ['id', 'user_id', 'password_hash'] or key.endswith('_entries'):
                    continue
                
                val = getattr(record, key)
                if isinstance(val, float): val = f"{val:.2f} €" if "price" in key else f"{val:.2f}"
                elif isinstance(val, bool): val = "✅ Yes" if val else "❌ No"
                elif val is None: val = "N/A"
                
                output.append(f"**{key.replace('_', ' ').capitalize()}**: {val}")
            output.append("\n")

        return "\n".join(output)