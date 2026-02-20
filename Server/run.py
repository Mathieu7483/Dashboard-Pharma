from app import create_app
<<<<<<< HEAD
from config import DevelopmentConfig


app = create_app(config_object=DevelopmentConfig)


if __name__ == '__main__':
    print("Démarrage du serveur...")
=======
from utils.seeder import seed_all_initial_data
from database.data_manager import db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_all_initial_data()
    
>>>>>>> Mathieu
    app.run(debug=True, port=5000)