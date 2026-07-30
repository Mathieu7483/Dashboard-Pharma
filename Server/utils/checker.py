from database.data_manager import db
from models.interaction import InteractionModel
from models.interaction_ansm import InteractionAnsmModel
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
    # ÉTAPE 1 : Recherche SQL directe dans la BDD Prioritaire
    # -------------------------------------------------------------
    primary_inter = InteractionModel.query.filter(
        db.or_(
            db.and_(
                InteractionModel.ingredient_a.ilike(norm_a),
                InteractionModel.ingredient_b.ilike(norm_b),
            ),
            db.and_(
                InteractionModel.ingredient_a.ilike(norm_b),
                InteractionModel.ingredient_b.ilike(norm_a),
            ),
        )
    ).first()

    if primary_inter:
        print(f"[DEBUG CHECKER] Interaction trouvée dans BDD Prioritaire : {ing_a} + {ing_b}")
        return {
            "has_interaction": True,
            "severity": primary_inter.severity,
            "description": primary_inter.description,
            "ingredient_a": ing_a,
            "ingredient_b": ing_b,
        }

    # -------------------------------------------------------------
    # ÉTAPE 2 : Recherche SQL directe sur les index ANSM
    # -------------------------------------------------------------
    # A) Correspondance exacte ou partielle sur les colonnes normalisées indexées
    ansm_inter = InteractionAnsmModel.query.filter(
        db.or_(
            # Sens A -> B
            db.and_(
                InteractionAnsmModel.substance_a_norm.ilike(f"%{norm_a}%"),
                InteractionAnsmModel.substance_b_norm.ilike(f"%{norm_b}%"),
            ),
            # Sens B -> A (Inversé)
            db.and_(
                InteractionAnsmModel.substance_a_norm.ilike(f"%{norm_b}%"),
                InteractionAnsmModel.substance_b_norm.ilike(f"%{norm_a}%"),
            ),
        )
    ).first()

    # B) Fallback si substance_a_norm est NULL : recherche sur substance_a / substance_b
    if not ansm_inter:
        ansm_inter = InteractionAnsmModel.query.filter(
            db.or_(
                db.and_(
                    InteractionAnsmModel.substance_a.ilike(f"%{norm_a}%"),
                    InteractionAnsmModel.substance_b.ilike(f"%{norm_b}%"),
                ),
                db.and_(
                    InteractionAnsmModel.substance_a.ilike(f"%{norm_b}%"),
                    InteractionAnsmModel.substance_b.ilike(f"%{norm_a}%"),
                ),
            )
        ).first()

    if ansm_inter:
        print(f"[DEBUG CHECKER] Interaction trouvée dans Thésaurus ANSM : {ing_a} + {ing_b}")
        return {
            "has_interaction": True,
            "severity": ansm_inter.severity or "high",
            "description": ansm_inter.description,
            "ingredient_a": ing_a,
            "ingredient_b": ing_b,
        }

    # Aucun conflit trouvé
    return {
        "has_interaction": False,
        "ingredient_a": ing_a,
        "ingredient_b": ing_b,
    }