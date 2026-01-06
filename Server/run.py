from app import create_app
from utils.seeder import seed_all_initial_data
from database.data_manager import db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_all_initial_data()
    
    app.run(debug=True, port=5000)