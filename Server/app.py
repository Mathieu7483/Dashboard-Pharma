from flask import Flask
from flask_restx import Api
from flask_cors import CORS
from config import DevelopmentConfig
from database.data_manager import db, bcrypt, jwt
from utils.seeder import seed_all_initial_data
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()
basedir = os.path.abspath(os.path.dirname(__file__))
database = os.path.join(basedir, 'database')

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configuration JWT
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=30)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(database, 'database.sqlite')

    # --- Extensions ---
    CORS(app)
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # --- Initialization Flask-RESTX ---
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

    # --- Import & Register Namespaces ---
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

    api.add_namespace(auth_ns, path='/auth')
    api.add_namespace(products_ns, path='/products')
    api.add_namespace(sales_ns, path='/sales')
    api.add_namespace(users_ns, path='/users')
    api.add_namespace(doctors_ns, path='/doctors')
    api.add_namespace(clients_ns, path='/clients')
    api.add_namespace(analytics_ns, path='/analytics')
    api.add_namespace(chatbot_ns, path='/chatbot')
    api.add_namespace(inventory_ns, path='/inventory')
    api.add_namespace(tickets_ns, path='/tickets')


    # --- Models Import pour SQLAlchemy ---
    with app.app_context():
        from models import user, product, sale, client, doctor, interaction, product_alias

    return app

# --- EXECUTION ---
if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        print("--- Database Initialization ---")
        db.create_all() 
        seed_all_initial_data()

    print("\n--- Starting Pharma Server ---")
    print("Documentation: http://127.0.0.1:5000/docs")
    
    app.run(debug=True, port=5000)