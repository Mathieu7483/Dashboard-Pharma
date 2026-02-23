"""
Server/core/chatbot/NLUProcessor.py
Bilingual NLU (FR/EN) for Pharmacy Management
"""

import re
import unicodedata
from typing import Dict, List
import spacy


class NLUProcessor:

    def __init__(self):
        # -- SpaCy Models Loading ----------------------------------------------
        try:
            self.nlp_fr = spacy.load("fr_core_news_md")
            print("✅ Loaded fr_core_news_md")
        except OSError:
            print("⚠️  Fallback to fr_core_news_sm")
            self.nlp_fr = spacy.load("fr_core_news_sm")

        try:
            self.nlp_en = spacy.load("en_core_web_sm")
            print("✅ Loaded en_core_web_sm")
        except OSError:
            print("⚠️  EN model not available — using FR for all")
            self.nlp_en = None

        # -- Greetings ---------------------------------------------------------
        self.greetings = {
            "fr": ["bonjour", "salut", "bonsoir", "coucou", "salutations"],
            "en": ["hello", "hi", "good morning", "good evening", "greetings"]
        }

        # -- Help (short messages only) ----------------------------------------
        self.help_keywords = {
            "fr": ["aide", "aider", "guide", "besoin d'aide", "comment utiliser"],
            "en": ["help me", "assist me", "need help", "how do i use"]
        }

        # -- Temporal keywords for calendar ------------------------------------
        self.temporal_keywords = {
            "demain", "aujourd'hui", "hier",
            "semaine", "prochaine", "prochain",
            "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
            "tomorrow", "today", "yesterday", "week", "next",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
        }

        # -- Stop entities: words that should NEVER be extracted as entities ---
        self.stop_entities = {
            # Intent-keywords FR
            "docteur", "medecin", "praticien", "specialiste",
            "client", "patient", "acheteur",
            "stock", "prix", "alerte", "rupture",
            "vente", "ventes", "chiffre", "statistique",
            "ordonnance", "prescription",
            "contact", "telephone", "numero", "email", "adresse",
            "interaction", "danger", "melange", "compatible",
            "rdv", "rendez-vous", "garde", "planning", "agenda", "calendrier",
            "ticket", "probleme",
            "produit", "medicament",
            # Intent-keywords EN
            "doctor", "physician", "specialist",
            "customer", "buyer",
            "price", "alert", "shortage",
            "sales", "revenue",
            "prescription", "phone", "address",
            "calendar", "schedule", "appointment", "meeting",
            # Verbs / Command words
            "cherche", "trouve", "trouver", "recherche", "affiche", "montre",
            "find", "search", "show", "get", "list",
            # Function words (Stop words) FR
            "le", "la", "les", "un", "une", "des", "du", "de", "d",
            "ce", "cet", "cette", "ces", "mon", "ma", "mes", "son", "sa", "ses",
            "et", "ou", "avec", "pour", "dans", "sur", "sous", "par",
            "est", "sont", "a", "ont", "ai", "as",
            "je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles",
            "me", "te", "se", "moi", "toi", "lui",
            "que", "qui", "quoi", "quel", "quelle", "quels",
            "comment", "combien", "pourquoi", "quand",
            "puis", "peut", "faut", "faire", "prendre",
            # Function words EN
            "the", "an", "some", "any",
            "is", "are", "was", "were", "has", "have", "do", "does",
            "can", "could", "would", "should", "may", "might",
            "i", "you", "he", "she", "we", "they", "it",
        }

        # -- Known products (direct detection) ---------------------------------
        self.known_products: set = set()

        # -- Intent patterns with priorities -----------------------------------
        self.intent_patterns = {

            # Drug-drug interactions
            "check_interaction": {
                "keywords": [
                    "incompatible", "interaction", "melange", "melanger",
                    "ensemble", "combiner", "conflit",
                    "compatible", "contre-indication", "associer", "puis-je", "peut-on",
                    "mix", "together", "combine", "contraindication", "can i take", "conflict",
                ],
                "priority": 10
            },

            # Low stock / Shortage alerts
            "get_stock_alerts": {
                "keywords": [
                    "alerte", "manque", "rupture", "stock faible", "faible stock",
                    "reapprovisionner", "commander", "stock bas", "critique",
                    "alert", "shortage", "out of stock", "low stock", "reorder", "critical",
                ],
                "priority": 8
            },

            # Sales and statistics
            "get_sales_summary": {
                "keywords": [
                    "vente", "ventes", "chiffre", "ca", "revenue",
                    "argent", "vendu", "total", "stat", "statistique",
                    "sales", "earnings", "sold", "statistics", "stats",
                ],
                "priority": 7
            },

            # Prescription info
            "get_prescription_info": {
                "keywords": [
                    "ordonnance", "prescription", "obligatoire",
                    "necessite", "prescrit",
                    "required", "prescribed", "mandatory",
                ],
                "priority": 6
            },

            # Contact details
            "get_contact_info": {
                "keywords": [
                    "telephone", "numero", "tel",
                    "joindre", "appeler", "email", "mail", "adresse",
                    "phone", "number", "call", "address", "reach",
                ],
                "priority": 9
            },

            # Doctor info
            "get_doctor": {
                "keywords": [
                    "docteur", "dr", "medecin", "praticien", "specialiste",
                    "doctor", "physician", "practitioner", "specialist",
                ],
                "priority": 5
            },

            # Client / Patient info
            "get_client": {
                "keywords": [
                    "client", "patient", "acheteur",
                    "customer", "buyer",
                ],
                "priority": 5
            },

            # Product stock level
            "check_stock": {
                "keywords": [
                    "stock", "combien", "quantite", "disponible",
                    "reste", "niveau", "dispo", "restant", "inventaire",
                    "how many", "quantity", "available", "remaining", "level", "inventory",
                ],
                "priority": 6
            },

            # Price check
            "check_price": {
                "keywords": [
                    "prix", "coute", "tarif",
                    "montant", "euro",
                    "price", "cost", "how much", "fee", "rate",
                ],
                "priority": 6
            },

            # Support tickets
            "search_ticket": {
                "keywords": [
                    "ticket", "incident",
                    "issue", "problem",
                ],
                "priority": 7
            },

            # Calendar / Planning
            "calendar": {
                "keywords": [
                    "calendrier", "agenda", "planning", "rendez-vous", "rdv",
                    "garde", "reunion", "seance", "evenement",
                    "calendar", "schedule", "appointments", "meeting", "event", "shift",
                ],
                "priority": 9
            },

            # Listing all items
            "list_all": {
                "keywords": [
                    "liste", "tous", "toutes", "affiche", "montre",
                    "list", "all", "show", "display", "every",
                ],
                "priority": 3
            },
        }

    def load_products_from_db(self) -> None:
        """
        Loads known products from database and populates the entity dictionary.
        - Includes full name, first word, and normalized (no accent) versions.
        """
        from models.product import ProductModel
        from database.data_manager import db

        def _norm(s: str) -> str:
            return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii").lower()

        try:
            rows = db.session.execute(
                db.select(ProductModel.name, ProductModel.active_ingredient)
            ).all()

            new_set: set = set()
            for name, ingredient in rows:
                if name:
                    name_low  = name.lower().strip()
                    name_norm = _norm(name)
                    # Full name: "Doliprane 1000mg"
                    new_set.add(name_low)
                    new_set.add(name_norm)
                    # First word only: "Doliprane"
                    first_word = name_low.split()[0] if name_low.split() else name_low
                    new_set.add(first_word)
                    new_set.add(_norm(first_word))
                if ingredient:
                    ing_low  = ingredient.lower().strip()
                    ing_norm = _norm(ingredient)
                    new_set.add(ing_low)
                    new_set.add(ing_norm)
                    # Active ingredient first word: "Acide" from "Acide acetylsalicylique"
                    first_ing = ing_low.split()[0] if ing_low.split() else ing_low
                    new_set.add(first_ing)
                    new_set.add(_norm(first_ing))

            self.known_products = new_set
            print(f"✅ NLU: {len(new_set)} product entries loaded from DB")

        except Exception as e:
            print(f"⚠️  NLU: Could not load products from DB: {e}")
            # Minimal fallback if DB is unreachable
            self.known_products = {
                "doliprane", "aspirine", "ibuprofene",
                "paracetamol", "amoxicilline", "omeprazole",
            }

    # ==========================================================================
    # 🔍 MAIN ENTRY POINT
    # ==========================================================================

    def analyze(self, text: str) -> Dict:
        """
        Analyzes the text and returns a dictionary containing:
        intent, entity, entity_list, confidence, and detected language.
        """
        if not text or not text.strip():
            return {"intent": "unknown", "entity": "", "entity_list": [], "confidence": 0.0, "language": "fr"}

        lang       = self._detect_language(text)
        text_lower = text.lower().strip()

        # 👋 Greeting detection - high priority, checked first
        if self._is_greeting(text_lower, lang):
            return {"intent": "greeting", "entity": "", "entity_list": [], "confidence": 1.0, "language": lang}

        # ❓ Help request - only if the message is short (<= 5 words)
        if self._is_help_request(text_lower, lang):
            return {"intent": "get_help", "entity": "", "entity_list": [], "confidence": 1.0, "language": lang}

        # 📅 Calendar query - immediate short-circuit if calendar keywords are present
        if self._is_calendar_query(text_lower):
            entities = self._extract_calendar_entities(text_lower)
            return {
                "intent": "calendar",
                "entity": entities[0] if entities else "",
                "entity_list": entities,
                "confidence": 0.95,
                "language": lang
            }

        # 🧠 Main NLU Pipeline
        nlp = self.nlp_fr if lang == "fr" else (self.nlp_en or self.nlp_fr)
        doc = nlp(text)

        entities       = self._extract_entities(doc, text)
        intent, conf   = self._detect_intent(doc, entities, text, lang)

        # 💊 Interaction - only if EXPLICIT markers are found in the text
        if intent != "check_interaction" and self._has_explicit_interaction_markers(text_lower, entities):
            intent = "check_interaction"
            conf   = 0.95

        return {
            "intent":      intent,
            "entity":      entities[0] if entities else "",
            "entity_list": entities,
            "confidence":  conf,
            "language":    lang
        }

    # ==========================================================================
    # ⚡ QUICK DETECTIONS (Before NLU Pipeline)
    # ==========================================================================

    def _is_greeting(self, text_lower: str, lang: str) -> bool:
        """Returns True if message is short AND starts with a greeting."""
        if len(text_lower.split()) > 4:
            return False
        all_greets = self.greetings.get("fr", []) + self.greetings.get("en", [])
        return any(text_lower.startswith(g) or text_lower == g for g in all_greets)

    def _is_help_request(self, text_lower: str, lang: str) -> bool:
        """Returns True if message is short (<= 5 words) and contains help keywords."""
        if len(text_lower.split()) > 5:
            return False
        return any(kw in text_lower for kw in self.help_keywords.get(lang, []))

    def _is_calendar_query(self, text_lower: str) -> bool:
        """Returns True if text contains obvious calendar/schedule triggers."""
        calendar_triggers = {
            "rdv", "r.d.v", "rendez-vous", "garde", "gardes",
            "planning", "agenda", "calendrier",
            "calendar", "schedule", "shift", "appointment",
        }
        words = set(re.split(r'\W+', text_lower))
        return bool(words & calendar_triggers)

    def _extract_calendar_entities(self, text_lower: str) -> List[str]:
        """Extracts event types and temporal keywords from calendar queries."""
        entities = []
        words    = re.split(r'\W+', text_lower)

        for kw in ["rdv", "garde", "reunion"]:
            if kw in words:
                entities.append(kw)

        for kw in self.temporal_keywords:
            if kw in text_lower:
                entities.append(kw)

        return entities if entities else []

    def _has_explicit_interaction_markers(self, text_lower: str, entities: List[str]) -> bool:
        """
        Interaction is valid ONLY if:
        1. At least 2 distinct entities in text
        2. AND an explicit marker (symbol, keyword, conjunction)
        """
        if len(entities) < 2:
            return False

        # Strong symbols
        if "+" in text_lower or "&" in text_lower:
            return True

        # Explicit interaction keywords
        interaction_keywords = [
            "interaction", "compatible", "incompatible", "melanger", "melange",
            "ensemble", "danger", "puis-je", "peut-on", "associer",
            "mix", "combine", "together", "safe to take", "can i take",
        ]
        if any(kw in text_lower for kw in interaction_keywords):
            return True

        # Conjunction + 2 entities (not if a command word is present)
        conjunctions  = ["et", "avec", "plus", "and", "with"]
        command_words = ["find", "search", "cherche", "liste", "list", "show", "montre", "affiche"]
        has_conj      = any(f" {w} " in f" {text_lower} " for w in conjunctions)
        has_command   = any(w in text_lower for w in command_words)

        return has_conj and not has_command

    # ==========================================================================
    # 🏷️ ENTITY EXTRACTION
    # ==========================================================================

    def _normalize(self, text: str) -> str:
        """Removes accents for matching (e.g., 'ibuprofène' -> 'ibuprofene')."""
        return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii").lower()

    def _extract_entities(self, doc, original_text: str) -> List[str]:
        """
        Extracts proper names and products from text.
        Order: symbols → known products → POS tagging → fallback
        """
        text_lower      = original_text.lower()
        text_normalized = self._normalize(original_text)
        entities        = []

        # 1️⃣ Split by symbols + / &
        if "+" in original_text or "&" in original_text:
            parts = re.split(r"[+&]", original_text)
            for part in parts:
                clean = part.strip().strip(".,!?;:")
                if len(clean) >= 3 and clean.lower() not in self.stop_entities:
                    entities.append(clean.strip())
            if len(entities) >= 2:
                return self._deduplicate_entities(entities)

        # 2️⃣ Known products lookup (Dictionary)
        for product in self.known_products:
            product_norm = self._normalize(product)
            # Match in original text (with accents) OR normalized (without)
            search_text = text_lower if product in text_lower else text_normalized
            search_prod = product    if product in text_lower else product_norm

            if search_prod in search_text:
                pattern = rf"\b{re.escape(search_prod)}\b\s*(\d+\s*mg|\d+\s*g)?"
                match   = re.search(pattern, search_text)
                if match:
                    # Get original word from source text (keep accents)
                    start, end = match.start(), match.end()
                    cap = original_text[start:end].strip().capitalize()
                    if cap and cap not in entities:
                        entities.append(cap)

        # 3️⃣ SpaCy POS Tagging (Proper nouns AND long common nouns as medications)
        for token in doc:
            t_low = token.text.lower()
            if t_low in self.stop_entities or token.is_punct or token.like_num:
                continue
            # NOUN accepted if >= 4 chars (meds are often tagged as NOUN instead of PROPN)
            is_relevant = (token.pos_ in ("PROPN", "X")) or (token.pos_ == "NOUN" and len(t_low) >= 4)
            if is_relevant and len(t_low) > 2:
                cap = token.text.capitalize()
                if cap not in entities:
                    entities.append(cap)

        # 4️⃣ Fallback: First non-stop word if nothing found
        if not entities:
            for token in doc:
                t_low = token.text.lower()
                if not token.is_stop and not token.is_punct and t_low not in self.stop_entities and len(t_low) > 2:
                    entities.append(token.text.capitalize())
                    break

        return self._deduplicate_entities(entities)

    def _deduplicate_entities(self, entities: List[str]) -> List[str]:
        """Removes entities contained within others (e.g., 'Aspirin' vs 'Aspirin 300mg')."""
        sorted_ents = sorted(set(entities), key=len, reverse=True)
        final       = []
        for ent in sorted_ents:
            if not any(ent.lower() in other.lower() for other in final):
                final.append(ent)
        return final[:5]

    # ==========================================================================
    # 🎯 INTENT DETECTION
    # ==========================================================================

    def _detect_intent(self, doc, entities: List[str], original_text: str, lang: str) -> tuple:
        text_lower   = original_text.lower()
        tokens_lemma = {token.lemma_.lower() for token in doc}

        # Rule 1: Explicit commands (Absolute priority)
        explicit_commands = {
            "find product":    "get_product",
            "search product":  "get_product",
            "cherche produit": "get_product",
            "trouve produit":  "get_product",
            "find doctor":     "get_doctor",
            "find client":     "get_client",
            "find ticket":     "search_ticket",
            "cherche ticket":  "search_ticket",
            "find sales":      "get_sales_summary",
            "find stock":      "check_stock",
            "stock de":        "check_stock",
            "find price":      "check_price",
            "prix de":         "check_price",
            "find contact":    "get_contact_info",
            "contact de":      "get_contact_info",
            "list all":        "list_all",
            "liste tous":      "list_all",
            "affiche tous":    "list_all",
        }
        for phrase, intent in explicit_commands.items():
            if phrase in text_lower:
                return intent, 0.95

        # Rule 2: Keyword scoring
        intent_scores = {}
        for intent_name, config in self.intent_patterns.items():
            score = 0
            for kw in config["keywords"]:
                if kw in text_lower or kw in tokens_lemma:
                    score += config["priority"]
            if score > 0:
                # Contextual bonuses
                if intent_name == "get_sales_summary" and any(w in text_lower for w in ["aujourd'hui", "jour", "today"]):
                    score *= 1.3
                if intent_name == "check_stock" and len(entities) >= 1:
                    score *= 1.2
                if intent_name == "get_contact_info" and len(entities) >= 1:
                    score *= 1.1
                intent_scores[intent_name] = score

        if intent_scores:
            best       = max(intent_scores, key=intent_scores.get)
            confidence = min(intent_scores[best] / 50.0, 1.0)
            return best, confidence

        return "get_product", 0.4

    # ==========================================================================
    # 🌍 LANGUAGE DETECTION
    # ==========================================================================

    def _detect_language(self, text: str) -> str:
        """Basic detection based on high-frequency indicators (Bilingual FR/EN)."""
        text_lower = text.lower()
        words      = text_lower.split()

        fr_indicators = [
            "le", "la", "les", "un", "une", "des", "du", "de",
            "est", "sont", "avec", "pour", "dans", "sur", "qui",
            "pourquoi", "quel", "quelle", "combien",
            "ordonnance", "mais", "ni", "car", "mon", "ma", "mes"
        ]
        en_indicators = [
            "the", "an", "is", "are", "with", "for",
            "in", "on", "what", "where", "how", "find",
            "search", "get", "show", "prescription", "my", "me"
        ]

        fr_count = sum(1 for w in words if w in fr_indicators)
        en_count = sum(1 for w in words if w in en_indicators)

        # Boost language detection based on command verbs
        if any(w in text_lower for w in ["find", "search", "show", "get"]):
            en_count += 2
        if any(w in text_lower for w in ["cherche", "trouve", "affiche", "montre"]):
            fr_count += 2

        return "en" if en_count > fr_count else "fr"