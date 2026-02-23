from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from core.chatbot.ChatBot_engine import ChatBotEngine
import logging

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
        """Process a natural language query and return a report."""
        data = ns.payload
        user_msg = data.get('message')
        current_user_id = get_jwt_identity()

        if not user_msg:
            ns.abort(400, message="Message content is required.")

        try:
            # ID of user is passed to the engine for personalized responses and logging
            result = bot_engine.process_query(user_msg, user_id=current_user_id)
            
            # Logging the detected intent for monitoring and debugging purposes
            logging.info(f"Chatbot - User {current_user_id} - Intent: {result.get('intent')}")
            
            return result, 200

        except Exception as e:
            logging.error(f"Chatbot Engine Error: {str(e)}", exc_info=True)
            return {
                "reply": "Désolé, j'ai rencontré une difficulté technique pour analyser votre demande.",
                "intent": "error"
            }, 500