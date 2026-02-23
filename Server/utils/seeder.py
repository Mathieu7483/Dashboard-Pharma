import csv
import json
import os
import random
import unicodedata
from datetime import datetime, timedelta, UTC
from database.data_manager import db
from models.user import UserModel
from models.product import ProductModel
from models.client import ClientModel
from models.doctor import DoctorModel
from models.interaction import InteractionModel
from utils.seed_aliases import seed_product_aliases
from utils.seed_sales import seed_product_sales


def _norm(s: str) -> str:
    """Normalise un nom d'ingredient : supprime accents, garde la casse."""
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii")


def seed_all_initial_data():
    """
    Main entry point for seeding the database.
    Execution order ensures foreign key constraints are respected.
    """
    print("\n--- 🚀 Starting Global Seeding Process ---")

    admin = _seed_admin()
    if not admin:
        print("❌ Critical failure: Admin seeding failed. Aborting.")
        return

    _seed_json_data(admin.id)
    _seed_csv_inventory(admin.id)
    _seed_medical_interactions()
    seed_product_sales()
    seed_product_aliases()

    print("--- ✅ Seeding Process Completed ---\n")


def _seed_admin():
    """Initializes the primary admin account or ensures it has correct privileges."""
    admin = UserModel.query.filter_by(username='Mathieu').first()

    if not admin:
        print("Creating primary admin account...")
        admin = UserModel(
            username='Mathieu',
            email='mathieu.admin@pharma.com',
            password='Admin@1234',
            is_admin=True
        )
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

        for u in data.get('users', []):
            if not UserModel.query.filter_by(username=u['username']).first():
                new_user = UserModel(
                    username=u['username'],
                    email=u['email'],
                    password=u['password'],
                    is_admin=u.get('is_admin', False)
                )
                new_user.set_password(u['password'])
                db.session.add(new_user)

        for c in data.get('clients', []):
            if not ClientModel.query.filter_by(email=c['email']).first():
                days_ago = random.randint(0, 365)
                created_date = datetime.now(UTC) - timedelta(days=days_ago)
                new_client = ClientModel(
                    first_name=c['first_name'],
                    last_name=c['last_name'],
                    email=c['email'],
                    address=c.get('address'),
                    phone=c.get('phone'),
                    user_id=admin_id
                )
                new_client.created_at = created_date
                new_client.updated_at = created_date
                db.session.add(new_client)

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
    csv_path = os.path.abspath(os.path.join(current_dir, '..', 'utils', 'initial_inventory.csv'))

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
    Populates the interaction table for medication safety logic.
    """
    if InteractionModel.query.first():
        print("Interaction data already exists. Skipping...")
        return

    conflicts = [
        # ── CARDIO / ANTICOAGULANTS ───────────────────────────────────────────
        {"a": "Warfarine",    "b": "Acide Acetylsalicylique", "sev": "Critical",
         "desc": "Risque majeur d'hemorragie interne (cumul anticoagulant + antiagregeant)."},
        {"a": "Warfarine",    "b": "Rivaroxaban",             "sev": "Critical",
         "desc": "Doublon anticoagulant : risque vital d'hemorragie."},
        {"a": "Warfarine",    "b": "Ibuprofene",              "sev": "Critical",
         "desc": "Risque hemorragique severe (lesion gastrique par l'AINS)."},
        {"a": "Warfarine",    "b": "Diclofenac",              "sev": "Critical",
         "desc": "Risque hemorragique severe."},
        {"a": "Warfarine",    "b": "Clopidogrel",             "sev": "High",
         "desc": "Risque hemorragique augmente (cumul anticoagulant + antiagregeant)."},
        {"a": "Rivaroxaban",  "b": "Acide Acetylsalicylique", "sev": "Critical",
         "desc": "Association dangereuse : risque de saignement incontrole."},
        {"a": "Clopidogrel",  "b": "Acide Acetylsalicylique", "sev": "High",
         "desc": "Risque de saignement augmente (necessite surveillance medicale)."},
        {"a": "Clopidogrel",  "b": "Omeprazole",              "sev": "Moderate",
         "desc": "Reduction de l'efficacite protectrice du Clopidogrel (risque d'infarctus)."},
        {"a": "Clopidogrel",  "b": "Esomeprazole",            "sev": "Moderate",
         "desc": "Diminution de l'effet antiagregeant."},

        # ── AINS & CORTICOIDES ────────────────────────────────────────────────
        {"a": "Ibuprofene",   "b": "Acide Acetylsalicylique", "sev": "High",
         "desc": "Risque d'ulcere gastrique et perte d'effet protecteur cardiaque de l'aspirine."},
        {"a": "Ibuprofene",   "b": "Naproxene",               "sev": "High",
         "desc": "Doublon d'AINS : toxicite renale et digestive accrue."},
        {"a": "Ibuprofene",   "b": "Ketoprofene",             "sev": "High",
         "desc": "Toxicite digestive severe."},
        {"a": "Ibuprofene",   "b": "Prednisone",              "sev": "High",
         "desc": "Risque massif d'ulcere et d'hemorragie digestive."},
        {"a": "Diclofenac",   "b": "Prednisone",              "sev": "High",
         "desc": "Association gastro-lesive severe."},
        {"a": "Furosemide",   "b": "Ibuprofene",              "sev": "High",
         "desc": "Insuffisance renale aigue par reduction du flux sanguin renal."},
        {"a": "Furosemide",   "b": "Naproxene",               "sev": "High",
         "desc": "Risque d'insuffisance renale."},
        {"a": "Captopril",    "b": "Ibuprofene",              "sev": "High",
         "desc": "L'AINS bloque l'effet antihypertenseur et menace les reins."},
        {"a": "Enalapril",    "b": "Ibuprofene",              "sev": "High",
         "desc": "Risque d'insuffisance renale (Triple Whammy avec diuretiques)."},

        # ── DIABETE ───────────────────────────────────────────────────────────
        {"a": "Metformine",   "b": "Prednisone",              "sev": "Moderate",
         "desc": "Le corticoide augmente la glycemie, s'opposant a l'antidiabetique."},
        {"a": "Insuline Lispro", "b": "Alcool",              "sev": "High",
         "desc": "Risque d'hypoglycemie severe et imprevisible."},
        {"a": "Gliclazide",   "b": "Alcool",                  "sev": "High",
         "desc": "Effet antabuse et risque d'hypoglycemie."},
        {"a": "Sitagliptine", "b": "Insuline Lispro",         "sev": "Moderate",
         "desc": "Surveillance accrue de la glycemie (risque d'hypoglycemie)."},

        # ── PSYCHOTROPES & ANALGESIQUES ───────────────────────────────────────
        {"a": "Tramadol",     "b": "Alprazolam",              "sev": "Critical",
         "desc": "Risque de depression respiratoire, sedation profonde et coma."},
        {"a": "Tramadol",     "b": "Bromazepam",              "sev": "Critical",
         "desc": "Association sedative dangereuse."},
        {"a": "Tramadol",     "b": "Escitalopram",            "sev": "High",
         "desc": "Risque de syndrome serotoninergique (agitation, fievre, confusion)."},
        {"a": "Zolpidem",     "b": "Alprazolam",              "sev": "Critical",
         "desc": "Somnolence extreme, risque d'accident et d'arret respiratoire."},
        {"a": "Zopiclone",    "b": "Diazepam",                "sev": "Critical",
         "desc": "Potentialisation reciproque de la sedation."},
        {"a": "Cyamemazine",  "b": "Tramadol",                "sev": "High",
         "desc": "Risque de convulsions augmente."},

        # ── ANTIBIOTIQUES ─────────────────────────────────────────────────────
        {"a": "Amoxicilline", "b": "Methotrexate",            "sev": "High",
         "desc": "L'antibiotique reduit l'elimination du methotrexate (toxicite)."},
        {"a": "Ciprofloxacine", "b": "Theophylline",          "sev": "High",
         "desc": "Surdosage de theophylline (tremblements, palpitations)."},
        {"a": "Clarithromycine", "b": "Simvastatine",         "sev": "Critical",
         "desc": "Risque de rhabdomyolyse (destruction des muscles)."},
        {"a": "Azithromycine", "b": "Amiodarone",             "sev": "Critical",
         "desc": "Troubles du rythme cardiaque graves."},

        # ── AUTRES ────────────────────────────────────────────────────────────
        {"a": "Spironolactone", "b": "Captopril",             "sev": "High",
         "desc": "Risque d'hyperkaliemie mortelle (exces de potassium)."},
        {"a": "Spironolactone", "b": "Valsartan",             "sev": "High",
         "desc": "Risque cardiaque par exces de potassium."},
        {"a": "Amiodarone",   "b": "Levofloxacine",           "sev": "Critical",
         "desc": "Risque majeur de torsades de pointe (coeur)."},
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
        print(f"✅ Success: {len(conflicts)} interactions medicales seedees (sans accents).")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error during Interaction seeding: {e}")