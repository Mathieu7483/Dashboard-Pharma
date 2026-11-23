import os
from dotenv import load_dotenv

# Must run BEFORE importing config: config.py reads the environment at import time.
load_dotenv()

from flask import Flask, send_from_directory
from flask_restx import Api, Resource
from flask_cors import CORS
from config import get_config
from database.data_manager import db, bcrypt, jwt


def create_app(config_class=None):
    config_class = config_class or get_config()
    if hasattr(config_class, 'validate'):
        config_class.validate()

    app = Flask(__name__)
    app.config.from_object(config_class)
    basedir     = os.path.abspath(os.path.dirname(__file__))
    database_dir = os.path.join(basedir, 'database')
    client_dir   = os.path.join(basedir, '..', 'Client')
    
    if not os.path.exists(database_dir):
        os.makedirs(database_dir)
        
    # Secrets, JWT lifetime and DB URI all come from config.py (environment variables).
    # Only fall back to the local SQLite file when no DATABASE_URL is provided.
    app.config.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:///' + os.path.join(database_dir, 'database.sqlite'))

    origins = app.config.get('CORS_ORIGINS')
    if origins:
        CORS(app, origins=origins)
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    @app.route('/')
    def root_redirect():
        return send_from_directory(client_dir, 'auth.html')

    @app.route('/<path:filename>')
    def serve_client_files(filename):
        return send_from_directory(client_dir, filename)

    authorizations = {
        'apikey': {'type': 'apiKey', 'in': 'header', 'name': 'Authorization'}
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
    
    from api.users         import users_ns
    from api.products      import products_ns
    from api.sales         import sales_ns
    from api.auth          import auth_ns
    from api.doctors       import doctors_ns
    from api.clients       import clients_ns
    from api.analytics     import analytics_ns
    from api.chatbot       import ns as chatbot_ns
    from api.inventory     import inventory_ns
    from api.notes         import notes_ns
    from api.tickets       import tickets_ns
    from api.calendar_events import calendar_ns
    from api.specialites   import specialites_ns
    
    api.add_namespace(auth_ns,        path='/auth')
    api.add_namespace(users_ns,       path='/users')
    api.add_namespace(products_ns,    path='/products')
    api.add_namespace(sales_ns,       path='/sales')
    api.add_namespace(doctors_ns,     path='/doctors')
    api.add_namespace(clients_ns,     path='/clients')
    api.add_namespace(analytics_ns,   path='/analytics')
    api.add_namespace(chatbot_ns,     path='/chatbot')
    api.add_namespace(inventory_ns,   path='/inventory')
    api.add_namespace(notes_ns,       path='/notes')
    api.add_namespace(tickets_ns,     path='/tickets')
    api.add_namespace(calendar_ns,    path='/calendar')
    api.add_namespace(specialites_ns, path='/specialites')
    
    with app.app_context():
        from models import (
            user, product, sale, client, doctor,
            interaction, calendar, ticket,
            specialite, composition, interaction_ansm, cip,
        )

    return app