from flask import Flask
from flask_restx import Api
from flask_cors import CORS
from config import DevelopmentConfig
from database.data_manager import db, bcrypt, jwt
from utils.seeder import seed_all_initial_data

# Authentication configuration for Swagger UI
authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization'
    }
}

# 1. Global API initialization
# The 'doc' parameter sets the Swagger UI path
api = Api(
    title='Pharma Dashboard API',
    version='1.0',
    description='API for Pharma Dashboard Application',
    doc='/docs',
    authorizations=authorizations,
    security='apikey' # Applies to all endpoints unless overridden
)

def create_app(config_class=DevelopmentConfig):
    """
    Application Factory: Initializes the Flask app, extensions, 
    and registers all API namespaces.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # --- Enable CORS ---
    # Essential to allow your HTML/JS frontend to talk to this Python backend
    CORS(app)

    # --- Initialize Extensions ---
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    
    # 2. IMPORT NAMESPACES
    # Using local imports inside the factory to avoid circular dependencies
    from api.users import users_ns 
    from api.products import products_ns
    from api.sales import sales_ns
    from api.auth import auth_ns
    from api.doctors import doctors_ns
    from api.clients import clients_ns
    from api.analytics import analytics_ns
    from api.chatbot import ns as chatbot_ns # Importing your chatbot namespace
    from api.inventory import inventory_ns
    
    # 3. REGISTER NAMESPACES
    # Resetting the list prevents duplicates during development hot-reloads
    api.namespaces = [] 

    api.add_namespace(auth_ns, path='/auth')
    api.add_namespace(products_ns, path='/products')
    api.add_namespace(sales_ns, path='/sales')
    api.add_namespace(users_ns, path='/users')
    api.add_namespace(doctors_ns, path='/doctors')
    api.add_namespace(clients_ns, path='/clients')
    api.add_namespace(analytics_ns, path='/analytics')
    api.add_namespace(chatbot_ns, path='/chatbot') # Registering chatbot namespace
    api.add_namespace(inventory_ns, path='/inventory')

    # 4. BIND API TO APP INSTANCE
    api.init_app(app)

    # 5. IMPORT MODELS
    # Ensures SQLAlchemy maps classes to database tables correctly
    from models import user, product, sale, client, doctor

    return app

# --- MAIN EXECUTION BLOCK ---
if __name__ == '__main__':
    # Create the Flask application instance
    app = create_app()
    
    # Use application context for database operations
    with app.app_context():
        print("--- Database Initialization ---")
        # Creates tables if they do not exist
        db.create_all() 
        
        # Populates the database with initial data
        seed_all_initial_data()

    print("\n--- Starting Pharma Server ---")
    print("Documentation: http://127.0.0.1:5000/docs")
    
    # Run the development server
    app.run(debug=True, port=5000)