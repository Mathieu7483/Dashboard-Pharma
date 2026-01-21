"""
Server/utils/seed_aliases.py
Seeds the product_aliases table with commercial name mappings
"""

from database.data_manager import db
from models.product_alias import ProductAliasModel

def seed_product_aliases():
    """
    Populate the product_aliases table with common commercial names.
    Run this after creating tables.
    """
    if ProductAliasModel.query.first():
        print("Product aliases already seeded.")
        return
    
    aliases = [
        # Anti-inflammatoires / Antalgiques
        {"alias": "Aspirine", "ingredient": "Acide Acétylsalicylique", "cat": "analgesic"},
        {"alias": "Aspegic", "ingredient": "Acide Acétylsalicylique", "cat": "analgesic"},
        {"alias": "Kardégic", "ingredient": "Acide Acétylsalicylique", "cat": "analgesic"},
        
        {"alias": "Ibuprofène", "ingredient": "Ibuprofène", "cat": "analgesic"},
        {"alias": "Advil", "ingredient": "Ibuprofène", "cat": "analgesic"},
        {"alias": "Nurofen", "ingredient": "Ibuprofène", "cat": "analgesic"},
        {"alias": "Spedifen", "ingredient": "Ibuprofène", "cat": "analgesic"},
        
        {"alias": "Paracétamol", "ingredient": "Paracétamol", "cat": "analgesic"},
        {"alias": "Doliprane", "ingredient": "Paracétamol", "cat": "analgesic"},
        {"alias": "Dafalgan", "ingredient": "Paracétamol", "cat": "analgesic"},
        {"alias": "Efferalgan", "ingredient": "Paracétamol", "cat": "analgesic"},
        {"alias": "Tylenol", "ingredient": "Paracétamol", "cat": "analgesic"},
        
        # Antibiotiques
        {"alias": "Amoxicilline", "ingredient": "Amoxicilline", "cat": "antibiotic"},
        {"alias": "Clamoxyl", "ingredient": "Amoxicilline", "cat": "antibiotic"},
        {"alias": "Augmentin", "ingredient": "Amoxicilline/Clavulanate", "cat": "antibiotic"},
        
        {"alias": "Azithromycine", "ingredient": "Azithromycine", "cat": "antibiotic"},
        {"alias": "Zithromax", "ingredient": "Azithromycine", "cat": "antibiotic"},
        
        {"alias": "Clarithromycine", "ingredient": "Clarithromycine", "cat": "antibiotic"},
        {"alias": "Zeclar", "ingredient": "Clarithromycine", "cat": "antibiotic"},
        
        {"alias": "Ciprofloxacine", "ingredient": "Ciprofloxacine", "cat": "antibiotic"},
        {"alias": "Ciflox", "ingredient": "Ciprofloxacine", "cat": "antibiotic"},
        
        {"alias": "Doxycycline", "ingredient": "Doxycycline", "cat": "antibiotic"},
        
        # Anticoagulants / Antiagrégants (CRITICAL)
        {"alias": "Warfarine", "ingredient": "Warfarine", "cat": "anticoagulant"},
        {"alias": "Coumadine", "ingredient": "Warfarine", "cat": "anticoagulant"},
        
        {"alias": "Clopidogrel", "ingredient": "Clopidogrel", "cat": "anticoagulant"},
        {"alias": "Plavix", "ingredient": "Clopidogrel", "cat": "anticoagulant"},
        
        {"alias": "Rivaroxaban", "ingredient": "Rivaroxaban", "cat": "anticoagulant"},
        {"alias": "Xarelto", "ingredient": "Rivaroxaban", "cat": "anticoagulant"},
        {"alias": "Rivière", "ingredient": "Rivaroxaban", "cat": "anticoagulant"},  # From your CSV
        
        # Antihistaminiques
        {"alias": "Cétirizine", "ingredient": "Cétirizine", "cat": "antihistamine"},
        {"alias": "Zyrtec", "ingredient": "Cétirizine", "cat": "antihistamine"},
        
        {"alias": "Loratadine", "ingredient": "Loratadine", "cat": "antihistamine"},
        {"alias": "Clarityne", "ingredient": "Loratadine", "cat": "antihistamine"},
        
        {"alias": "Lévocétirizine", "ingredient": "Lévocétirizine", "cat": "antihistamine"},
        {"alias": "Xyzal", "ingredient": "Lévocétirizine", "cat": "antihistamine"},
        
        # IPP (Inhibiteurs Pompe à Protons)
        {"alias": "Oméprazole", "ingredient": "Oméprazole", "cat": "ppi"},
        {"alias": "Mopral", "ingredient": "Oméprazole", "cat": "ppi"},
        {"alias": "MopralPro", "ingredient": "Oméprazole", "cat": "ppi"},
        
        {"alias": "Pantoprazole", "ingredient": "Pantoprazole", "cat": "ppi"},
        {"alias": "Inipomp", "ingredient": "Pantoprazole", "cat": "ppi"},
        
        # Diurétiques
        {"alias": "Furosémide", "ingredient": "Furosémide", "cat": "diuretic"},
        {"alias": "Lasilix", "ingredient": "Furosémide", "cat": "diuretic"},
        
        # Corticoïdes
        {"alias": "Hydrocortisone", "ingredient": "Hydrocortisone", "cat": "corticoid"},
        {"alias": "Dexaméthasone", "ingredient": "Dexaméthasone", "cat": "corticoid"},
        {"alias": "Prednisone", "ingredient": "Prednisone", "cat": "corticoid"},
        {"alias": "Cortancyl", "ingredient": "Prednisone", "cat": "corticoid"},
        
        # Antidiabétiques
        {"alias": "Metformine", "ingredient": "Metformine", "cat": "antidiabetic"},
        {"alias": "Glucophage", "ingredient": "Metformine", "cat": "antidiabetic"},
        {"alias": "Stagid", "ingredient": "Metformine", "cat": "antidiabetic"},
        
        {"alias": "Insuline", "ingredient": "Insuline Lispro", "cat": "antidiabetic"},
        
        # Bronchodilatateurs
        {"alias": "Ventoline", "ingredient": "Salbutamol", "cat": "bronchodilator"},
        {"alias": "Salbutamol", "ingredient": "Salbutamol", "cat": "bronchodilator"},
        
        # Antidépresseurs
        {"alias": "Lexapro", "ingredient": "Escitalopram", "cat": "antidepressant"},
        {"alias": "Escitalopram", "ingredient": "Escitalopram", "cat": "antidepressant"},
        
        # Statines
        {"alias": "Simvastatine", "ingredient": "Simvastatine", "cat": "statin"},
        {"alias": "Atorvastatine", "ingredient": "Atorvastatine", "cat": "statin"},
        
        # Antihypertenseurs
        {"alias": "Amlodipine", "ingredient": "Amlodipine", "cat": "antihypertensive"},
        {"alias": "Losartan", "ingredient": "Losartan", "cat": "antihypertensive"},
        {"alias": "Captopril", "ingredient": "Captopril", "cat": "antihypertensive"},
        {"alias": "Enalapril", "ingredient": "Enalapril", "cat": "antihypertensive"},
        
        # Vitamines
        {"alias": "Vitamine C", "ingredient": "Acide Ascorbique", "cat": "vitamin"},
        {"alias": "Vitamine D", "ingredient": "Cholécalciférol", "cat": "vitamin"},
        {"alias": "Vitamine D3", "ingredient": "Cholécalciférol", "cat": "vitamin"},
        {"alias": "Vitamine B12", "ingredient": "Cobalamine", "cat": "vitamin"},
    ]
    
    for item in aliases:
        db.session.add(ProductAliasModel(
            alias=item["alias"],
            active_ingredient=item["ingredient"],
            category=item.get("cat")
        ))
    
    try:
        db.session.commit()
        print(f"✅ Seeded {len(aliases)} product aliases.")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error seeding aliases: {e}")