import spacy

class NLUProcessor:
    """
    NLU unit responsible for Intent Recognition and Entity Extraction
    using the spaCy French model.
    """

    def __init__(self):
        try:
            # Loading the medium French model for better accuracy than 'sm'
            self.nlp = spacy.load("fr_core_news_md")
        except OSError:
            # Professional error handling if the model is missing on the PC
            raise OSError("Model 'fr_core_news_md' not found. Please run: python -m spacy download fr_core_news_md")

    def analyze(self, text):
        """
        Processes raw text to extract the user's goal and the subject.
        """
        doc = self.nlp(text)
        intent = "unknown"
        entity = None

        # 1. ENTITY EXTRACTION
        # We look for Proper Nouns (PROPN) or Nouns (NOUN) as potential search terms
        for token in doc:
            if token.pos_ in ["PROPN", "NOUN"] and len(token.text) > 2:
                entity = token.text
                break

        # 2. INTENT DETECTION (Keyword-based mapping)
        text_lower = text.lower()
        
        # Product detection keywords
        if any(kw in text_lower for kw in ["produit", "médicament", "stock", "prix", "doliprane"]):
            intent = "get_product"
        # Doctor detection keywords
        elif any(kw in text_lower for kw in ["docteur", "médecin", "dr", "spécialité"]):
            intent = "get_doctor"
        # Client detection keywords
        elif any(kw in text_lower for kw in ["client", "patient"]):
            intent = "get_client"
            
        # 3. SMART FALLBACK
        # If no specific keyword is found but an entity is present (like just "Doliprane")
        # we default the search to products as it's the most common query.
        if intent == "unknown" and entity:
            intent = "get_product"

        return {
            "intent": intent,
            "entity": entity
        }