"""
Server/core/chatbot/NLUProcessor.py
Enhanced NLU optimized for your actual database schema and products
"""

import spacy
import re
from typing import Dict, List

class NLUProcessor:
    """
    Natural Language Understanding with French support.
    
    Key improvements:
    - Multi-entity extraction (for drug interactions)
    - Intent classification with weighted scoring
    - Product name normalization (handles "Doliprane" variants)
    - Symbol detection (+, &) for interaction queries
    """

    def __init__(self):
        # Load French spaCy model
        try:
            self.nlp = spacy.load("fr_core_news_md")
            print("✅ Loaded fr_core_news_md")
        except OSError:
            print("⚠️ Fallback to fr_core_news_sm")
            self.nlp = spacy.load("fr_core_news_sm")
        
        # Intent patterns with priority scoring
        self.intent_patterns = {
            # HIGHEST PRIORITY - Safety critical
            "check_interaction": {
                "keywords": [
                    "incompatible", "interaction", "danger", "mélange", "mélanger",
                    "ensemble", "avec", "combiner", "conflit", "prendre",
                    "compatible", "contre-indication", "associer", "puis-je", "peut-on"
                ],
                "priority": 10
            },
            
            # Stock management
            "get_stock_alerts": {
                "keywords": [
                    "alerte", "manque", "rupture", "stock faible", 
                    "réapprovisionner", "commander", "faible stock",
                    "stock bas", "critique"
                ],
                "priority": 8
            },
            
            # Sales analytics
            "get_sales_summary": {
                "keywords": [
                    "vente", "ventes", "chiffre", "ca", "revenue", 
                    "argent", "vendu", "aujourd'hui", "total",
                    "jour", "journée", "stat", "statistique"
                ],
                "priority": 7
            },
            
            # Prescription info
            "get_prescription_info": {
                "keywords": [
                    "ordonnance", "prescription", "obligatoire", 
                    "rx", "nécessite", "faut", "besoin",
                    "prescrit", "médecin"
                ],
                "priority": 6
            },
            
            # Contact info
            "get_contact_info": {
                "keywords": [
                    "téléphone", "telephone", "numéro", "numero", "tél", "tel", 
                    "joindre", "appeler", "contact", "email", "mail", "adresse"
                ],
                "priority": 9
            },
            
            # People search
            "get_doctor": {
                "keywords": [
                    "docteur", "dr", "médecin", "doctor", 
                    "praticien", "spécialiste"
                ],
                "priority": 5
            },
            
            "get_client": {
                "keywords": [
                    "client", "patient", "customer", 
                    "acheteur", "personne"
                ],
                "priority": 5
            },
            
            # Product queries
            "check_stock": {
                "keywords": [
                    "stock", "combien", "quantité", "disponible", 
                    "reste", "niveau", "dispo", "restant"
                ],
                "priority": 4
            },
            
            "check_price": {
                "keywords": [
                    "prix", "coûte", "coute", "tarif", 
                    "montant", "combien", "euro", "€"
                ],
                "priority": 4
            }
        }
        
        # Stop words to exclude from entity extraction
        self.stop_entities = {
            # Intent keywords
            "docteur", "dr", "médecin", "doctor", "client", "patient",
            "stock", "prix", "price", "alerte", "vente", "ventes",
            "produit", "médicament", "interaction", "avec", "et", "ou",
            
            # Common words
            "cherche", "find", "search", "trouve", "trouver",
            "quel", "quelle", "quoi", "comment", "combien",
            "le", "la", "les", "un", "une", "des", "du", "de",
            
            # Question words
            "est", "sont", "a", "ont", "fait", "faire",
            "puis", "je", "peut", "on", "mélanger", "prendre",
            "compatibles", "danger", "ensemble"
        }

    def analyze(self, text: str) -> Dict:
        """
        Main analysis entry point.
        
        Args:
            text: User's natural language query
            
        Returns:
            {
                "intent": str,
                "entity": str (first entity, legacy),
                "entity_list": List[str] (all entities),
                "confidence": float
            }
        """
        if not text or not text.strip():
            return {
                "intent": "unknown",
                "entity": "",
                "entity_list": [],
                "confidence": 0.0
            }
        
        # Process with spaCy
        doc = self.nlp(text)
        tokens_lemma = [token.lemma_.lower() for token in doc]
        
        # 1. Extract entities (product names, person names)
        entities = self._extract_entities(doc, text)

        if not entities:
            clean_words = [t.text for t in doc if not t.is_stop and not t.is_punct and t.text.lower() not in self.stop_entities]
            if clean_words:
                entities = [clean_words[0].capitalize()]    
        
        # 2. ✨ NEW: Check for interaction patterns FIRST
        is_interaction_query = self._detect_interaction_pattern(text, entities)
        
        # 3. Detect intent with scoring
        intent, confidence = self._detect_intent(tokens_lemma, entities, text)
        
        # 4. ✨ NEW: Override intent if interaction detected
        if is_interaction_query:
            intent = "check_interaction"
            confidence = max(confidence, 0.9)
        
        # Legacy compatibility
        entity_str = entities[0] if entities else ""
        
        return {
            "intent": intent,
            "entity": entity_str,
            "entity_list": entities,
            "confidence": confidence
        }
    
    def _detect_interaction_pattern(self, text: str, entities: List[str]) -> bool:
        """
        ✨ NEW METHOD: Detects if query is about drug interactions.
        
        Patterns detected:
        - "Aspirine + Ibuprofène" (symbol +)
        - "Doliprane & Advil" (symbol &)
        - "Warfarine et Plavix" (conjunction with 2+ entities)
        - "Puis-je mélanger X et Y" (interaction keywords + 2+ entities)
        
        Returns:
            True if interaction query detected
        """
        text_lower = text.lower()
        
        # Pattern 1: Contains interaction symbols (+, &)
        if '+' in text or '&' in text:
            return len(entities) >= 2
        
        # Pattern 2: Conjunction words with 2+ entities
        conjunction_words = ['et', 'avec', 'plus']
        has_conjunction = any(f' {word} ' in f' {text_lower} ' for word in conjunction_words)
        if has_conjunction and len(entities) >= 2:
            return True
        
        # Pattern 3: Interaction keywords + 2+ entities
        interaction_keywords = [
            'interaction', 'compatible', 'mélanger', 'ensemble',
            'danger', 'puis-je', 'peut-on', 'associer', 'incompatible'
        ]
        has_keyword = any(kw in text_lower for kw in interaction_keywords)
        if has_keyword and len(entities) >= 2:
            return True
        
        # Pattern 4: Just 2+ product names in a short query
        # (e.g., "Aspirine Ibuprofène" - likely interaction)
        if len(entities) >= 2 and len(text.split()) <= 4:
            return True
        
        return False
    
    def _extract_entities(self, doc, original_text: str) -> List[str]:
        """
        Extract product, doctor, and client names with smart normalization.
        ✨ UPDATED: Now handles symbol splitting for interactions
        """
        entities = []
        text_lower = original_text.lower()
        
        # --- ✨ NEW PHASE 0: Split by interaction symbols ---
        # "Aspirine + Ibuprofène" → ["Aspirine", "Ibuprofène"]
        if '+' in original_text or '&' in original_text:
            parts = re.split(r'[+&]', original_text)
            for part in parts:
                clean_part = part.strip().strip('.,!?;:')
                if clean_part and clean_part.lower() not in self.stop_entities:
                    if len(clean_part) >= 3:
                        entities.append(clean_part.capitalize())
            
            # If we found entities via symbol split, return them
            if len(entities) >= 2:
                return entities[:5]
    
        # --- PHASE 1: Known product pattern matching ---
        known_products = [
            "paracétamol", "doliprane", "ibuprofène", "ibuprofen",
            "amoxicilline", "aspirine", "oméprazole", "cétirizine",
            "vitamines", "vitamine", "sérum", "hydrocortisone",
            "clarithromycine", "métronidazole", "loratadine",
            "furosémide", "pantoprazole", "insuline", "tramadol",
            "warfarine", "augmentin", "ventoline", "dexaméthasone",
            "azithromycine", "fluconazole", "montelukast", "plavix",
            "clopidogrel", "coumadine"
        ]
    
        for product in known_products:
            if product in text_lower:
                # Check for qualifiers (e.g., "Doliprane Sirop")
                words = text_lower.split()
                for i, word in enumerate(words):
                    if product in word:
                        if i + 1 < len(words) and words[i+1] in ["liquide", "crème", "spray", "sirop"]:
                            full_name = f"{product.capitalize()} {words[i+1].capitalize()}"
                            if full_name not in entities:
                                entities.append(full_name)
                        else:
                            if product.capitalize() not in entities:
                                entities.append(product.capitalize())

        # --- PHASE 2: Universal Entity Extraction (POS Tagging) ---
        for token in doc:
            clean_token = token.text.lower()
        
            # Skip functional words and intent triggers
            if token.is_stop or token.is_punct or clean_token in self.stop_entities:
                continue
            
            # Extract Proper Nouns (PROPN), Nouns (NOUN), and unknown words (X)
            if token.pos_ in ["PROPN", "NOUN", "X"]:
                cap_token = token.text.capitalize()
                if len(cap_token) > 2 and cap_token not in entities:
                    if not token.like_num and not token.is_digit:
                        entities.append(cap_token)
    
        return entities[:5]
    
    def _detect_intent(self, tokens_lemma: List[str], entities: List[str], original_text: str) -> tuple:
        """
        Weighted intent detection with context awareness.
        
        Returns:
            (intent_name, confidence_score)
        """
        intent_scores = {}
        text_lower = ' '.join(tokens_lemma)
        
        # Calculate scores for each intent
        for intent_name, config in self.intent_patterns.items():
            keywords = config["keywords"]
            priority = config["priority"]
            
            # Count keyword matches
            matches = sum(1 for kw in keywords if kw in text_lower)
            
            if matches > 0:
                # Score = matches * priority weight
                base_score = matches * priority
                
                # Boost score for specific patterns
                if intent_name == "check_interaction":
                    if any(word in text_lower for word in ["avec", "ensemble", "et", "mélanger"]):
                        base_score *= 1.5
                
                if intent_name == "get_sales_summary":
                    if "aujourd'hui" in text_lower or "jour" in text_lower:
                        base_score *= 1.3
                
                intent_scores[intent_name] = base_score
        
        # Select highest scoring intent
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            max_score = intent_scores[best_intent]
            
            # Normalize confidence (0.0 to 1.0)
            confidence = min(max_score / 20.0, 1.0)
            
            return best_intent, confidence
        
        # Default: assume product search
        return "get_product", 0.4