import spacy

class NLUProcessor:
    """
    Handles Natural Language Understanding by identifying user intents 
    and extracting relevant entities (names, products, etc.).
    """

    def __init__(self):
        # Using the medium French model for better accuracy in entity recognition
        try:
            self.nlp = spacy.load("fr_core_news_md")
        except OSError:
            # Fallback to the small model if the medium one is missing
            self.nlp = spacy.load("fr_core_news_sm")

    def analyze(self, text):
        """
        Analyzes the input text to extract intent and the specific entity name.
        """
        # Process the text without lowercasing first to help spaCy identify Proper Nouns
        doc = self.nlp(text)
        
        # 1. Intent Detection using Lemmatization (root form of words)
        intent = "get_product"  # Default fallback intent
        tokens_lemma = [token.lemma_.lower() for token in doc]
        
        # Checking for doctor or client keywords in their base form
        if any(w in tokens_lemma for w in ["docteur", "dr", "médecin", "doctor"]):
            intent = "get_doctor"
        elif any(w in tokens_lemma for w in ["client", "patient", "customer"]):
            intent = "get_client"

        # 2. Advanced Entity Extraction
        # Words strictly related to navigation/intents that should never be searched in DB
        intent_keywords = [
            "docteur", "dr", "médecin", "doctor", 
            "client", "patient", "customer", 
            "infos", "info", "information", "stock", "prix", "price"
        ]
        
        # Filter logic:
        # - Not a spaCy stop word (le, la, sur, etc.)
        # - Not a punctuation mark
        # - Not in our intent keywords list
        # - Must be a Noun, Proper Noun or Adjective
        entity_parts = []
        for token in doc:
            clean_lemma = token.lemma_.lower()
            if not token.is_stop and not token.is_punct:
                if clean_lemma not in intent_keywords:
                    if token.pos_ in ["PROPN", "NOUN", "ADJ"]:
                        entity_parts.append(token.text)

        entity = " ".join(entity_parts).strip()

        # Debugging output for the terminal
        print(f"--- NLU DEBUG ---")
        print(f"Input: '{text}'")
        print(f"Extracted Entity: '{entity}'")
        print(f"Detected Intent: '{intent}'")
        print(f"-----------------")

        return {
            "intent": intent,
            "entity": entity
        }