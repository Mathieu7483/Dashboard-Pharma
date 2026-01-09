import spacy

class NLUProcessor:
    """
    Handles Natural Language Understanding (NLU).
    Improved to detect interactions based on context and multiple entities.
    """

    def __init__(self):
        # Professional-grade French model
        try:
            self.nlp = spacy.load("fr_core_news_md")
        except OSError:
            self.nlp = spacy.load("fr_core_news_sm")

    def analyze(self, text):
        """
        Analyzes input to determine intent and extract entities.
        """
        doc = self.nlp(text)
        tokens_lemma = [token.lemma_.lower() for token in doc]
        
        # 1. PRIMARY ENTITY EXTRACTION
        # We extract nouns and proper nouns that are not stop words
        # This is crucial for detecting if the user mentions MULTIPLE products
        intent_keywords = [
            "docteur", "dr", "médecin", "doctor", "client", "patient", 
            "customer", "stock", "prix", "price", "alerte", "vente"
        ]
        
        found_entities = []
        for token in doc:
            clean_lemma = token.lemma_.lower()
            if not token.is_stop and not token.is_punct:
                if clean_lemma not in intent_keywords:
                    if token.pos_ in ["PROPN", "NOUN"]:
                        found_entities.append(token.text)

        # 2. INTENT DETECTION LOGIC
        intent = "get_product"  # Default fallback

        # A. Interaction Detection (The fix for your Advil/Aspirine issue)
        # If the user uses "avec", "et", or mentions 2+ products
        if any(w in tokens_lemma for w in ["incompatible", "conflit", "danger", "mélange", "interaction", "avec"]):
            intent = "check_interaction"
        elif len(found_entities) >= 2:
            intent = "check_interaction"

        # B. Stock Alerts
        elif any(w in tokens_lemma for w in ["alerte", "manquer", "rupture", "stock"]):
            intent = "get_stock_alerts"

        # C. Sales Summary
        elif any(w in tokens_lemma for w in ["vente", "chiffre", "ca", "argent", "vendre"]):
            intent = "get_sales_summary"

        # D. Medical Staff / Clients
        elif any(w in tokens_lemma for w in ["docteur", "dr", "médecin", "doctor"]):
            intent = "get_doctor"
        elif any(w in tokens_lemma for w in ["client", "patient", "customer"]):
            intent = "get_client"

        # E. Prescription
        elif any(w in tokens_lemma for w in ["ordonnance", "prescription", "obligatoire"]):
            intent = "get_prescription_info"

        # 3. DEBUG OUTPUT
        entity_str = " ".join(found_entities).strip()
        print(f"--- NLU DEBUG ---")
        print(f"Input: '{text}'")
        print(f"Found Entities: {found_entities}")
        print(f"Detected Intent: '{intent}'")
        print(f"-----------------")

        return {
            "intent": intent,
            "entity": entity_str,
            "entity_list": found_entities # We return a list for easier processing in the Engine
        }