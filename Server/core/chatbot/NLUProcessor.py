"""
Server/core/chatbot/NLUProcessor.py
Bilingual NLU (FR/EN) for Pharmacy Management
"""

import re
import unicodedata
from typing import Dict, List, Tuple
import spacy
from utils.text_norm import normalize as _shared_normalize


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
            "en": ["help", "help me", "assist me", "need help", "how do i use"]
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
            "ordonnance", "prescription", "posologie", "traitement", "boite",
            "contact", "telephone", "numero", "email", "adresse",
            "interaction", "danger", "melange", "compatible",
            "rdv", "rendez-vous", "garde", "planning", "agenda", "calendrier",
            "ticket", "probleme", "produit", "medicament",
            # Intent-keywords EN
            "doctor", "physician", "specialist",
            "customer", "buyer",
            "price", "alert", "shortage",
            "sales", "revenue", "dosage", "treatment", "box",
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

        self.known_products: set = set()

        # -- Intent patterns with priorities -----------------------------------
        self.intent_patterns = {
            "check_interaction": {
                "keywords": [
                    "incompatible", "interaction", "melange", "melanger",
                    "ensemble", "combiner", "conflit",
                    "compatible", "contre-indication", "associer", "puis-je", "peut-on",
                    "mix", "together", "combine", "contraindication", "can i take", "conflict",
                ],
                "priority": 10
            },
            "get_stock_alerts": {
                "keywords": [
                    "alerte", "manque", "rupture", "stock faible", "faible stock",
                    "reapprovisionner", "commander", "stock bas", "critique",
                    "alert", "shortage", "out of stock", "low stock", "reorder", "critical",
                ],
                "priority": 8
            },
            "get_sales_summary": {
                "keywords": [
                    "vente", "ventes", "chiffre", "ca", "revenue",
                    "argent", "vendu", "total", "stat", "statistique",
                    "sales", "earnings", "sold", "statistics", "stats",
                ],
                "priority": 7
            },
            "get_prescription_info": {
                "keywords": [
                    "ordonnance", "prescription", "obligatoire",
                    "necessite", "prescrit",
                    "required", "prescribed", "mandatory",
                ],
                "priority": 6
            },
            "get_contact_info": {
                "keywords": [
                    "telephone", "numero", "tel",
                    "joindre", "appeler", "email", "mail", "adresse",
                    "phone", "number", "call", "address", "reach",
                ],
                "priority": 9
            },
            "get_doctor": {
                "keywords": [
                    "docteur", "dr", "medecin", "praticien", "specialiste",
                    "doctor", "physician", "practitioner", "specialist",
                ],
                "priority": 5
            },
            "get_client": {
                "keywords": [
                    "client", "patient", "acheteur",
                    "customer", "buyer",
                ],
                "priority": 5
            },
            "check_stock": {
                "keywords": [
                    "stock", "combien", "quantite", "disponible",
                    "reste", "niveau", "dispo", "restant", "inventaire",
                    "how many", "quantity", "available", "remaining", "level", "inventory",
                ],
                "priority": 6
            },
            "check_price": {
                "keywords": [
                    "prix", "coute", "tarif",
                    "montant", "euro",
                    "price", "cost", "how much", "fee", "rate",
                ],
                "priority": 6
            },
            "search_ticket": {
                "keywords": [
                    "ticket", "incident",
                    "issue", "problem",
                ],
                "priority": 7
            },
            "calendar": {
                "keywords": [
                    "calendrier", "agenda", "planning", "rendez-vous", "rdv",
                    "garde", "reunion", "seance", "evenement",
                    "calendar", "schedule", "appointments", "meeting", "event", "shift",
                ],
                "priority": 9
            },
            "list_all": {
                "keywords": [
                    "liste", "tous", "toutes", "affiche", "montre",
                    "list", "all", "show", "display", "every",
                ],
                "priority": 3
            },
        }

    def load_products_from_db(self) -> None:
        """Loads known products from database and populates the entity dictionary."""
        from models.product import ProductModel
        from database.data_manager import db

        _norm = _shared_normalize

        try:
            rows = db.session.execute(
                db.select(ProductModel.name, ProductModel.active_ingredient)
            ).all()

            new_set: set = set()
            for name, ingredient in rows:
                if name:
                    name_low = name.lower().strip()
                    name_norm = _norm(name)
                    new_set.add(name_low)
                    new_set.add(name_norm)
                    first_word = name_low.split()[0] if name_low.split() else name_low
                    new_set.add(first_word)
                    new_set.add(_norm(first_word))
                if ingredient:
                    ing_low = ingredient.lower().strip()
                    ing_norm = _norm(ingredient)
                    new_set.add(ing_low)
                    new_set.add(ing_norm)
                    first_ing = ing_low.split()[0] if ing_low.split() else ing_low
                    new_set.add(first_ing)
                    new_set.add(_norm(first_ing))

            self.known_products = new_set
            print(f"✅ NLU: {len(new_set)} product entries loaded from DB")

        except Exception as e:
            print(f"⚠️  NLU: Could not load products from DB: {e}")
            self.known_products = {
                "doliprane", "aspirine", "ibuprofene",
                "paracetamol", "amoxicilline", "omeprazole",
            }

    # ==========================================================================
    # 🔍 MAIN ENTRY POINT
    # ==========================================================================

    def analyze(self, text: str) -> Dict:
        if not text or not text.strip():
            return {"intent": "unknown", "entity": "", "entity_list": [], "confidence": 0.0, "language": "fr"}

        lang = self._detect_language(text)
        text_lower = text.lower().strip()

        # Greeting detection
        if self._is_greeting(text_lower, lang):
            return {"intent": "greeting", "entity": "", "entity_list": [], "confidence": 1.0, "language": lang}

        # Help request
        if self._is_help_request(text_lower, lang):
            return {"intent": "get_help", "entity": "", "entity_list": [], "confidence": 1.0, "language": lang}

        # Calendar query
        if self._is_calendar_query(text_lower):
            entities = self._extract_calendar_entities(text_lower)
            return {
                "intent": "calendar",
                "entity": entities[0] if entities else "",
                "entity_list": entities,
                "confidence": 0.95,
                "language": lang
            }

        # NLU Pipeline
        nlp = (self.nlp_en if lang == "en" and self.nlp_en else self.nlp_fr)
        doc = nlp(text)

        entities = self._extract_entities(doc, text)
        intent, conf = self._detect_intent(doc, entities, text, lang)

        if intent != "check_interaction" and self._has_explicit_interaction_markers(text_lower, entities):
            intent = "check_interaction"
            conf = 0.95

        return {
            "intent": intent,
            "entity": entities[0] if entities else "",
            "entity_list": entities,
            "confidence": conf,
            "language": lang
        }

    # ==========================================================================
    # ⚡ QUICK DETECTIONS
    # ==========================================================================

    def _is_greeting(self, text_lower: str, lang: str) -> bool:
        if len(text_lower.split()) > 4:
            return False
        all_greets = self.greetings.get("fr", []) + self.greetings.get("en", [])
        return any(text_lower.startswith(g) or text_lower == g for g in all_greets)

    def _is_help_request(self, text_lower: str, lang: str) -> bool:
        if len(text_lower.split()) > 5:
            return False
        return any(kw in text_lower for kw in self.help_keywords.get(lang, []))

    def _is_calendar_query(self, text_lower: str) -> bool:
        calendar_triggers = {
            "rdv", "r.d.v", "rendez-vous", "garde", "gardes",
            "planning", "agenda", "calendrier",
            "calendar", "schedule", "shift", "appointment",
        }
        words = set(re.split(r'\W+', text_lower))
        return bool(words & calendar_triggers)

    def _extract_calendar_entities(self, text_lower: str) -> List[str]:
        entities = []
        words = re.split(r'\W+', text_lower)

        for kw in ["rdv", "garde", "reunion"]:
            if kw in words:
                entities.append(kw)

        for kw in self.temporal_keywords:
            if kw in text_lower:
                entities.append(kw)

        return entities

    def _has_explicit_interaction_markers(self, text_lower: str, entities: List[str]) -> bool:
        if len(entities) < 2:
            return False

        if "+" in text_lower or "&" in text_lower:
            return True

        interaction_keywords = [
            "interaction", "compatible", "incompatible", "melanger", "melange",
            "ensemble", "danger", "puis-je", "peut-on", "associer",
            "mix", "combine", "together", "safe to take", "can i take",
        ]
        if any(kw in text_lower for kw in interaction_keywords):
            return True

        conjunctions = ["et", "avec", "plus", "and", "with"]
        command_words = ["find", "search", "cherche", "liste", "list", "show", "montre", "affiche"]
        has_conj = any(f" {w} " in f" {text_lower} " for w in conjunctions)
        has_command = any(w in text_lower for w in command_words)

        return has_conj and not has_command

    # ==========================================================================
    # 🏷️ ENTITY EXTRACTION
    # ==========================================================================

    def _normalize(self, text: str) -> str:
        return _shared_normalize(text)

    def _extract_entities(self, doc, original_text: str) -> List[str]:
        text_lower = original_text.lower()
        text_normalized = self._normalize(original_text)
        entities = []

        # 1️⃣ Split by symbols (+ or &)
        if "+" in original_text or "&" in original_text:
            parts = re.split(r"[+&]", original_text)
            for part in parts:
                clean = part.strip().strip(".,!?;:")
                clean_norm = self._normalize(clean)
                if len(clean) >= 3 and clean_norm not in self.stop_entities:
                    entities.append(clean.title())
            if len(entities) >= 2:
                return self._deduplicate_entities(entities)

        # 2️⃣ Known products lookup
        for product in self.known_products:
            product_norm = self._normalize(product)
            if product_norm in text_normalized:
                pattern = rf"\b{re.escape(product_norm)}\b\s*(\d+\s*mg|\d+\s*g)?"
                match = re.search(pattern, text_normalized)
                if match:
                    start, end = match.start(), match.end()
                    # Safe slice extraction on original text using word bounds
                    matched_text = original_text[start:end].strip()
                    cap = matched_text.title()
                    if cap and cap.lower() not in [e.lower() for e in entities]:
                        entities.append(cap)

        # 3️⃣ SpaCy POS Tagging (PROPN / NOUN filtering)
        for token in doc:
            t_norm = self._normalize(token.text)
            if t_norm in self.stop_entities or token.is_punct or token.like_num or token.is_stop:
                continue

            # Strict on NOUN: only keep if titled/uppercase in text or explicitly PROPN/X
            is_propn = token.pos_ in ("PROPN", "X")
            is_valid_noun = token.pos_ == "NOUN" and (token.text[0].isupper() or len(token.text) > 5)

            if (is_propn or is_valid_noun) and len(t_norm) > 2:
                cap = token.text.title()
                if cap.lower() not in [e.lower() for e in entities]:
                    entities.append(cap)

        # 4️⃣ Fallback
        if not entities:
            for token in doc:
                t_norm = self._normalize(token.text)
                if not token.is_stop and not token.is_punct and t_norm not in self.stop_entities and len(t_norm) > 2:
                    entities.append(token.text.title())
                    break

        return self._deduplicate_entities(entities)

    def _deduplicate_entities(self, entities: List[str]) -> List[str]:
        """Deduplicates case-insensitively without dropping distinct substring names."""
        seen = set()
        final = []
        for ent in entities:
            ent_clean = ent.strip()
            ent_key = ent_clean.lower()
            if ent_key not in seen:
                seen.add(ent_key)
                final.append(ent_clean)
        return final[:5]

    # ==========================================================================
    # 🎯 INTENT DETECTION
    # ==========================================================================

    def _detect_intent(self, doc, entities: List[str], original_text: str, lang: str) -> Tuple[str, float]:
        text_lower = original_text.lower()
        tokens_lemma = {token.lemma_.lower() for token in doc}

        explicit_commands = {
            "find product": "get_product",
            "search product": "get_product",
            "cherche produit": "get_product",
            "trouve produit": "get_product",
            "find doctor": "get_doctor",
            "find client": "get_client",
            "find ticket": "search_ticket",
            "cherche ticket": "search_ticket",
            "find sales": "get_sales_summary",
            "find stock": "check_stock",
            "stock de": "check_stock",
            "find price": "check_price",
            "prix de": "check_price",
            "find contact": "get_contact_info",
            "contact de": "get_contact_info",
            "list all": "list_all",
            "liste tous": "list_all",
            "affiche tous": "list_all",
        }
        for phrase, intent in explicit_commands.items():
            if phrase in text_lower:
                return intent, 0.95

        intent_scores = {}
        for intent_name, config in self.intent_patterns.items():
            score = 0
            for kw in config["keywords"]:
                if kw in text_lower or kw in tokens_lemma:
                    score += config["priority"]
            if score > 0:
                if intent_name == "get_sales_summary" and any(w in text_lower for w in ["aujourd'hui", "jour", "today"]):
                    score *= 1.3
                if intent_name == "check_stock" and len(entities) >= 1:
                    score *= 1.2
                if intent_name == "get_contact_info" and len(entities) >= 1:
                    score *= 1.1
                intent_scores[intent_name] = score

        if intent_scores:
            best = max(intent_scores, key=intent_scores.get)
            confidence = min(intent_scores[best] / 30.0, 1.0)
            return best, round(confidence, 2)

        return "get_product", 0.4

    # ==========================================================================
    # 🌍 LANGUAGE DETECTION
    # ==========================================================================

    def _detect_language(self, text: str) -> str:
        text_lower = text.lower()
        words = text_lower.split()

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

        if any(w in text_lower for w in ["find", "search", "show", "get", "list", "help"]):
            en_count += 2
        if any(w in text_lower for w in ["cherche", "trouve", "affiche", "montre", "aide"]):
            fr_count += 2

        return "en" if en_count > fr_count else "fr"