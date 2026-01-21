import csv
import json
import os
from database.data_manager import db
from models.user import UserModel
from models.product import ProductModel
from models.client import ClientModel
from models.doctor import DoctorModel
from models.interaction import InteractionModel
from utils.seed_aliases import seed_product_aliases


def seed_all_initial_data():
    """
    Main entry point for seeding the database.
    Order: Admin -> JSON Entities -> CSV Inventory -> Medical Interactions.
    """
    print("\n--- 🚀 Starting Global Seeding Process ---")
    
    # 1. ADMIN USER
    admin = _seed_admin()
    if not admin:
        return

    # 2. JSON DATA (Clients, Doctors, Users)
    _seed_json_data(admin.id)

    # 3. CSV DATA (Products)
    _seed_csv_inventory(admin.id)

    # 4. MEDICAL INTERACTIONS (Safety Logic)
    _seed_medical_interactions()

    # 5. PRODUCT ALIASES
    seed_product_aliases()
    print("--- ✅ Seeding Process Completed ---\n")


def _seed_admin():
    """Initializes the primary admin account."""
    admin = UserModel.query.filter_by(username='Mathieu').first()
    if not admin:
        print("Creating primary admin account...")
        admin = UserModel(
            username='Mathieu', 
            email='mathieu.admin@pharma.com', 
            is_admin=True,
            password='Admin@1234' 
        )
        admin.set_password('Admin@1234')
        db.session.add(admin)
        try:
            db.session.commit()
            print("Success: Admin 'Mathieu' is ready.")
        except Exception as e:
            db.session.rollback()
            print(f"Abort: Critical error during admin initialization: {e}")
            return None
    return admin

def _seed_json_data(admin_id):
    """Imports users, clients, and doctors from JSON."""
    current_dir = os.path.dirname(__file__)
    json_path = os.path.join(current_dir, 'data_seed.json')

    if not os.path.exists(json_path):
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Users
        for u in data.get('users', []):
            if not UserModel.query.filter_by(username=u['username']).first():
                new_user = UserModel(
                    username=u['username'], email=u['email'],
                    is_admin=u.get('is_admin', False), password=u['password'] 
                )
                new_user.set_password(u['password'])
                db.session.add(new_user)

        # Clients
        for c in data.get('clients', []):
            if not ClientModel.query.filter_by(email=c['email']).first():
                db.session.add(ClientModel(
                    first_name=c['first_name'], last_name=c['last_name'],
                    email=c['email'], address=c.get('address'),
                    phone=c.get('phone'), user_id=admin_id
                ))

        # Doctors
        for d in data.get('doctors', []):
            if not DoctorModel.query.filter_by(email=d['email']).first():
                db.session.add(DoctorModel(
                    first_name=d['first_name'], last_name=d['last_name'],
                    email=d['email'], specialty=d.get('specialty'),
                    phone=d.get('phone'), address=d.get('address'),
                    user_id=admin_id
                ))

        db.session.commit()
        print("Success: JSON entities imported.")
    except Exception as e:
        db.session.rollback()
        print(f"Error during JSON seeding: {e}")

def _seed_csv_inventory(admin_id):
    """Imports products from the CSV file."""
    current_dir = os.path.dirname(__file__)
    csv_path = os.path.abspath(os.path.join(current_dir, '..', 'database', 'initial_inventory.csv'))

    if not os.path.exists(csv_path):
        print(f"Warning: CSV not found at {csv_path}")
        return

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
                        user_id=admin_id
                    ))
                    product_count += 1
            db.session.commit()
            print(f"Success: {product_count} products imported from CSV.")
    except Exception as e:
        db.session.rollback()
        print(f"Error during CSV seeding: {e}")

def _seed_medical_interactions():
    """
    Seeds the interaction table. 
    Matches 'active_ingredient' from CSV for logic consistency.
    """
    if InteractionModel.query.first():
        return

    # IMPORTANT: Use the EXACT names from your CSV 'active_ingredient' column
    conflicts = [
        {
            "a": "Ibuprofène", 
            "b": "Acide Acétylsalicylique", # Corrected for your CSV
            "sev": "High", 
            "desc": "Risque accru d'ulcère et d'hémorragie gastrique."
        },
        {
            "a": "Warfarine", 
            "b": "Acide Acétylsalicylique", 
            "sev": "Critical", 
            "desc": "Risque majeur d'hémorragie interne (Anticoagulant + Antiagrégant)."
        },
        {
            "a": "Furosémide", 
            "b": "Ibuprofène", 
            "sev": "Moderate", 
            "desc": "Réduction de l'effet diurétique et risque pour la fonction rénale."
        }
    ]

    for c in conflicts:
        db.session.add(InteractionModel(
            ingredient_a=c["a"],
            ingredient_b=c["b"],
            severity=c["sev"],
            description=c["desc"]
        ))
    
    try:
        db.session.commit()
        print("Success: Medical interaction logic seeded.")
    except Exception as e:
        db.session.rollback()
        print(f"Error during Interaction seeding: {e}")