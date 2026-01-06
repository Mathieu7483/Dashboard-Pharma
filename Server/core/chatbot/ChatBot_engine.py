from sqlalchemy import inspect, or_
from database.data_manager import db
from models.product import ProductModel
from models.client import ClientModel
from models.doctor import DoctorModel
from core.chatbot.NLUProcessor import NLUProcessor

class ChatBotEngine:
    """
    Core engine that coordinates the NLU analysis and database retrieval 
    to provide professional formatted reports.
    """

    def __init__(self):
        self.nlu = NLUProcessor()
        # Mapping intents to SQLAlchemy models
        self.model_mapping = {
            "get_product": ProductModel,
            "get_client": ClientModel,
            "get_doctor": DoctorModel
        }

    def process_query(self, user_text):
        """
        Main entry point: analyzes text, and attempts cascaded search if needed.
        """
        analysis = self.nlu.analyze(user_text)
        intent = analysis.get("intent")
        entity = analysis.get("entity")

        if not entity:
            return "❓ **Please specify a name.** I can look for products, clients, or doctors."

        # 1. Initial attempt with detected intent
        model = self.model_mapping.get(intent)
        results = self._search_database(model, entity)

        # 2. SMART FALLBACK: If nothing found, try other tables automatically
        if not results:
            # If we looked for a product and found nothing, try Clients
            if intent == "get_product":
                results = self._search_database(ClientModel, entity)
                if results:
                    intent = "get_client"
                else:
                    # Still nothing? Try Doctors
                    results = self._search_database(DoctorModel, entity)
                    if results:
                        intent = "get_doctor"

        return self._format_results(results, intent)

    def _search_database(self, model, search_term):
        """
        Performs a flexible search across relevant columns (Name, Last Name, First Name).
        """
        if model == ProductModel:
            # Products only use the 'name' column
            condition = model.name.ilike(f"%{search_term}%")
        else:
            # Clients and Doctors search in BOTH first and last names
            condition = or_(
                model.last_name.ilike(f"%{search_term}%"),
                model.first_name.ilike(f"%{search_term}%")
            )

        query = db.select(model).where(condition)
        return db.session.execute(query).scalars().all()

    def _format_results(self, records, intent):
        """
        Translates SQLAlchemy objects into professional Markdown cards.
        """
        if not records:
            return f"❌ **No records found** for this {intent.split('_')[1]} search. Try a different spelling."

        # Professional Header
        search_type = intent.split('_')[1].upper()
        output = [f"## 📋 Search Results for '{search_type}'\n"]
        output.append(f"Found **{len(records)}** entry(ies).\n")
        
        for record in records:
            # Determine card title based on available attributes
            title = getattr(record, 'name', 
                    f"{getattr(record, 'first_name', '')} {getattr(record, 'last_name', '')}".strip())
            
            output.append(f"### 🔹 {record.__class__.__name__}: {title}")
            output.append("---")
            
            # Inspect all columns of the model
            mapper = inspect(record).mapper
            for column in mapper.attrs:
                key = column.key
                value = getattr(record, key)

                # Skip sensitive or irrelevant technical fields
                if key in ['password_hash', 'id', 'user_id', 'created_at', 'user', 'sales_entries']:
                    continue

                # Clean label formatting
                label = key.replace('_', ' ').capitalize()
                
                # Intelligent value styling
                if value is None:
                    val_str = "*Not provided*"
                elif isinstance(value, float):
                    val_str = f"{value:.2f} €" if "price" in key else f"{value:.2f}"
                elif isinstance(value, bool):
                    val_str = "✅ Yes" if value else "❌ No"
                else:
                    val_str = str(value)

                output.append(f"**{label}**: {val_str}")
            
            output.append("\n") # Spacer between results

        return "\n".join(output)