import csv
import json
import os
from database.data_manager import db
from models.user import UserModel
from models.product import ProductModel
from models.client import ClientModel
from models.doctor import DoctorModel

def seed_all_initial_data():
    """
    Main seeding function. Fixed to satisfy UserModel.__init__ requirements.
    """
    print("--- Starting Global Seeding Process ---")
    
    # 1. ADMIN USER INITIALIZATION (MATHIEU)
    admin = UserModel.query.filter_by(username='Mathieu').first()
    
    if not admin:
        print("Creating primary admin account...")
        # We pass 'Admin@1234' directly to satisfy the mandatory argument in __init__
        admin = UserModel(
            username='Mathieu', 
            email='mathieu.admin@pharma.com', 
            is_admin=True,
            password='Admin@1234' 
        )
    
    # We call set_password anyway to ensure the hashing logic is applied
    admin.set_password('Admin@1234')
    db.session.add(admin)
    
    try:
        db.session.commit()
        print(f"Success: Admin 'Mathieu' is ready.")
    except Exception as e:
        db.session.rollback()
        print(f"Abort: Critical error during admin initialization: {e}")
        return

    # Path configuration
    current_dir = os.path.dirname(__file__)
    json_path = os.path.join(current_dir, 'data_seed.json')

    # 2. JSON DATA IMPORT
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for u in data.get('users', []):
                if not UserModel.query.filter_by(username=u['username']).first():
                    # Satisfying mandatory 'password' argument for secondary users too
                    new_user = UserModel(
                        username=u['username'],
                        email=u['email'],
                        is_admin=u.get('is_admin', False),
                        password=u['password'] 
                    )
                    new_user.set_password(u['password'])
                    db.session.add(new_user)

            # Seed Clients
            for c in data.get('clients', []):
                if not ClientModel.query.filter_by(email=c['email']).first():
                    db.session.add(ClientModel(
                        first_name=c['first_name'],
                        last_name=c['last_name'],
                        email=c['email'],
                        address=c.get('address'),
                        user_id=admin.id
                    ))

            # Seed Doctors
            for d in data.get('doctors', []):
                if not DoctorModel.query.filter_by(email=d['email']).first():
                    db.session.add(DoctorModel(
                        first_name=d['first_name'],
                        last_name=d['last_name'],
                        email=d['email'],
                        specialty=d.get('specialty'),
                        phone=d.get('phone'),
                        user_id=admin.id
                    ))

            db.session.commit()
            print("Success: JSON entities imported.")
        except Exception as e:
            db.session.rollback()
            print(f"Error during JSON seeding: {e}")

    # 3. CSV DATA IMPORT
    csv_path = os.path.abspath(os.path.join(current_dir, '..', 'database', 'initial_inventory.csv'))
    if os.path.exists(csv_path):
        try:
            with open(csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                product_count = 0
                for row in reader:
                    if not ProductModel.query.filter_by(name=row['name']).first():
                        db.session.add(ProductModel(
                            name=row['name'],
                            active_ingredient=row['active_ingredient'],
                            dosage=row['dosage'],
                            stock=int(row['stock']),
                            price=float(row['price']),
                            is_prescription_only=row['is_prescription_only'].strip().lower() == 'true',
                            user_id=admin.id
                        ))
                        product_count += 1
                db.session.commit()
                print(f"Success: {product_count} products imported from CSV.")
        except Exception as e:
            db.session.rollback()
            print(f"Error during CSV seeding: {e}")

    print("--- Seeding Process Completed ---")