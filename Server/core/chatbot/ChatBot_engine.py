from sqlalchemy import inspect, or_
from database.data_manager import db
from models.product import ProductModel
from models.client import ClientModel
from models.doctor import DoctorModel
from core.chatbot.NLUProcessor import NLUProcessor

class ChatBotEngine:
    """
    Core engine that manages the workflow: NLU analysis -> DB Search -> Result Formatting.
    """

    def __init__(self):
        self.nlu = NLUProcessor()
        # Map intents to their corresponding SQLAlchemy models
        self.models = {
            "get_product": ProductModel,
            "get_client": ClientModel,
            "get_doctor": DoctorModel
        }

    def process_query(self, user_text):
        """
        Coordinates the search and handles the smart fallback logic.
        """
        analysis = self.nlu.analyze(user_text)
        intent = analysis.get("intent")
        entity = analysis.get("entity")

        if not entity:
            return "❓ **Please specify a name.** (e.g., 'Search Doliprane' or 'Find Dr. Martin')"

        # 1. Primary search based on NLU intent
        primary_model = self.models.get(intent)
        results = self._search_database(primary_model, entity)

        # 2. SMART FALLBACK: If no results, loop through other models to find a match
        if not results:
            for model_key, model_class in self.models.items():
                if model_class == primary_model:
                    continue # Skip the one we already searched
                
                results = self._search_database(model_class, entity)
                if results:
                    intent = model_key # Update intent for correct formatting
                    break

        return self._format_results(results, intent)

    def _search_database(self, model, search_term):
        """
        Performs a database query using the ILIKE operator for flexible matching.
        """
        if model == ProductModel:
            # Products are usually searched by name only
            condition = model.name.ilike(f"%{search_term}%")
        else:
            # Clients and Doctors search across first AND last names
            condition = or_(
                model.last_name.ilike(f"%{search_term}%"),
                model.first_name.ilike(f"%{search_term}%")
            )
        
        query = db.select(model).where(condition)
        return db.session.execute(query).scalars().all()

    def _format_results(self, records, intent):
        """
        Formats SQLAlchemy records into a professional Markdown report.
        Limits the output to the first 3 results to avoid information overload.
        """
        if not records:
            category = intent.split('_')[1]
            return f"❌ **No results found** for '{category}'. Please try a different spelling."

        search_type = intent.split('_')[1].upper()
        total_found = len(records)
        
        # Limit to the first 3 matches
        display_limit = 3
        to_display = records[:display_limit]

        output = [f"## 📋 Results: {search_type}"]
        
        # Inform the user about the total count
        if total_found > 1:
            output.append(f"I found **{total_found}** matches. Showing the first {len(to_display)}:\n")
        else:
            output.append(f"Found **1** exact match:\n")
        
        for record in to_display:
            # Determine display title (Full Name or Product Name)
            title = getattr(record, 'name', 
                    f"{getattr(record, 'first_name', '')} {getattr(record, 'last_name', '')}".strip())
            
            output.append(f"### 🔹 {title}")
            output.append("---")
            
            # Introspect model columns
            mapper = inspect(record).mapper
            for column in mapper.attrs:
                key = column.key
                value = getattr(record, key)

                # Security & Cleanliness: Fields to skip
                excluded_fields = ['password_hash', 'id', 'user_id', 'created_at', 'updated_at']
                if key in excluded_fields or key.endswith('_entries'):
                    continue

                label = key.replace('_', ' ').capitalize()
                
                # Intelligent value styling
                if value is None or value == "": 
                    val_str = "*Not provided*"
                elif isinstance(value, float): 
                    val_str = f"{value:.2f} €" if "price" in key else f"{value:.2f}"
                elif isinstance(value, bool): 
                    val_str = "✅ Yes" if value else "❌ No"
                else: 
                    val_str = str(value)

                output.append(f"**{label}**: {val_str}")
            output.append("\n") # Space between cards

        # If there are more results than displayed, add a footer note
        if total_found > display_limit:
            output.append(f"⚠️ *Note: {total_found - display_limit} other results exist. Please be more specific if you haven't found the right one.*")

        return "\n".join(output)