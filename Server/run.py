from app import create_app
from database.data_manager import db
from utils.seeder import seed_all_initial_data

app = create_app()

if __name__ == "__main__":
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

    print("\n--- 🗺️ Routes enregistrées ---")
    for rule in app.url_map.iter_rules():
        print(f"{rule} -> {rule.endpoint}")
    
    app.run(host="0.0.0.0", debug=True, port=5000, use_reloader=False)