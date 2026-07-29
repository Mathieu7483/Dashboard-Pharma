from models.interaction import InteractionModel
from models.product_alias import ProductAliasModel
from utils.text_norm import normalize as _norm

def resolve_ingredient(term: str) -> str:
    """
    Transforme un nom commercial ou une chaîne saisie en son principe actif normalisé.
    Ex: 'Advil' -> 'ibuprofene'
    """
    clean_term = _norm(term).lower().strip()
    
    # 1. Chercher dans les alias
    alias_entry = ProductAliasModel.query.filter(
        ProductAliasModel.alias.ilike(clean_term)
    ).first()
    
    if alias_entry:
        return alias_entry.active_ingredient.lower()
        
    return clean_term

def check_drug_interaction(term_a: str, term_b: str):
    """
    Vérifie l'interaction entre deux termes (noms commerciaux ou molécules).
    """
    ing_a = resolve_ingredient(term_a)
    ing_b = resolve_ingredient(term_b)

    # Recherche dans les 2 sens (A-B ou B-A)
    interaction = InteractionModel.query.filter(
        ((InteractionModel.ingredient_a == ing_a) & (InteractionModel.ingredient_b == ing_b)) |
        ((InteractionModel.ingredient_a == ing_b) & (InteractionModel.ingredient_b == ing_a))
    ).first()

    if interaction:
        return {
            "has_interaction": True,
            "severity": interaction.severity,
            "description": interaction.description,
            "ingredient_a": ing_a,
            "ingredient_b": ing_b
        }

    return {"has_interaction": False}