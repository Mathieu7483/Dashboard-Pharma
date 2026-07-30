from database.data_manager import db
from models.interaction import InteractionModel
from models.interaction_ansm import InteractionAnsmModel  # 👈 Import du filet de sécurité ANSM
from models.product import ProductModel
from models.product_alias import ProductAliasModel
from utils.text_norm import normalize as _norm


def resolve_ingredient(term: str) -> str:
    """Transforme un nom commercial ou alias en sa substance/DCI."""
    if not term:
        return ""

    clean_term = _norm(term).lower().strip()

    # 1. Alias
    alias_entry = ProductAliasModel.query.filter(
        ProductAliasModel.alias.ilike(clean_term)
    ).first()
    if alias_entry and alias_entry.active_ingredient:
        return alias_entry.active_ingredient.strip()

    # 2. Produit principal
    product_entry = ProductModel.query.filter(
        db.or_(
            ProductModel.name.ilike(clean_term),
            ProductModel.active_ingredient.ilike(clean_term),
        )
    ).first()
    if product_entry and product_entry.active_ingredient:
        return product_entry.active_ingredient.strip()

    return term.strip()


def check_drug_interaction(term_a: str, term_b: str):
    """
    Vérifie les interactions sur les deux bases :
    1. Table curée prioritaire (InteractionModel)
    2. Référentiel complet ANSM (InteractionAnsmModel)
    """
    ing_a = resolve_ingredient(term_a)
    ing_b = resolve_ingredient(term_b)

    norm_a = _norm(ing_a).lower()
    norm_b = _norm(ing_b).lower()

    # -------------------------------------------------------------
    # ÉTAPE 1 : Recherche dans la table prioritaire (InteractionModel)
    # -------------------------------------------------------------
    primary_interactions = InteractionModel.query.all()
    for inter in primary_interactions:
        db_a = _norm(inter.ingredient_a).lower()
        db_b = _norm(inter.ingredient_b).lower()

        if (db_a == norm_a and db_b == norm_b) or (
            db_a == norm_b and db_b == norm_a
        ):
            print(f"[DEBUG CHECKER] Interaction trouvée dans la BDD Prioritaire : {ing_a} + {ing_b}")
            return {
                "has_interaction": True,
                "severity": inter.severity,
                "description": inter.description,
                "ingredient_a": ing_a,
                "ingredient_b": ing_b,
            }

    # -------------------------------------------------------------
    # ÉTAPE 2 : Fallback sur le Thésaurus complet (InteractionAnsmModel)
    # -------------------------------------------------------------
    ansm_interactions = InteractionAnsmModel.query.all()
    for inter in ansm_interactions:
        # On utilise substance_a_norm / substance_b_norm si renseignés, sinon normalize(substance)
        db_a = _norm(inter.substance_a_norm or inter.substance_a).lower()
        db_b = _norm(inter.substance_b_norm or inter.substance_b).lower()

        # Match partiel ou exact (ex: 'millepertuis' contenu dans le nom de la substance)
        match_direct = (norm_a in db_a and norm_b in db_b)
        match_inverse = (norm_a in db_b and norm_b in db_a)

        if match_direct or match_inverse:
            print(f"[DEBUG CHECKER] Interaction trouvée dans le Thésaurus ANSM : {ing_a} + {ing_b}")
            return {
                "has_interaction": True,
                "severity": inter.severity or "high",
                "description": inter.description,  # Utilise la property .description déjà définie !
                "ingredient_a": ing_a,
                "ingredient_b": ing_b,
            }

    # Aucun conflit trouvé
    return {
        "has_interaction": False,
        "ingredient_a": ing_a,
        "ingredient_b": ing_b,
    }