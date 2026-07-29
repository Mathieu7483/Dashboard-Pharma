from app import create_app
from database.data_manager import db
from utils.seeder import seed_all_initial_data
from utils.migrate_ansm_fields import ensure_ansm_columns

app = create_app()

HOST = "127.0.0.1"
BACKEND_PORT = 5000
FRONTEND_PORT = 3000

with app.app_context():
    print("\n--- 🔧 Database Initialization ---")
    db.create_all()
    ensure_ansm_columns()
    print("--- 🌱 Seeding Process ---")
    try:
        seed_all_initial_data()
        print("✅ Seeding completed successfully.")
    except Exception as e:
        print(f"❌ Seeding failed: {str(e)}")

print("\n--- 🚀 Starting Pharma Server ---")
print(f"🌐 Application Front: http://{HOST}:{FRONTEND_PORT}/Client/auth.html")
print(f"📚 Documentation API:  http://{HOST}:{BACKEND_PORT}/docs\n")
app.run(debug=False, port=5000)

if __name__ == "__main__":
    app.run(debug=True, host=HOST, port=BACKEND_PORT)
>>>>>>> 083b8bd (feat: Implement ANSM referential for pharmaceutical specialties)
