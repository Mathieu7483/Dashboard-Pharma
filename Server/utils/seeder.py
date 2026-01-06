import csv
import json
import os
from database.data_manager import db
from models.user import UserModel
from models.product import ProductModel
from models.client import ClientModel
from models.doctor import DoctorModel

def seed_all_initial_data():
    print("--- Starting Global Seeding ---")
    
    # 1. RECUPERATION DE L'ADMIN (MATHIEU)
    admin = UserModel.query.filter_by(username='Mathieu').first()
    if not admin:
        try:
            admin = UserModel(
                username='Mathieu', 
                email='mathieu.admin@pharma.com', 
                is_admin=True,
                password='Admin@1234'
            )
            admin.set_password('Admin@1234')
            db.session.add(admin)
            db.session.commit()
            print("Success: Primary Admin 'Mathieu' created.")
        except Exception as e:
            db.session.rollback()
            print(f"Abort: Admin creation failed: {e}")
            return

    current_dir = os.path.dirname(__file__)
    json_path = os.path.join(current_dir, 'data_seed.json')

    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 2. IMPORT USERS
            for u in data.get('users', []):
                if not UserModel.query.filter_by(username=u['username']).first():
                    # PASSAGE EXPLICITE DES ARGUMENTS
                    new_u = UserModel(
                        username=u['username'],
                        email=u['email'],
                        is_admin=u['is_admin'],
                        password=u['password']
                    )
                    new_u.set_password(u['password'])
                    db.session.add(new_u)

            # 3. IMPORT CLIENTS (AVEC USER_ID OBLIGATOIRE)
            for c in data.get('clients', []):
                if not ClientModel.query.filter_by(email=c['email']).first():
                    db.session.add(ClientModel(
                        first_name=c['first_name'],
                        last_name=c['last_name'],
                        email=c['email'],
                        address=c.get('address'),
                        user_id=admin.id  # <--- PASSÉ EXPLICITEMENT ICI
                    ))

            # 4. IMPORT DOCTORS (AVEC USER_ID OBLIGATOIRE)
            for d in data.get('doctors', []):
                if not DoctorModel.query.filter_by(email=d['email']).first():
                    db.session.add(DoctorModel(
                        first_name=d['first_name'],
                        last_name=d['last_name'],
                        email=d['email'],
                        specialty=d.get('specialty'),
                        phone=d.get('phone'),
                        user_id=admin.id  # <--- PASSÉ EXPLICITEMENT ICI
                    ))

            db.session.commit()
            print("Success: JSON data imported successfully.")

        except Exception as e:
            db.session.rollback()
            # On affiche l'erreur complète pour débugger
            print(f"Error seeding JSON data: {e}")

    # 5. IMPORT CSV
    csv_path = os.path.abspath(os.path.join(current_dir, '..', 'database', 'initial_inventory.csv'))
    if os.path.exists(csv_path):
        try:
            with open(csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
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
                        count += 1
                db.session.commit()
                print(f"Success: {count} products imported from CSV.")
        except Exception as e:
            db.session.rollback()
            print(f"Error seeding CSV: {e}")