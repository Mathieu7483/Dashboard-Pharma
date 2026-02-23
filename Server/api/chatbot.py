from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required
from core.chatbot.ChatBot_engine import ChatBotEngine

# --- NAMESPACE INITIALIZATION ---
# Using 'ns' to maintain compatibility with the existing app.py import logic
ns = Namespace('chatbot', description="AI-powered pharmacy assistant operations")

# Global engine instance to handle NLU processing and database lookups
bot_engine = ChatBotEngine()

# --- API MODELS ---
# Input model defining the structure for the user's natural language message
chat_input_model = ns.model('ChatInput', {
    'message': fields.String(required=True, description='The user natural language query')
})

# Output model for the bot's detailed response
chat_output_model = ns.model('ChatOutput', {
    'reply': fields.String(description='The formatted data report or error message'),
    'intent': fields.String(description='The detected NLU intent')
})

# --- ROUTES ---
@ns.route('/')
class ChatbotQuery(Resource):
    
    @ns.doc('process_chat_query')
    @ns.expect(chat_input_model)
    @ns.marshal_with(chat_output_model, code=200)
    @jwt_required()
    def post(self):
        data = ns.payload
        user_msg = data.get('message')
  
        result = bot_engine.process_query(user_msg)
        
        # Debug console
        print(f"\n--- DEBUG CHATBOT ---")
        print(f"Result: {result}")
        print(f"----------------------\n")


        return result, 200