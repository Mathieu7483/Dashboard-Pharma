import csv
import json
import os
import random
from datetime import datetime, timedelta, UTC
from database.data_manager import db
from models.user import UserModel
from models.product import ProductModel
from models.client import ClientModel
from models.doctor import DoctorModel
from models.interaction import InteractionModel
from utils.seed_aliases import seed_product_aliases
from utils.seed_sales import seed_product_sales

def seed_all_initial_data():
    """
    Main entry point for seeding the database.
    Execution order ensures foreign key constraints are respected.
    """
    print("\n--- 🚀 Starting Global Seeding Process ---")
    
    # 1. Initialize Admin first (required as owner for other entities)
    admin = _seed_admin()
    if not admin:
        print("❌ Critical failure: Admin seeding failed. Aborting.")
        return

    # 2. Import secondary entities from JSON
    _seed_json_data(admin.id)

    # 3. Load product catalog from CSV
    _seed_csv_inventory(admin.id)

    # 4. Populate medical interaction safety rules
    _seed_medical_interactions()
    
    # 5. Generate historical sales data
    seed_product_sales()

    # 6. Generate product search aliases
    seed_product_aliases()
    
    print("--- ✅ Seeding Process Completed ---\n")


def _seed_admin():
    """Initializes the primary admin account or ensures it has correct privileges."""
    admin = UserModel.query.filter_by(username='Mathieu').first()
    
    if not admin:
        print("Creating primary admin account...")
        # You MUST provide the password here because your UserModel __init__ requires it
        admin = UserModel(
            username='Mathieu', 
            email='mathieu.admin@pharma.com', 
            password='Admin@1234',  # This was the missing argument
            is_admin=True
        )
        # We still call set_password to ensure it's hashed via Bcrypt
        admin.set_password('Admin@1234')
        db.session.add(admin)
    else:
        print("Admin account exists. Updating credentials and privileges...")
        admin.is_admin = True 
        admin.set_password('Admin@1234') 

    try:
        db.session.commit()
        print("Success: Admin 'Mathieu' is ready.")
        return admin
    except Exception as e:
        db.session.rollback()
        print(f"Abort: Error during admin initialization: {e}")
        return None


def _seed_json_data(admin_id):
    """Imports users, clients, and doctors from JSON with randomized historical dates."""
    current_dir = os.path.dirname(__file__)
    json_path = os.path.join(current_dir, 'data_seed.json')

    if not os.path.exists(json_path):
        print(f"Warning: JSON seed file not found at {json_path}")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # --- SEED USERS ---
        for u in data.get('users', []):
            if not UserModel.query.filter_by(username=u['username']).first():
                # FIX: Added the mandatory 'password' positional argument
                new_user = UserModel(
                    username=u['username'], 
                    email=u['email'],
                    password=u['password'],  # <--- REQUIRED BY YOUR MODEL __init__
                    is_admin=u.get('is_admin', False)
                )
                # Ensure the password is properly hashed
                new_user.set_password(u['password'])
                db.session.add(new_user)

        # --- SEED CLIENTS ---
        # Note: These will now be created because the user loop above won't crash
        for c in data.get('clients', []):
            if not ClientModel.query.filter_by(email=c['email']).first():
                days_ago = random.randint(0, 365)
                # Use UTC for consistency
                created_date = datetime.now(UTC) - timedelta(days=days_ago)
                
                new_client = ClientModel(
                    first_name=c['first_name'], 
                    last_name=c['last_name'],
                    email=c['email'], 
                    address=c.get('address'),
                    phone=c.get('phone'), 
                    user_id=admin_id
                )
                # Manually setting timestamps for your monthly stats
                new_client.created_at = created_date
                new_client.updated_at = created_date
                db.session.add(new_client)

        # --- SEED DOCTORS ---
        for d in data.get('doctors', []):
            if not DoctorModel.query.filter_by(email=d['email']).first():
                days_ago = random.randint(0, 365)
                created_date = datetime.now(UTC) - timedelta(days=days_ago)
                
                new_doctor = DoctorModel(
                    first_name=d['first_name'], 
                    last_name=d['last_name'],
                    email=d['email'], 
                    specialty=d.get('specialty'),
                    phone=d.get('phone'), 
                    address=d.get('address'),
                    user_id=admin_id
                )
                new_doctor.created_at = created_date
                new_doctor.updated_at = created_date
                db.session.add(new_doctor)

        db.session.commit()
        print("✅ Success: JSON entities (Users, Clients, Doctors) imported.")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error during JSON seeding: {e}")

def _seed_csv_inventory(admin_id):
    """Imports products from the CSV file into the database."""
    current_dir = os.path.dirname(__file__)
    # Path resolution to find the CSV in the utils folder
    csv_path = os.path.abspath(os.path.join(current_dir, '..', 'utils', 'initial_inventory.csv'))

    if not os.path.exists(csv_path):
        print(f"Warning: CSV not found at {csv_path}")
        return

    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            product_count = 0
            for row in reader:
                # Avoid duplicates by checking product name
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
    """Populates the interaction table for medication safety logic."""
    if InteractionModel.query.first():
        print("Interaction data already exists. Skipping...")
        return

    # List of known drug-drug interactions for the engine
    conflicts = [
        {"a": "Warfarine", "b": "Acide Acétylsalicylique", "sev": "Critical", "desc": "Major risk of internal bleeding."},
        {"a": "Warfarine", "b": "Rivaroxaban", "sev": "Critical", "desc": "Anticoagulant overlap: life-threatening hemorrhage risk."},
        {"a": "Amiodarone", "b": "Levofloxacine", "sev": "Critical", "desc": "Serious cardiac arrhythmia risk (QT prolongation)."},
        {"a": "Ibuprofène", "b": "Acide Acétylsalicylique", "sev": "High", "desc": "Increased risk of gastric ulcers."},
        {"a": "Furosémide", "b": "Ibuprofène", "sev": "High", "desc": "Risk of acute renal failure."},
        {"a": "Ibuprofène", "b": "Prednisone", "sev": "High", "desc": "High bleeding risk (NSAID + Corticosteroid)."},
        {"a": "Oméprazole", "b": "Clopidogrel", "sev": "Moderate", "desc": "Reduced Clopidogrel efficacy."},
        {"a": "Metformine", "b": "Prednisone", "sev": "Moderate", "desc": "Blood sugar spike (corticosteroid counteracts antidiabetic)."}
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