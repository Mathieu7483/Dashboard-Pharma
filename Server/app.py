<<<<<<< HEAD
import os
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask
from flask_restx import Api
from flask_cors import CORS

# Local imports
from config import DevelopmentConfig
from database.data_manager import db, bcrypt, jwt
from utils.seeder import seed_all_initial_data

# Load environment variables
load_dotenv()

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # --- Configuration Path & Database ---
    basedir = os.path.abspath(os.path.dirname(__file__))
    database_dir = os.path.join(basedir, 'database')
    
    # Ensure database directory exists
    if not os.path.exists(database_dir):
        os.makedirs(database_dir)

    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=30)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL', 
        'sqlite:///' + os.path.join(database_dir, 'database.sqlite')
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- Extensions Initialization ---
    CORS(app)
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # --- Flask-RESTX Setup ---
    authorizations = {
        'apikey': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization'
        }
    }

    api = Api(
        app,
        title='Pharma Dashboard API',
        version='1.0',
        description='API for Pharma Dashboard Application',
        doc='/docs',
        authorizations=authorizations,
        security='apikey'
    )

    # --- Register Namespaces ---
    from api.users import users_ns 
    from api.products import products_ns
    from api.sales import sales_ns
    from api.auth import auth_ns
    from api.doctors import doctors_ns
    from api.clients import clients_ns
    from api.analytics import analytics_ns
    from api.chatbot import ns as chatbot_ns
    from api.inventory import inventory_ns
    from api.tickets import tickets_ns
    from api.calendar_events import calendar_ns

    api.add_namespace(auth_ns, path='/auth')
    api.add_namespace(users_ns, path='/users')
    api.add_namespace(products_ns, path='/products')
    api.add_namespace(sales_ns, path='/sales')
    api.add_namespace(doctors_ns, path='/doctors')
    api.add_namespace(clients_ns, path='/clients')
    api.add_namespace(analytics_ns, path='/analytics')
    api.add_namespace(chatbot_ns, path='/chatbot')
    api.add_namespace(inventory_ns, path='/inventory')
    api.add_namespace(tickets_ns, path='/tickets')
    api.add_namespace(calendar_ns, path='/calendar')

    # --- Critical Models Import for SQLAlchemy Registry ---
    with app.app_context():
        # Import all models to ensure relationships are mapped correctly
        from models import (
            user, product, sale, client, doctor, interaction, product_alias, calendar
        )

    return app

# --- Execution Entry Point ---
if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        print("\n--- 🔧 Database Initialization ---")
        db.create_all() 
        
        print("--- 🌱 Global Seeding Process ---")
        try:
            seed_all_initial_data()
            print("✅ Seeding completed successfully.")
        except Exception as e:
            print(f"❌ Seeding failed: {str(e)}")

    print("\n--- 🚀 Starting Pharma Server ---")
    print("Documentation: http://127.0.0.1:5000/docs")
    
    app.run(debug=True, port=5000)
=======
from flask import Flask
from config import DevelopmentConfig
from flask_restx import Api
from database.data_manager import db, bcrypt, jwt 

# Initialize the Flask-RESTx API instance globally
api = Api(title='Pharma Dashboard API', version='1.0', description='API for Pharma Dashboard Application')

def create_app():
    """
    Application Factory Pattern: Initializes and configures the Flask application.
    """
    app = Flask(__name__)
    # Load configuration from the specified object (e.g., DevelopmentConfig)
    app.config.from_object(DevelopmentConfig)

    # --- Initialize Extensions ---
    # Bind extensions to the application instance
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    api.init_app(app)

    # --- Register Models and Namespaces ---
    
    # IMPORT MODELS: Ensures all SQLAlchemy model classes are loaded into memory 
    # before db.create_all() is called, allowing SQLAlchemy to map them to tables.
    from models import basemodel, user, product, sale 
 
    # Import API Namespaces (Endpoints)
    from api.users import user_ns
    from api.products import products_ns
    from api.sales import sale_ns
    from api.auth import auth_ns
    
    # Register Namespaces with the API (Defines the base path for each module)
    api.add_namespace(auth_ns, path='/auth')
    api.add_namespace(products_ns, path='/products')
    api.add_namespace(sale_ns, path='/sales')
    api.add_namespace(user_ns, path='/users')

    return app


if __name__ == '__main__':
    # Create the application instance
    app = create_app()
    
    # Push the application context before interacting with extensions (like SQLAlchemy)
    with app.app_context():
        # Create database tables if they do not exist
        db.create_all() 

    app.run(debug=True)
>>>>>>> main
