"""
Server/utils/seed_aliases.py
Seeds the product_aliases table with commercial name mappings
"""

from database.data_manager import db
from models.product_alias import ProductAliasModel

def seed_product_aliases():
    """
    Populate the product_aliases table with common commercial names.
    """
    if ProductAliasModel.query.first():
        print("Product aliases already seeded.")
        return
    
    # NOTE: Les ingrédients actifs sont normalisés (minuscules, sans accents)
    # pour matcher avec la table interactions et le CSV produits.
    aliases = [
        # Anti-inflammatoires / Antalgiques
        {"alias": "Aspirine", "ingredient": "acide acetylsalicylique", "cat": "analgesic"},
        {"alias": "Aspegic", "ingredient": "acide acetylsalicylique", "cat": "analgesic"},
        {"alias": "Kardégic", "ingredient": "acide acetylsalicylique", "cat": "analgesic"},
        
        {"alias": "Ibuprofène", "ingredient": "ibuprofene", "cat": "analgesic"},
        {"alias": "Advil", "ingredient": "ibuprofene", "cat": "analgesic"},
        {"alias": "Nurofen", "ingredient": "ibuprofene", "cat": "analgesic"},
        {"alias": "Spedifen", "ingredient": "ibuprofene", "cat": "analgesic"},
        
        {"alias": "Paracétamol", "ingredient": "paracetamol", "cat": "analgesic"},
        {"alias": "Doliprane", "ingredient": "paracetamol", "cat": "analgesic"},
        {"alias": "Dafalgan", "ingredient": "paracetamol", "cat": "analgesic"},
        {"alias": "Efferalgan", "ingredient": "paracetamol", "cat": "analgesic"},
        {"alias": "Tylenol", "ingredient": "paracetamol", "cat": "analgesic"},
        
        # Antibiotiques
        {"alias": "Amoxicilline", "ingredient": "amoxicilline", "cat": "antibiotic"},
        {"alias": "Clamoxyl", "ingredient": "amoxicilline", "cat": "antibiotic"},
        {"alias": "Augmentin", "ingredient": "amoxicilline/clavulanate", "cat": "antibiotic"},
        
        {"alias": "Azithromycine", "ingredient": "azithromycine", "cat": "antibiotic"},
        {"alias": "Zithromax", "ingredient": "azithromycine", "cat": "antibiotic"},
        
        {"alias": "Clarithromycine", "ingredient": "clarithromycine", "cat": "antibiotic"},
        {"alias": "Zeclar", "ingredient": "clarithromycine", "cat": "antibiotic"},
        
        # Anticoagulants
        {"alias": "Warfarine", "ingredient": "warfarine", "cat": "anticoagulant"},
        {"alias": "Coumadine", "ingredient": "warfarine", "cat": "anticoagulant"},
        {"alias": "Clopidogrel", "ingredient": "clopidogrel", "cat": "anticoagulant"},
        {"alias": "Plavix", "ingredient": "clopidogrel", "cat": "anticoagulant"},
        {"alias": "Rivaroxaban", "ingredient": "rivaroxaban", "cat": "anticoagulant"},
        {"alias": "Xarelto", "ingredient": "rivaroxaban", "cat": "anticoagulant"},
        
        # IPP
        {"alias": "Oméprazole", "ingredient": "omeprazole", "cat": "ppi"},
        {"alias": "Mopral", "ingredient": "omeprazole", "cat": "ppi"},
        {"alias": "MopralPro", "ingredient": "omeprazole", "cat": "ppi"},
        
        # Diurétiques / Corticoïdes
        {"alias": "Furosémide", "ingredient": "furosemide", "cat": "diuretic"},
        {"alias": "Prednisone", "ingredient": "prednisone", "cat": "corticoid"},
        {"alias": "Cortancyl", "ingredient": "prednisone", "cat": "corticoid"},
        
        # Vitamines
        {"alias": "Vitamine C", "ingredient": "acide ascorbique", "cat": "vitamin"},
        {"alias": "Vitamine D", "ingredient": "cholecalciferol", "cat": "vitamin"},
        {"alias": "Vitamine D3", "ingredient": "cholecalciferol", "cat": "vitamin"},
    ]
    
    for item in aliases:
        db.session.add(ProductAliasModel(
            alias=item["alias"],
            active_ingredient=item["ingredient"],
            category=item.get("cat")
        ))
    
    try:
        db.session.commit()
        print(f"✅ Seeded {len(aliases)} product aliases (normalized).")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error seeding aliases: {e}")