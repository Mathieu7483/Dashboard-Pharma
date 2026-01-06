import os
import sys
import random
from datetime import datetime, timedelta, UTC

# Add parent directory to sys.path to allow imports from 'app' and 'services'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app 
from services.facade import FacadeService

def seed_data():
    """
    Simulation script to populate the database with fake sales data
    spanning the last 30 days to test Dashboard Analytics.
    """
    app = create_app()
    facade = FacadeService()

    with app.app_context():
        print("--- 🚀 Starting Sales Data Seeding ---")
        
        # Fetching required entities from the database
        products = facade.get_all_products()
        users = facade.get_all_users()
        clients = facade.get_all_clients()
        doctors = facade.get_all_doctors()

        # Safety check: ensures basic data exists before creating sales
        if not products or not users or not clients:
            print("❌ Error: Missing prerequisite data (Products, Users, or Clients).")
            print("Please run the initial seeder first.")
            return

        # Use the first available user and client for all simulated sales
        user_id = users[0].id
        client_id = clients[0].id
        
        # Pick a doctor if available for products requiring a prescription
        doctor_id = doctors[0].id if doctors else None

        print(f"DEBUG: Using User ID {user_id} and Client ID {client_id}")
        
        # --- 30-DAY TIME SERIES SIMULATION ---
        now = datetime.now(UTC)
        total_sales_created = 0

        for i in range(30):
            # Calculate the date for each day in the past
            past_date = now - timedelta(days=i)
            
            # Generate a random number of sales per day (between 2 and 8)
            daily_sales_count = random.randint(2, 8)
            
            for _ in range(daily_sales_count):
                # Pick a random product from the inventory
                product = random.choice(products)
                
                # Skip if product is out of stock to prevent process_sale from failing
                if product.stock <= 0:
                    continue

                # Format the item data as expected by the FacadeService
                items_data = [
                    {
                        'product_id': product.id,
                        'quantity': random.randint(1, 3)
                    }
                ]
                
                try:
                    # Execute business logic: creates sale, items, and updates stock
                    facade.process_sale(
                        client_id=client_id,
                        # Pass doctor_id only if the drug requires a prescription
                        doctor_id=doctor_id if product.is_prescription_only else None,
                        items_data=items_data,
                        user_id=user_id,
                        created_at=past_date
                    )
                    total_sales_created += 1
                except Exception as e:
                    # Log failure but continue the loop (e.g., 'Insufficient stock')
                    print(f"⚠️ Sale skipped for {product.name}: {e}")

        print(f"\n--- ✅ Seeding Complete! ---")
        print(f"Total sales generated: {total_sales_created}")

if __name__ == "__main__":
    seed_data()