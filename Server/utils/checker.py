import re
from database.data_manager import db
from models.interaction import InteractionModel
from models.interaction_ansm import InteractionAnsmModel
from models.product import ProductModel
from models.specialite import SpecialiteModel
from utils.text_norm import normalize as _norm

COMMON_SALTS = [
    r'\bbromhydrate de\b', r'\bchlorhydrate de\b', r'\bsulfate de\b',
    r'\bsodium\b', r'\bpotassium\b', r'\bmaleate de\b', r'\bdihydrate\b',
    r'\bphosphate de\b', r'\bmesilate de\b', r'\btartrate de\b', r'\bacetate de\b'
]

# Dictionnaire de correspondance DCI -> Classe Thérapeutique ANSM
# (Évite de devoir toucher à la BDD pour les grandes familles thésaurus)
ANSM_CLASS_MAPPING = {
    "citalopram": ["INHIBITEURS SÉLECTIFS DE LA RECAPTURE DE LA SÉROTONINE", "ISRS"],
    "escitalopram": ["INHIBITEURS SÉLECTIFS DE LA RECAPTURE DE LA SÉROTONINE", "ISRS"],
    "fluoxetine": ["INHIBITEURS SÉLECTIFS DE LA RECAPTURE DE LA SÉROTONINE", "ISRS"],
    "paroxetine": ["INHIBITEURS SÉLECTIFS DE LA RECAPTURE DE LA SÉROTONINE", "ISRS"],
    "sertraline": ["INHIBITEURS SÉLECTIFS DE LA RECAPTURE DE LA SÉROTONINE", "ISRS"],
    "tramadol": ["TRAMADOL", "OPIOÏDES"],
    "ibuprofene": ["ANTI-INFLAMMATOIRES NON STÉROÏDIENS", "AINS"],
    "ketoprofene": ["ANTI-INFLAMMATOIRES NON STÉROÏDIENS", "AINS"],
    "aspirine": ["ANTI-INFLAMMATOIRES NON STÉROÏDIENS", "AINS"],
    "krameria": ["HEMOSTATIQUES"],
}


def clean_substance_name(substance: str) -> str:
    text = substance.lower()
    for salt in COMMON_SALTS:
        text = re.sub(salt, '', text)
    return text.strip()


def expand_substance_terms(substance: str) -> list[str]:
    """
    Prend une molécule (ex: 'citalopram') et retourne une liste contenant :
    1. La molécule elle-même
    2. Les classes thérapeutiques ANSM associées
    """
    clean_sub = clean_substance_name(substance)
    terms = [clean_sub]

    # Recherche dans le mapping de classes
    for dci, classes in ANSM_CLASS_MAPPING.items():
        if dci in clean_sub:
            terms.extend(classes)

    return list(set(terms))


def resolve_substances(term: str) -> list[str]:
    """Identifie toutes les substances actives associées à un terme."""
    if not term:
        return []

    clean_term = _norm(term).lower().strip()
    clean_base = re.sub(r'\b\d+\s*(mg|g|ml|mcg|ui|gtt)?\b', '', clean_term).strip()

    # 1. ProductModel (Stock)
    prod = ProductModel.query.filter(
        db.or_(
            ProductModel.name.ilike(f"%{clean_base}%"),
            ProductModel.active_ingredient.ilike(f"%{clean_base}%")
        )
    ).first()

    if prod and prod.active_ingredient and prod.active_ingredient.lower() != 'n/a':
        return _split_ingredients(prod.active_ingredient)

    # 2. SpecialiteModel (ANSM)
    spec = SpecialiteModel.query.filter(
    SpecialiteModel.search_name.ilike(f"%{clean_base}%")
    ).first()

    if spec:
        subs = [
            c.denomination_substance.strip().lower()
            for c in spec.compositions
            if getattr(c, 'nature_composant', 'SA') == 'SA' and c.denomination_substance
        ]
        if subs:
            return subs

    # 3. Fallback
    return [clean_base] if clean_base else []

def check_drug_interaction(term_a: str, term_b: str) -> dict:
    subs_a = resolve_substances(term_a)
    subs_b = resolve_substances(term_b)

    if not subs_a or not subs_b:
        return {
            "has_interaction": False,
            "term_a": term_a,
            "term_b": term_b,
            "substances_a": subs_a,
            "substances_b": subs_b,
            "message": "Impossible de déterminer les substances actives."
        }

    for sa in subs_a:
        # Génère ['citalopram', 'INHIBITEURS SÉLECTIFS DE LA RECAPTURE DE LA SÉROTONINE']
        terms_a = expand_substance_terms(sa)

        for sb in subs_b:
            # Génère ['tramadol', 'OPIOÏDES']
            terms_b = expand_substance_terms(sb)

            # ---------------------------------------------------------
            # ÉTAPE A : Alerte surdosage
            # ---------------------------------------------------------
            clean_sa = clean_substance_name(sa)
            clean_sb = clean_substance_name(sb)
            if _norm(clean_sa).lower() == _norm(clean_sb).lower() and clean_sa != "n/a":
                return {
                    "has_interaction": True,
                    "severity": "Critical",
                    "description": f"Risque de surdosage : les deux traitements contiennent du {clean_sa.title()}.",
                    "substance_a": clean_sa,
                    "substance_b": clean_sb,
                    "term_a": term_a,
                    "term_b": term_b
                }

            # ---------------------------------------------------------
            # ÉTAPE B : Recherche croisée dans le Thésaurus ANSM
            # ---------------------------------------------------------
            for ta in terms_a:
                norm_ta = _norm(ta).lower()
                for tb in terms_b:
                    norm_tb = _norm(tb).lower()

                    # On cherche la présence des mots-clés de A et B dans la BDD ANSM
                    ansm_inter = InteractionAnsmModel.query.filter(
                        db.or_(
                            db.and_(
                                InteractionAnsmModel.substance_a.ilike(f"%{norm_ta}%"),
                                InteractionAnsmModel.substance_b.ilike(f"%{norm_tb}%")
                            ),
                            db.and_(
                                InteractionAnsmModel.substance_a.ilike(f"%{norm_tb}%"),
                                InteractionAnsmModel.substance_b.ilike(f"%{norm_ta}%")
                            )
                        )
                    ).first()

                    if ansm_inter:
                        # Mappe la sévérité ANSM vers un niveau d'alerte exploitable
                        sev = ansm_inter.severity or "Moderate"
                        if sev.lower() in ["low", "faible"]:
                            sev = "Moderate"  # S'assure que l'alerte remonte au front-end

                        return {
                            "has_interaction": True,
                            "severity": sev,
                            "description": ansm_inter.description or f"Interaction détectée entre {clean_sa.title()} et {clean_sb.title()} (Thésaurus ANSM).",
                            "substance_a": clean_sa,
                            "substance_b": clean_sb,
                            "term_a": term_a,
                            "term_b": term_b
                        }

def _split_ingredients(raw_str: str) -> list[str]:
    """Découpe les chaînes multi-composants (ex: 'paracétamol / codéine') selon les séparateurs usuels."""
    if not raw_str:
        return []
    temp_str = raw_str
    for delim in [",", "/", "+", ";"]:
        temp_str = temp_str.replace(delim, "|")
    return [ing.strip().lower() for ing in temp_str.split("|") if ing.strip()]