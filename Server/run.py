from app import create_app
from config import DevelopmentConfig


app = create_app(config_object=DevelopmentConfig)


if __name__ == '__main__':
    print("Démarrage du serveur...")
    app.run(debug=True, port=5000)