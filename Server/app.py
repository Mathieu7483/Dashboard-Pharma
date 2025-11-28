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