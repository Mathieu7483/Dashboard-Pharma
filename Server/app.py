from flask import Flask
from config import DevelopmentConfig
from flask_restx import Api

from database.data_manager import db, bcrypt, jwt 

api = Api(title='Pharma Dashboard API', version='1.0', description='API for Pharma Dashboard Application')

def create_app():
    app = Flask(__name__)
    app.config.from_object(DevelopmentConfig)

    # Initialize extensions 
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    api.init_app(app)

    # --- ENREGISTREMENT DES MODÈLES ET NAMESPACES ---
    from models import basemodel, user, product, sale 
  
    from api.users import user_ns
    from api.products import product_ns
    from api.sales import sale_ns
    from api.auth import auth_ns
    api.add_namespace(auth_ns, path='/auth')
    api.add_namespace(product_ns, path='/products')
    api.add_namespace(sale_ns, path='/sales')
    api.add_namespace(user_ns, path='/users')

    return app


if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        db.create_all() 

    app.run(debug=True)
