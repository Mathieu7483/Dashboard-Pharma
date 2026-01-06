import spacy
from sqlalchemy import inspect
from database.data_manager import db
from models.product import ProductModel
from models.client import ClientModel
from models.doctor import DoctorModel
from core.chatbot.NLUProcessor import NLUProcessor

class ChatBotEngine:
    """
    Main Engine for the Chatbot handling the flow between Natural Language 
    Understanding (NLU) and Database queries.
    """

    def __init__(self):
        # Initialize the NLU processor (ensure spacy model is downloaded)
        self.nlu = NLUProcessor()
        # Mapping intents to their respective SQLAlchemy models
        self.model_mapping = {
            "get_product": ProductModel,
            "get_client": ClientModel,
            "get_doctor": DoctorModel
        }

    def process_query(self, user_text):
        """
        Main entry point: analyzes the text, searches the DB, and formats the report.
        """
        # 1. Extract intent and entities from the NLU
        analysis = self.nlu.analyze(user_text)
        intent = analysis.get("intent")
        entity = analysis.get("entity")

        if intent == "unknown" or not entity:
            return "I'm sorry, I couldn't understand your request. Please specify a product, client, or doctor name."

        # 2. Execute search based on the identified intent
        model = self.model_mapping.get(intent)
        if not model:
            return f"Intent '{intent}' is recognized but not yet implemented in the engine."

        results = self._search_database(model, entity)

        # 3. Format and return the detailed report
        return self._format_results(results, intent)

    def _search_database(self, model, search_term):
        """
        Performs a fuzzy search using ILIKE on the 'name' or 'last_name' columns.
        """
        # We determine which column to search based on the model type
        if model == ProductModel:
            column = model.name
        else:
            column = model.last_name

        # Execute query using SQLAlchemy 2.0 syntax
        query = db.select(model).where(column.ilike(f"%{search_term}%"))
        return db.session.execute(query).scalars().all()

    def _format_results(self, records, intent):
        """
        Formats database records into a highly readable professional report.
        """
        if not records:
            return "❌ **No records found.** Please check the spelling or try another name."

        # Header with a professional touch
        output = [f"## 📋 Search Results for '{intent.split('_')[1].upper()}'\n"]
        output.append(f"Found **{len(records)}** matching entry(ies).\n")
        
        for record in records:
            # Header for each card
            output.append(f"### 🔹 {record.__class__.__name__}: {getattr(record, 'name', getattr(record, 'last_name', 'Unnamed'))}")
            output.append("---")
            
            mapper = inspect(record).mapper
            for column in mapper.attrs:
                key = column.key
                value = getattr(record, key)

                # 1. Skip technical and relationship fields
                if key in ['password_hash', 'id', 'user_id', 'created_at', 'user', 'sales_entries']:
                    continue

                # 2. Pretty labels
                label = key.replace('_', ' ').capitalize()
                
                # 3. Intelligent Value Formatting
                if value is None:
                    val_str = "N/A"
                elif isinstance(value, float):
                    val_str = f"{value:.2f} €" if "price" in key else f"{value:.2f}"
                elif isinstance(value, bool):
                    val_str = "✅ Yes" if value else "❌ No"
                else:
                    val_str = str(value)

                output.append(f"**{label}**: {val_str}")
            
            output.append("\n") # Space between cards

        return "\n".join(output)