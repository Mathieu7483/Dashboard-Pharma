from app import create_app
from database.data_manager import db
from utils.seeder import seed_all_initial_data

app = create_app()

with app.app_context():
    print("\n--- 🔧 Database Initialization ---")
    db.create_all()

    print("--- 🌱 Seeding Process ---")
    try:
        seed_all_initial_data()
        print("✅ Seeding completed successfully.")
    except Exception as e:
        print(f"❌ Seeding failed: {str(e)}")

print("\n--- 🚀 Starting Pharma Server ---")
print("Documentation: http://127.0.0.1:5000/docs")

app.run(debug=True, port=5000)