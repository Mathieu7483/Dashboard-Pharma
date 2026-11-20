"""
Server/core/chatbot/drug_lexicon.py

Reconnaissance des médicaments / substances / classes dans une phrase LIBRE,
à partir d'un lexique construit depuis la base (pas depuis la structure de la phrase).

- Déterministe : même phrase -> même résultat, aucune génération.
- Plus longue correspondance d'abord ("acide acetylsalicylique" avant "acide").
- Tolérance aux fautes de frappe (rapidfuzz) seulement pour les mots longs.
"""
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from utils.text_norm import normalize as _shared_normalize

try:  # rapidfuzz est optionnel : sans lui, correspondance exacte uniquement
    from rapidfuzz import fuzz, process
except ImportError:  # pragma: no cover
    fuzz = process = None

MIN_TERM_LEN = 4          # "fer", "or", "sel"... trop ambigus avec le français courant
MIN_FUZZY_LEN = 6         # pas de correction floue sur les mots courts
FUZZY_CUTOFF = 88         # score rapidfuzz (0-100)
MAX_NGRAM = 5             # longueur max d'un nom composé recherché dans la phrase

# Mots courants qui existent aussi comme noms de médicament/substance : jamais pris seuls
AMBIGUOUS_WORDS = {
    "avec", "pour", "dans", "plus", "entre", "tout", "tous", "sans", "autre", "autres",
    "acide", "huile", "huiles", "sels", "sel", "eau", "sucre", "vitamine", "vitamines",
    "extrait", "poudre", "solution", "comprime", "gelule", "sirop", "creme", "gel",
    "dose", "doses", "risque", "danger", "prix", "stock", "mois", "jour", "jours",
}


@dataclass(frozen=True)
class DrugMention:
    surface: str      # texte tel que tapé par l'utilisateur
    canonical: str    # forme du lexique (normalisée)
    kind: str         # "produit" | "specialite" | "substance" | "classe"
    start: int        # position (en tokens) dans la phrase normalisée
    end: int
    fuzzy: bool = False
    score: float = 100.0


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", _shared_normalize(text or "").lower()).strip()


def _tokens(text: str) -> List[str]:
    """Tokens normalisés ; l'apostrophe sépare les articles : "l'aspirine" -> l, aspirine."""
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", _norm(text))


class DrugLexicon:
    # priorité quand un même terme existe sous plusieurs types
    _KIND_PRIORITY = {"produit": 0, "specialite": 1, "substance": 2, "classe": 3}

    def __init__(self):
        self._terms: Dict[Tuple[str, ...], Tuple[str, str]] = {}   # tokens -> (canonical, kind)
        self._single: List[str] = []                               # mots uniques (pour le flou)
        self._single_map: Dict[str, Tuple[str, str]] = {}

    # -- construction ---------------------------------------------------------
    def add(self, term: str, kind: str, canonical: Optional[str] = None) -> None:
        norm = _norm(term)
        toks = tuple(_tokens(norm))
        if not toks or len(norm) < MIN_TERM_LEN:
            return
        if len(toks) == 1 and toks[0] in AMBIGUOUS_WORDS:
            return
        canon = _norm(canonical) if canonical else norm
        existing = self._terms.get(toks)
        if existing and self._KIND_PRIORITY[existing[1]] <= self._KIND_PRIORITY[kind]:
            return
        self._terms[toks] = (canon, kind)

    def add_alias(self, alias: str, target: str) -> None:
        """Sigle ou nom usuel -> terme du lexique (ex: AINS). Autorisé même très court."""
        toks = tuple(_tokens(alias))
        target_toks = tuple(_tokens(target))
        if toks and target_toks in self._terms:
            self._terms[toks] = self._terms[target_toks]

    def build(self) -> "DrugLexicon":
        self._single_map = {t[0]: v for t, v in self._terms.items() if len(t) == 1}
        self._single = [w for w in self._single_map if len(w) >= MIN_FUZZY_LEN]
        return self

    def __len__(self) -> int:
        return len(self._terms)

    # -- recherche ------------------------------------------------------------
    def find(self, text: str) -> List[DrugMention]:
        toks = _tokens(text)
        mentions: List[DrugMention] = []
        i = 0
        while i < len(toks):
            hit = None
            for n in range(min(MAX_NGRAM, len(toks) - i), 0, -1):          # plus long d'abord
                key = tuple(toks[i:i + n])
                if key in self._terms:
                    canon, kind = self._terms[key]
                    hit = DrugMention(" ".join(key), canon, kind, i, i + n)
                    break
            if hit is None and process is not None:
                hit = self._fuzzy(toks[i], i)
            if hit:
                mentions.append(hit)
                i = hit.end
            else:
                i += 1
        return self._dedupe(mentions)

    def _fuzzy(self, token: str, pos: int) -> Optional[DrugMention]:
        if len(token) < MIN_FUZZY_LEN or token in AMBIGUOUS_WORDS or not self._single:
            return None
        match = process.extractOne(token, self._single, scorer=fuzz.ratio, score_cutoff=FUZZY_CUTOFF)
        if not match:
            return None
        word, score, _ = match
        canon, kind = self._single_map[word]
        return DrugMention(token, canon, kind, pos, pos + 1, fuzzy=True, score=float(score))

    @staticmethod
    def _dedupe(mentions: List[DrugMention]) -> List[DrugMention]:
        seen, out = set(), []
        for m in mentions:
            if m.canonical not in seen:
                seen.add(m.canonical)
                out.append(m)
        return out


# Sigles courants -> libellé de classe du thésaurus ANSM (ajoutés seulement si la classe existe)
CLASS_ALIASES = {
    "ains": "anti-inflammatoires non steroidiens",
    "aine": "anti-inflammatoires non steroidiens",
    "isrs": "inhibiteurs selectifs de la recapture de la serotonine",
    "iec": "inhibiteurs de l'enzyme de conversion",
    "ipp": "antisecretoires inhibiteurs de la pompe a protons",
    "ara ii": "antagonistes des recepteurs de l'angiotensine ii",
    "aod": "anticoagulants oraux",
    "avk": "anticoagulants oraux",
    "statines": "inhibiteurs de l'hmg-coa reductase (statines)",
    "benzodiazepines": "benzodiazepines et apparentes",
}


def build_lexicon_from_db(max_specialites: Optional[int] = None) -> DrugLexicon:
    """Construit le lexique depuis la base (stock, spécialités BDPM, compositions, classes ANSM)."""
    from database.data_manager import db
    from models.product import ProductModel
    from models.specialite import SpecialiteModel
    from models.composition import CompositionModel
    from models.classe_ansm import ClasseMembreModel

    lex = DrugLexicon()

    for name, ingredient in db.session.execute(db.select(ProductModel.name, ProductModel.active_ingredient)):
        if name:
            lex.add(name, "produit")
            lex.add(name.split()[0], "produit", canonical=name.split()[0])
        for part in re.split(r"[,/+;]", ingredient or ""):
            if part.strip() and part.strip().lower() != "n/a":
                lex.add(part, "substance")

    for (search_name,) in db.session.execute(db.select(SpecialiteModel.search_name)):
        if search_name:
            first = search_name.split()[0]          # "DOLIPRANE 1000 mg, comprimé" -> "doliprane"
            lex.add(first, "specialite")

    for (sub,) in db.session.execute(db.select(CompositionModel.denomination_substance).distinct()):
        if sub:
            lex.add(sub, "substance")

    for classe, membre in db.session.execute(
        db.select(ClasseMembreModel.classe_norm, ClasseMembreModel.membre_norm)
    ):
        lex.add(classe, "classe")
        lex.add(membre, "substance")

    for alias, target in CLASS_ALIASES.items():
        lex.add_alias(alias, target)

    return lex.build()
