import os
import sys
import random
from datetime import datetime, timedelta, UTC

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app 
from services.facade import FacadeService

def seed_data():
    app = create_app()
    facade = FacadeService()

    with app.app_context():
        print("--- 🚀 Seeding Sales Data into Database ---")
        
        products = facade.get_all_products()
        users = facade.get_all_users()
        clients = facade.get_all_clients()
        doctors = facade.get_all_doctors()

        if not products or not users or not clients:
            print("❌ Error: You need Products, Users, and Clients in DB first.")
            return

        user_id = users[0].id
        client_id = clients[0].id
        # Pick a doctor if one exists for prescriptions
        doctor_id = doctors[0].id if doctors else None

        # Simulation: Monthly (30 days)
        for i in range(30):
            past_date = datetime.now(UTC) - timedelta(days=i)
            
            for _ in range(random.randint(2, 5)):
                # Prepare items for process_sale
                product = random.choice(products)
                items_data = [
                    {
                        'product_id': product.id,
                        'quantity': random.randint(1, 2)
                    }
                ]
                
                try:
                    # We call your existing business logic
                    facade.process_sale(
                        client_id=client_id,
                        doctor_id=doctor_id if product.is_prescription_only else None,
                        items_data=items_data,
                        user_id=user_id,
                        created_at=past_date
                    )
                except Exception as e:
                    print(f"Skipping a sale: {e}")

        print("--- ✅ Seeding Complete! ---")

if __name__ == "__main__":
    seed_data()