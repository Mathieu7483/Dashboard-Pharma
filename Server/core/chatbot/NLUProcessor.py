"""
Server/core/chatbot/NLUProcessor_improved.py
"""

import spacy
import re
from typing import Dict, List

class NLUProcessor:
    """
    Natural Language Understanding with French + English support.
    
    🆕 New features:
    - Bilingual keyword detection (FR/EN)
    - Language auto-detection
    - Greeting and help handlers
    - Improved intent scoring with context awareness
    - Better entity extraction with symbol splitting
    """

    def __init__(self):
        # Load French + English spaCy models
        try:
            self.nlp_fr = spacy.load("fr_core_news_md")
            print("✅ Loaded fr_core_news_md")
        except OSError:
            print("⚠️ Fallback to fr_core_news_sm")
            self.nlp_fr = spacy.load("fr_core_news_sm")
        
        try:
            self.nlp_en = spacy.load("en_core_web_sm")
            print("✅ Loaded en_core_web_sm")
        except OSError:
            print("⚠️ EN model not available - using FR for all")
            self.nlp_en = None
        
        # 🆕 Bilingual greetings
        self.greetings = {
            "fr": ["bonjour", "salut", "bonsoir", "coucou", "hey", "allo"],
            "en": ["hello", "hi", "hey", "good morning", "good evening", "greetings"]
        }
        
        # 🆕 Help keywords
        self.help_keywords = {
            "fr": ["aide", "aider", "comment", "utiliser", "guide", "besoin"],
            "en": ["help", "how", "assist", "guide", "need", "support"]
        }
        
        # 🆕 Bilingual intent patterns
        self.intent_patterns = {
            "check_interaction": {
                "keywords": [
                    # Français
                    "incompatible", "interaction", "danger", "mélange", "mélanger",
                    "ensemble", "avec", "combiner", "conflit", "prendre",
                    "compatible", "contre-indication", "associer", "puis-je", "peut-on",
                    # English
                    "mix", "together", "combine", "compatible", "contraindication",
                    "can i take", "safe", "conflict", "interaction"
                ],
                "priority": 10
            },
            
            "get_stock_alerts": {
                "keywords": [
                    # FR
                    "alerte", "manque", "rupture", "stock faible", 
                    "réapprovisionner", "commander", "faible stock",
                    "stock bas", "critique",
                    # EN
                    "alert", "shortage", "out of stock", "low stock",
                    "reorder", "critical"
                ],
                "priority": 8
            },
            
            "get_sales_summary": {
                "keywords": [
                    # FR
                    "vente", "ventes", "chiffre", "ca", "revenue", 
                    "argent", "vendu", "aujourd'hui", "total",
                    "jour", "journée", "stat", "statistique",
                    # EN
                    "sales", "revenue", "earnings", "sold", 
                    "today", "total", "statistics", "stats"
                ],
                "priority": 7
            },
            
            "get_prescription_info": {
                "keywords": [
                    # FR
                    "ordonnance", "prescription", "obligatoire", 
                    "rx", "nécessite", "faut", "besoin", "prescrit",
                    # EN
                    "prescription", "required", "need", "rx",
                    "prescribed", "mandatory"
                ],
                "priority": 6
            },
            
            "get_contact_info": {
                "keywords": [
                    # FR
                    "téléphone", "telephone", "numéro", "numero", "tél", "tel", 
                    "joindre", "appeler", "contact", "email", "mail", "adresse",
                    # EN
                    "phone", "number", "call", "contact", "email",
                    "address", "reach"
                ],
                "priority": 9
            },
            
            "get_doctor": {
                "keywords": [
                    # FR
                    "docteur", "dr", "médecin", "praticien", "spécialiste",
                    # EN
                    "doctor", "physician", "practitioner", "specialist"
                ],
                "priority": 5
            },
            
            "get_client": {
                "keywords": [
                    # FR
                    "client", "patient", "acheteur", "personne",
                    # EN
                    "client", "customer", "patient", "buyer"
                ],
                "priority": 5
            },
            
            "check_stock": {
                "keywords": [
                    # FR
                    "stock", "combien", "quantité", "disponible", 
                    "reste", "niveau", "dispo", "restant",
                    # EN
                    "stock", "how many", "quantity", "available",
                    "remaining", "level", "inventory"
                ],
                "priority": 4
            },
            
            "check_price": {
                "keywords": [
                    # FR
                    "prix", "coûte", "coute", "tarif", 
                    "montant", "combien", "euro", "€",
                    # EN
                    "price", "cost", "how much", "fee",
                    "rate", "euro", "€", "$"
                ],
                "priority": 4
            },
            
            "list_all": {
                "keywords": [
                    # FR
                    "liste", "tous", "toutes", "affiche", "montre",
                    # EN
                    "list", "all", "show", "display", "every"
                ],
                "priority": 3
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
            "the", "a", "an", "some", "any",
            
            # Question words
            "est", "sont", "a", "ont", "fait", "faire",
            "puis", "je", "peut", "on", "mélanger", "prendre",
            "compatibles", "danger", "ensemble",
            "is", "are", "has", "have", "do", "does",
            "can", "could", "would", "should"
        }

    def _detect_language(self, text: str) -> str:
        """
        🆕 Détecte la langue du texte (fr/en)
        
        Args:
            text: User input
            
        Returns:
            "fr" or "en"
        """
        text_lower = text.lower()
        words = text_lower.split()
        
        # Mots indicateurs français
        fr_indicators = [
            "le", "la", "les", "un", "une", "des", "du", "de",
            "est", "sont", "avec", "pour", "dans", "sur", "qui", "pourquoi"
            "quel", "quelle", "combien", "où", "ordonnance",
            "mais", "ni", "car"
        ]
        
        # Mots indicateurs anglais
        en_indicators = [
            "the", "a", "an", "is", "are", "with", "for",
            "in", "on", "what", "where", "how", "find",
            "search", "get", "show", "prescription"
        ]
        
        fr_count = sum(1 for word in words if word in fr_indicators)
        en_count = sum(1 for word in words if word in en_indicators)
        
        # Si présence de mots-clés spécifiques
        if any(word in text_lower for word in ["find", "search", "get", "show"]):
            en_count += 2
        
        if any(word in text_lower for word in ["cherche", "trouve", "affiche", "montre"]):
            fr_count += 2
        
        return "en" if en_count > fr_count else "fr"

    def analyze(self, text: str) -> Dict:
        """
        Main analysis entry point with language detection.
        
        Args:
            text: User's natural language query
            
        Returns:
            {
                "intent": str,
                "entity": str (first entity, legacy),
                "entity_list": List[str] (all entities),
                "confidence": float,
                "language": str ("fr" or "en")
            }
        """
        if not text or not text.strip():
            return {
                "intent": "unknown",
                "entity": "",
                "entity_list": [],
                "confidence": 0.0,
                "language": "fr"
            }
        
        # 🆕 Detect language
        lang = self._detect_language(text)
        
        # 🆕 Handle greetings
        text_lower = text.lower().strip()
        if any(greeting in text_lower for greeting in self.greetings.get(lang, [])):
            return {
                "intent": "greeting",
                "entity": "",
                "entity_list": [],
                "confidence": 1.0,
                "language": lang
            }
        
        # 🆕 Handle help requests
        if any(kw in text_lower for kw in self.help_keywords.get(lang, [])):
            return {
                "intent": "get_help",
                "entity": "",
                "entity_list": [],
                "confidence": 1.0,
                "language": lang
            }
        
        # Choose appropriate spaCy model
        nlp = self.nlp_fr if lang == "fr" else (self.nlp_en or self.nlp_fr)
        doc = nlp(text)
        tokens_lemma = [token.lemma_.lower() for token in doc]
        
        # Extract entities
        entities = self._extract_entities(doc, text)
        
        if not entities:
            clean_words = [
                t.text for t in doc 
                if not t.is_stop and not t.is_punct 
                and t.text.lower() not in self.stop_entities
            ]
            if clean_words:
                entities = [clean_words[0].capitalize()]
        
        # 🆕 Improved interaction detection
        is_interaction_query = self._detect_interaction_pattern(text, entities)
        
        # Detect intent with scoring
        intent, confidence = self._detect_intent(tokens_lemma, entities, text, lang)
        
        # Override intent if interaction detected
        if is_interaction_query:
            intent = "check_interaction"
            confidence = max(confidence, 0.9)
        
        # Legacy compatibility
        entity_str = entities[0] if entities else ""
        
        return {
            "intent": intent,
            "entity": entity_str,
            "entity_list": entities,
            "confidence": confidence,
            "language": lang
        }
    
    def _detect_interaction_pattern(self, text: str, entities: List[str]) -> bool:
        """
        Detects if query is about drug interactions.
        
        Patterns:
        - "Aspirine + Ibuprofène" (symbol +)
        - "Doliprane & Advil" (symbol &)
        - "Warfarine et Plavix" (conjunction with 2+ entities)
        - "Can I mix X and Y" (interaction keywords + 2+ entities)
        
        Returns:
            True if interaction query detected
        """
        text_lower = text.lower()
        
        # Pattern 1: Contains interaction symbols (+, &)
        if '+' in text or '&' in text:
            return len(entities) >= 2
        
        # Pattern 2: Conjunction words with 2+ entities
        conjunction_words = ['et', 'avec', 'plus', 'and', 'with']
        has_conjunction = any(f' {word} ' in f' {text_lower} ' for word in conjunction_words)
        if has_conjunction and len(entities) >= 2:
            # 🆕 But NOT if there's an explicit command word
            command_words = ['find', 'search', 'cherche', 'trouve', 'list', 'show']
            has_command = any(word in text_lower for word in command_words)
            if not has_command:
                return True
        
        # Pattern 3: Interaction keywords + 2+ entities
        interaction_keywords = [
            'interaction', 'compatible', 'mélanger', 'ensemble',
            'danger', 'puis-je', 'peut-on', 'associer', 'incompatible',
            'mix', 'combine', 'together', 'safe', 'can i take'
        ]
        has_keyword = any(kw in text_lower for kw in interaction_keywords)
        if has_keyword and len(entities) >= 2:
            return True
        
        # Pattern 4: Just 2+ product names in short query
        if len(entities) >= 2 and len(text.split()) <= 4:
            return True
        
        return False
    
    def _extract_entities(self, doc, original_text: str) -> List[str]:
        """
        Extract product, doctor, and client names with smart normalization.
        🆕 Enhanced with symbol splitting and better product matching
        """
        entities = []
        text_lower = original_text.lower()
        
        # 🆕 PHASE 0: Split by interaction symbols
        if '+' in original_text or '&' in original_text:
            parts = re.split(r'[+&]', original_text)
            for part in parts:
                clean_part = part.strip().strip('.,!?;:')
                if clean_part and clean_part.lower() not in self.stop_entities:
                    if len(clean_part) >= 3:
                        entities.append(clean_part.capitalize())
            
            if len(entities) >= 2:
                return entities[:5]
        
        # PHASE 1: Known product pattern matching
        known_products = [
            # Français
            "paracétamol", "doliprane", "ibuprofène", "ibuprofen",
            "amoxicilline", "aspirine", "oméprazole", "cétirizine",
            "vitamines", "vitamine", "sérum", "hydrocortisone",
            "clarithromycine", "métronidazole", "loratadine",
            "furosémide", "pantoprazole", "insuline", "tramadol",
            "warfarine", "augmentin", "ventoline", "dexaméthasone",
            "azithromycine", "fluconazole", "montelukast", "plavix",
            "clopidogrel", "coumadine", "metformine",
            # English/International
            "paracetamol", "acetaminophen", "tylenol", "advil",
            "nurofen", "aspirin", "amoxicillin", "omeprazole"
        ]
        
        for product in known_products:
            if product in text_lower:
                words = text_lower.split()
                for i, word in enumerate(words):
                    if product in word:
                        if i + 1 < len(words) and words[i+1] in ["liquide", "crème", "spray", "sirop", "tablet", "capsule"]:
                            full_name = f"{product.capitalize()} {words[i+1].capitalize()}"
                            if full_name not in entities:
                                entities.append(full_name)
                        else:
                            if product.capitalize() not in entities:
                                entities.append(product.capitalize())
        
        # PHASE 2: Universal Entity Extraction (POS Tagging)
        for token in doc:
            clean_token = token.text.lower()
            
            if token.is_stop or token.is_punct or clean_token in self.stop_entities:
                continue
            
            if token.pos_ in ["PROPN", "NOUN", "X"]:
                cap_token = token.text.capitalize()
                if len(cap_token) > 2 and cap_token not in entities:
                    if not token.like_num and not token.is_digit:
                        entities.append(cap_token)
        
        return entities[:5]
    
    def _detect_intent(self, tokens_lemma: List[str], entities: List[str], 
                      original_text: str, lang: str) -> tuple:
        """
        🆕 Enhanced intent detection with explicit commands and context awareness
        
        Returns:
            (intent_name, confidence_score)
        """
        text_lower = ' '.join(tokens_lemma)
        original_lower = original_text.lower()
        
        # 🆕 RULE 1: Explicit commands (highest priority)
        explicit_commands = {
            # English
            "find product": "get_product",
            "search product": "get_product",
            "find doctor": "get_doctor",
            "find client": "get_client",
            "list all": "list_all",
            "show all": "list_all",
            # French
            "cherche produit": "get_product",
            "trouve produit": "get_product",
            "liste tous": "list_all",
            "affiche tous": "list_all",
        }
        
        for phrase, intent in explicit_commands.items():
            if phrase in original_lower:
                return intent, 0.95
        
        # 🆕 RULE 2: Interaction = 2+ entities + markers (but NO command words)
        interaction_keywords = ["et", "avec", "plus", "+", "&", "together", "with", "and"]
        has_interaction_marker = any(kw in original_lower for kw in interaction_keywords)
        
        if len(entities) >= 2 and has_interaction_marker:
            command_words = ["find", "search", "cherche", "liste", "list", "show"]
            has_command = any(word in original_lower for word in command_words)
            
            if not has_command:
                return "check_interaction", 0.95
        
        # 🆕 RULE 3: Single entity + action word = get_product
        if len(entities) == 1:
            action_words = ["find", "search", "get", "show", "cherche", "trouve", "affiche"]
            if any(word in original_lower for word in action_words):
                return "get_product", 0.85
        
        # RULE 4: Keyword scoring (existing logic enhanced)
        intent_scores = {}
        
        for intent_name, config in self.intent_patterns.items():
            keywords = config["keywords"]
            priority = config["priority"]
            
            matches = sum(1 for kw in keywords if kw in text_lower)
            
            if matches > 0:
                base_score = matches * priority
                
                # Boost scores for specific patterns
                if intent_name == "check_interaction":
                    if any(word in text_lower for word in ["avec", "ensemble", "et", "mélanger", "with", "and"]):
                        base_score *= 1.5
                
                if intent_name == "get_sales_summary":
                    if any(word in text_lower for word in ["aujourd'hui", "jour", "today"]):
                        base_score *= 1.3
                
                if intent_name == "list_all":
                    if any(word in text_lower for word in ["tous", "toutes", "all", "every"]):
                        base_score *= 1.4
                
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