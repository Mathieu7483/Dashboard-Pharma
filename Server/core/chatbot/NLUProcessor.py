import spacy

class NLUProcessor:
    """
    Handles Natural Language Understanding by identifying user intents 
    and extracting relevant entities (names, products, etc.).
    """

    def __init__(self):
        # Load the French model for better processing of French names/keywords
        # Make sure to run: python -m spacy download fr_core_news_sm
        try:
            self.nlp = spacy.load("fr_core_news_sm")
        except OSError:
            # Fallback to English if French is not installed
            self.nlp = spacy.load("en_core_web_sm")

    def analyze(self, text):
        doc = self.nlp(text.lower())
        
        # 1. Intent Detection (RESTE IDENTIQUE)
        keywords = {
            "get_client": ["client", "patient", "customer", "dupont"], # Optionnel: ajouter des noms communs si besoin
            "get_doctor": ["docteur", "doctor", "dr", "medecin"],
            "get_product": ["produit", "médicament", "stock", "prix"]
        }
        
        intent = "get_product" # Default
        if any(word in doc.text for word in ["docteur", "dr", "medecin"]):
            intent = "get_doctor"
        elif any(word in doc.text for word in ["client", "patient"]):
            intent = "get_client"

        # 2. Advanced Entity Extraction
        # List of "noise" words to remove from the search query
        noise_words = [
            "cherche", "trouve", "search", "find", "show", "montre", 
            "le", "la", "les", "des", "du", "un", "une", 
            "stock", "de", "prix", "combien", "infos", "informations",
            "client", "docteur", "dr", "produit"
        ]
        
        # We only keep tokens that are NOT in noise_words and are not punctuation
        entity_tokens = [
            token.text for token in doc 
            if token.text not in noise_words and not token.is_punct
        ]
        
        entity = " ".join(entity_tokens).strip()

        return {
            "intent": intent,
            "entity": entity
        }