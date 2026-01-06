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
    'reply': fields.String(description='The formatted data report or error message')
})

# --- ROUTES ---
@ns.route('/')
class ChatbotQuery(Resource):
    
    @ns.doc('process_chat_query')
    @ns.expect(chat_input_model)
    @ns.marshal_with(chat_output_model, code=200)
    @jwt_required() # Authentication required for chatbot usage
    def post(self):
        data = ns.payload
        user_msg = data.get('message')
        
        # 1. Capture the engine's output
        reply = bot_engine.process_query(user_msg)
        
        # 2. PRINT IN YOUR TERMINAL (Watch the black window!)
        print(f"\n--- DEBUG CHATBOT ---")
        print(f"User Message: {user_msg}")
        print(f"Engine Output: {reply}")
        print(f"----------------------\n")

        # 3. Ensure we return a string under the 'reply' key
        return {'reply': str(reply)}, 200