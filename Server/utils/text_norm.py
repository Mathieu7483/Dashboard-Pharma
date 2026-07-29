import unicodedata


def normalize(s: str) -> str:
    """
    Minuscule + sans accents. Référence UNIQUE pour tout matching de noms de
    médicaments/substances (interactions, alias, référentiel ANSM, NLU).
    Ne pas dupliquer cette logique ailleurs : toute divergence casse le
    matching entre InteractionModel, CompositionModel et le chatbot.
    """
    if not s:
        return ""
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii").lower().strip()