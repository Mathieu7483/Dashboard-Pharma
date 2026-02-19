"""
Server/core/chatbot/NLUProcessor_improved.py
"""

import spacy
import re
from typing import Dict, List

class NLUProcessor:
    """
    Natural Language Understanding with French + English support.
    
    - Bilingual keyword detection (FR/EN)
    - Language auto-detection
    - Greeting and help handlers
    - Improved intent scoring with context awareness
    - Better entity extraction with symbol splitting
    """

    def __init__(self):
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
        
        self.greetings = {
            "fr": ["bonjour", "salut", "bonsoir", "coucou", "hey", "allo"],
            "en": ["hello", "hi", "hey", "good morning", "good evening", "greetings"]
        }
        
        # BUG FIX: help keywords now only trigger get_help when NO other meaningful
        # content is present. Moved to a separate weak-signal check in analyze().
        self.help_keywords = {
            "fr": ["aide", "aider", "guide", "besoin d'aide"],
            "en": ["help me", "assist me", "need help", "how do i use"]
        }
        
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
            
            "search ticket": {
                "keywords": [
                    # FR
                    "cherche", "trouve", "recherche", "ticket", "problème",
                    # EN
                    "find", "search", "ticket", "issue", "problem"
                ],
                "priority": 5
            },

            "calendar": {
                "keywords": [
                    # FR
                    "calendrier", "agenda", "planning", "rendez-vous",
                    # EN
                    "calendar", "schedule", "appointments", "agenda"
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
        
        self.stop_entities = {
            "docteur", "dr", "médecin", "doctor", "client", "patient",
            "stock", "prix", "price", "alerte", "vente", "ventes",
            "produit", "médicament", "interaction", "avec", "et", "ou",
            "cherche", "trouve", "recherche", "affiche", "montre",
            "contact", "téléphone", "tel", "email", "adresse",
            "rdv", "rendez-vous", "planning", "agenda", "garde",
            "quel", "quelle", "combien", "où", "est-ce", "que",
            "le", "la", "les", "un", "une", "des", "du", "de"
        }

        self.intent_patterns = {
            "check_interaction": {"keywords": ["incompatible", "interaction", "danger", "mélange", "compatible", "contre-indication"], "priority": 10},
            "get_sales_summary": {"keywords": ["vente", "chiffre", "ca", "revenue", "argent", "statistique"], "priority": 7},
            "get_contact_info": {"keywords": ["téléphone", "numéro", "contact", "email", "adresse", "joindre"], "priority": 9},
            "calendar": {"keywords": ["calendrier", "agenda", "planning", "rdv", "rendez-vous", "garde", "planning"], "priority": 10}, # Upgradé (Bug #4, #7)
            "check_stock": {"keywords": ["stock", "combien", "quantité", "disponible", "reste"], "priority": 6},
            "check_price": {"keywords": ["prix", "coûte", "tarif", "montant", "euro", "€"], "priority": 6},
            "get_help": {"keywords": ["aide", "aider", "comment", "fonctionne"], "priority": 5}
        }

    def _detect_language(self, text: str) -> str:
        text_lower = text.lower()
        fr_indicators = ["le", "la", "les", "est", "avec", "pour", "dans", "ordonnance", "quel", "ou"]
        en_indicators = ["the", "is", "with", "for", "in", "what", "prescription", "or"]
        
        fr_count = sum(1 for word in text_lower.split() if word in fr_indicators)
        en_count = sum(1 for word in text_lower.split() if word in en_indicators)
        return "en" if en_count > fr_count else "fr"

    def analyze(self, text: str) -> Dict:
        if not text or not text.strip():
            return {"intent": "unknown", "entity": "", "entity_list": [], "confidence": 0.0, "language": "fr"}
        
        lang = self._detect_language(text)
        text_lower = text.lower().strip()

        # Greetings (Short messages only)
        if any(g in text_lower for g in self.greetings.get(lang, [])) and len(text_lower.split()) <= 2:
            return {"intent": "greeting", "entity": "", "entity_list": [], "confidence": 1.0, "language": lang}

        nlp = self.nlp_fr if lang == "fr" else (self.nlp_en or self.nlp_fr)
        doc = nlp(text)
        
        # Extraction & Nettoyage des entités (Bug #1)
        entities = self._extract_entities(doc, text)
        entities = self._clean_overlapping_entities(entities) 

        # Intent Detection
        intent, confidence = self._detect_intent(doc, entities, text, lang)
        
        # Sécurity Interaction
        if len(entities) >= 2 and intent not in ["check_stock", "check_price", "get_contact_info"]:
            if any(kw in text_lower for kw in ["+", "&", "avec", "et", "mélanger", "mix"]):
                intent = "check_interaction"
                confidence = 0.95

        return {
            "intent": intent,
            "entity": entities[0] if entities else "",
            "entity_list": entities,
            "confidence": confidence,
            "language": lang
        }
    
    def _detect_interaction_pattern(self, text: str, entities: List[str]) -> bool:
        """
        Detects if query is about drug interactions.
        """
        text_lower = text.lower()
        
        if '+' in text or '&' in text:
            return len(entities) >= 2
        
        conjunction_words = ['et', 'avec', 'plus', 'and', 'with']
        has_conjunction = any(f' {word} ' in f' {text_lower} ' for word in conjunction_words)
        if has_conjunction and len(entities) >= 2:
            command_words = ['find', 'search', 'cherche', 'trouve', 'list', 'show']
            has_command = any(word in text_lower for word in command_words)
            if not has_command:
                return True
        
        interaction_keywords = [
            'interaction', 'compatible', 'mélanger', 'ensemble',
            'danger', 'puis-je', 'peut-on', 'associer', 'incompatible',
            'mix', 'combine', 'together', 'safe', 'can i take'
        ]
        has_keyword = any(kw in text_lower for kw in interaction_keywords)
        if has_keyword and len(entities) >= 2:
            return True
        
        if len(entities) >= 2 and len(text.split()) <= 4:
            return True
        
        return False
    
    def _extract_entities(self, doc, original_text: str) -> List[str]:
        entities = []
        text_lower = original_text.lower()
        
        # 1. Gestion des symboles (ton code existant)
        if any(sym in original_text for sym in ['+', '&']):
            parts = re.split(r'[+&]', original_text)
            for part in parts:
                clean = part.strip().strip('.,!?;:')
                if len(clean) >= 3 and clean.lower() not in self.stop_entities:
                    entities.append(clean) # On ne capitalise plus de force ici
            if len(entities) >= 2: return entities

        # 2. Extraction par POS Tagging
        for token in doc:
            t_low = token.text.lower()
            if t_low in self.stop_entities or token.is_punct or token.like_num:
                continue
            
            # On accepte PROPN, NOUN et même les mots "inconnus" s'ils sont assez longs
            if token.pos_ in ["PROPN", "NOUN", "X", "ADJ"] and len(t_low) > 2:
                entities.append(token.text) # On garde le texte original !

        # 3. FALLBACK : Si SpaCy n'a rien trouvé (ex: "godalier" ignoré)
        if not entities:
            words = original_text.split()
            for w in words:
                w_clean = w.lower().strip('.,!?;:')
                if len(w_clean) > 2 and w_clean not in self.stop_entities:
                    entities.append(w)

        return entities
    

    def _clean_overlapping_entities(self, entities: List[str]) -> List[str]:
        """ Supprime les entités incluses dans d'autres (ex: 'Aspirine' vs 'Aspirine 300mg') """
        if not entities: return []
        # Trier par longueur décroissante
        sorted_ents = sorted(list(set(entities)), key=len, reverse=True)
        final = []
        for ent in sorted_ents:
            if not any(ent in other for other in final):
                final.append(ent)
        return final
    

    def _detect_intent(self, doc, entities: List[str], original_text: str, lang: str) -> tuple:
        text_lower = original_text.lower()
        tokens_lemma = [t.lemma_.lower() for t in doc]
        
        if any(kw in text_lower for kw in ["rdv", "rendez-vous", "garde", "planning", "agenda"]):
            return "calendar", 0.95

        intent_scores = {}
        for name, config in self.intent_patterns.items():
            score = sum(2 for kw in config["keywords"] if kw in text_lower or kw in tokens_lemma)
            if score > 0:
                intent_scores[name] = score * config["priority"]

        if intent_scores:
            best = max(intent_scores, key=intent_scores.get)
            return best, min(intent_scores[best] / 20.0, 1.0)
        
        return "get_product", 0.4