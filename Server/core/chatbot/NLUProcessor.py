"""
NLU bilingue FR/EN
"""

import re
from typing import Dict, List
import spacy


class NLUProcessor:

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

        # ── Salutations ──────────────────────────────────────────────────────
        self.greetings = {
            "fr": ["bonjour", "salut", "bonsoir", "coucou", "allo"],
            "en": ["hello", "hi", "good morning", "good evening", "greetings"]
        }

        # ── Help ──────────────────────────────────
        self.help_keywords = {
            "fr": ["aide", "aider", "guide", "besoin d'aide", "comment utiliser"],
            "en": ["help me", "assist me", "need help", "how do i use"]
        }

        # ── Keywords calendar ───────────────────────────────────
        self.temporal_keywords = {
            "demain", "aujourd'hui", "hier",
            "semaine", "prochaine", "prochain",
            "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"
        }

        # ── 💊 known products ───────────────────────────
        self.known_products = {
            "paracetamol", "doliprane", "ibuprofene", "ibuprofen",
            "amoxicilline", "aspirine", "omeprazole", "cetirizine",
            "vitamine", "vitamines", "serum", "hydrocortisone",
            "clarithromycine", "metronidazole", "loratadine",
            "furosemide", "pantoprazole", "insuline", "tramadol",
            "warfarine", "augmentin", "ventoline", "dexamethasone",
            "azithromycine", "fluconazole", "montelukast", "plavix",
            "clopidogrel", "coumadine", "metformine",
            "paracetamol", "acetaminophen", "tylenol", "advil",
            "nurofen", "aspirin", "amoxicillin", "omeprazole",
        }

        # ── Stop entities ───────────
        self.stop_entities = {
            # Intent-keywords FR
            "docteur", "médecin", "praticien", "spécialiste",
            "client", "patient", "acheteur",
            "stock", "prix", "alerte", "rupture",
            "vente", "ventes", "chiffre", "statistique",
            "ordonnance", "prescription",
            "contact", "téléphone", "telephone", "numéro", "email", "adresse",
            "interaction", "danger", "mélange", "compatible",
            "rdv", "rendez-vous", "garde", "planning", "agenda", "calendrier",
            "ticket", "problème",
            "produit", "médicament",
            # Intent-keywords EN
            "doctor", "physician", "specialist",
            "customer", "buyer",
            "price", "stock", "alert", "shortage",
            "sales", "revenue",
            "prescription", "contact", "phone", "address",
            "calendar", "schedule", "appointment", "meeting",
            # Commands words FR/EN
            "cherche", "trouve", "trouver", "recherche", "affiche", "montre",
            "find", "search", "show", "get", "list",
            # Pronouns and little words FR
            "le", "la", "les", "un", "une", "des", "du", "de", "d",
            "ce", "cet", "cette", "ces", "mon", "ma", "mes", "son", "sa", "ses",
            "et", "ou", "avec", "pour", "dans", "sur", "sous", "par",
            "est", "sont", "a", "ont", "ai", "as",
            "je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles",
            "me", "te", "se", "moi", "toi", "lui",
            "que", "qui", "quoi", "quel", "quelle", "quels",
            "comment", "combien", "pourquoi", "où", "quand",
            "puis", "peut", "faut", "faire", "faire", "prendre",
            # Articles EN
            "the", "a", "an", "some", "any",
            "is", "are", "was", "were", "has", "have", "do", "does",
            "can", "could", "would", "should", "may", "might",
            "i", "you", "he", "she", "we", "they", "it",
        }

        # ── Intent patterns ───────────────────────────
        self.intent_patterns = {

            "check_interaction": {
                "keywords": [
                    "incompatible", "interaction", "mélange", "mélanger",
                    "ensemble", "combiner", "conflit",
                    "compatible", "contre-indication", "associer", "puis-je", "peut-on",
                    "mix", "together", "combine", "contraindication", "can i take", "conflict",
                ],
                "priority": 10
            },

            "get_stock_alerts": {
                "keywords": [
                    "alerte", "manque", "rupture", "stock faible", "faible stock",
                    "réapprovisionner", "commander", "stock bas", "critique",
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
                    "nécessite", "prescrit",
                    "required", "prescribed", "mandatory",
                ],
                "priority": 6
            },

            "get_contact_info": {
                "keywords": [
                    "téléphone", "telephone", "numéro", "numero", "tél",
                    "joindre", "appeler", "email", "mail", "adresse",
                    "phone", "number", "call", "address", "reach",
                ],
                "priority": 9
            },

            "get_doctor": {
                "keywords": [
                    "docteur", "dr", "médecin", "praticien", "spécialiste",
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

            # FIX: priority 6 (était 4) — doit surpasser check_interaction sans marqueur
            "check_stock": {
                "keywords": [
                    "stock", "combien", "quantité", "disponible",
                    "reste", "niveau", "dispo", "restant", "inventaire",
                    "how many", "quantity", "available", "remaining", "level", "inventory",
                ],
                "priority": 6
            },

            "check_price": {
                "keywords": [
                    "prix", "coûte", "coute", "tarif",
                    "montant", "euro", "€",
                    "price", "cost", "how much", "fee", "rate", "$",
                ],
                "priority": 6
            },

            "search_ticket": {
                "keywords": [
                    "ticket", "problème", "incident", "issue",
                    "issue", "problem",
                ],
                "priority": 7
            },

            "calendar": {
                "keywords": [
                    "calendrier", "agenda", "planning", "rendez-vous", "rdv",
                    "garde", "réunion", "séance", "événement",
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

    # ══════════════════════════════════════════════════════════════════════════
    # ENTRY POINT
    # ══════════════════════════════════════════════════════════════════════════

    def analyze(self, text: str) -> Dict:
        """
        Retourne :
            intent, entity, entity_list, confidence, language
        """
        if not text or not text.strip():
            return {"intent": "unknown", "entity": "", "entity_list": [], "confidence": 0.0, "language": "fr"}

        lang = self._detect_language(text)
        text_lower = text.lower().strip()

        # FIX: greeting in first
        if self._is_greeting(text_lower, lang):
            return {"intent": "greeting", "entity": "", "entity_list": [], "confidence": 1.0, "language": lang}

        if self._is_help_request(text_lower, lang):
            return {"intent": "get_help", "entity": "", "entity_list": [], "confidence": 1.0, "language": lang}

        # FIX: Calendar words are very explicit, so we can shortcut the pipeline for these queries
        if self._is_calendar_query(text_lower):
            entities = self._extract_calendar_entities(text_lower)
            return {
                "intent": "calendar",
                "entity": entities[0] if entities else "",
                "entity_list": entities,
                "confidence": 0.95,
                "language": lang
            }

        # Pipeline NLU principal
        nlp = self.nlp_fr if lang == "fr" else (self.nlp_en or self.nlp_fr)
        doc = nlp(text)

        entities = self._extract_entities(doc, text)
        intent, confidence = self._detect_intent(doc, entities, text, lang)

        # FIX: if intent is not already "check_interaction" and we have strong markers of interaction, override intent to "check_interaction"
        if intent != "check_interaction" and self._has_explicit_interaction_markers(text_lower, entities):
            intent = "check_interaction"
            confidence = 0.95

        return {
            "intent": intent,
            "entity": entities[0] if entities else "",
            "entity_list": entities,
            "confidence": confidence,
            "language": lang
        }

    # ══════════════════════════════════════════════════════════════════════════
    # DETECT SPECIAL CASES (GREETING, HELP, CALENDAR) - to shortcut the pipeline for very explicit queries
    # ══════════════════════════════════════════════════════════════════════════

    def _is_greeting(self, text_lower: str, lang: str) -> bool:
        """Vrai seulement si le message est très court ET commence par une salutation.
        FIX: vérifie les deux langues — 'Hello' détecté en FR ne ratait jamais."""
        if len(text_lower.split()) > 4:
            return False
        # all the greetings in both languages to catch greetings even if language detection is off (ex: "Hello" in FR)
        all_greets = self.greetings.get("fr", []) + self.greetings.get("en", [])
        return any(text_lower.startswith(g) or text_lower == g for g in all_greets)

    def _is_help_request(self, text_lower: str, lang: str) -> bool:
        """Vrai seulement si message court contenant un mot d'aide."""
        if len(text_lower.split()) > 5:
            return False
        return any(kw in text_lower for kw in self.help_keywords.get(lang, []))

    def _is_calendar_query(self, text_lower: str) -> bool:
        """Vrai si le texte contient un mot-clé calendrier évident."""
        calendar_triggers = {
            "rdv", "r.d.v", "rendez-vous", "garde", "gardes",
            "planning", "agenda", "calendrier",
            "calendar", "schedule", "shift", "appointment",
        }
        words = set(re.split(r'\W+', text_lower))
        return bool(words & calendar_triggers)

    def _extract_calendar_entities(self, text_lower: str) -> List[str]:
        """
        Pour les requêtes calendrier, extrait :
        - les mots temporels (demain, semaine...)
        - les mots de type (rdv, garde)
        - les noms propres potentiels (capitalisés dans le texte original)
        """
        entities = []
        words = re.split(r'\W+', text_lower)

        # events types
        for kw in ["rdv", "garde", "réunion"]:
            if kw in words:
                entities.append(kw)

        # Time indicators
        for kw in self.temporal_keywords:
            if kw in text_lower:
                entities.append(kw)

        return entities if entities else []

    def _has_explicit_interaction_markers(self, text_lower: str, entities: List[str]) -> bool:
        """
        detection of explicit interaction markers:
        - presence of '+' or '&' symbols
        - presence of explicit interaction keywords (compatible, mélange, ensemble...)
        - presence of conjunctions (et, avec) + 2 entities
        """
        if len(entities) < 2:
            return False

        # Strong signal: presence of '+' or '&' in the text
        if '+' in text_lower or '&' in text_lower:
            return True

        # keywords explicitly indicating interaction, mixing, compatibility, etc.
        interaction_keywords = [
            'interaction', 'compatible', 'incompatible', 'mélanger', 'mélange',
            'ensemble', 'danger', 'puis-je', 'peut-on', 'associer',
            'mix', 'combine', 'together', 'safe to take', 'can i take',
        ]
        if any(kw in text_lower for kw in interaction_keywords):
            return True

        # conjunctions like "et", "avec", "plus" connecting two entities without command words strongly suggests an interaction query
        conjunctions = ['et', 'avec', 'plus', 'and', 'with']
        command_words = ['find', 'search', 'cherche', 'liste', 'list', 'show', 'montre', 'affiche']
        has_conjunction = any(f' {w} ' in f' {text_lower} ' for w in conjunctions)
        has_command = any(w in text_lower for w in command_words)

        return has_conjunction and not has_command

    # ══════════════════════════════════════════════════════════════════════════
    # EXTRACTION OF ENTITIES
    # ══════════════════════════════════════════════════════════════════════════

    def _extract_entities(self, doc, original_text: str) -> List[str]:
        """
        Extracting entities with a combination of methods:
        """
        text_lower = original_text.lower()
        entities = []

        # 1. Seperated entities with '+' or '&' (strong signal of interaction query, so we want to capture all parts as entities)
        if '+' in original_text or '&' in original_text:
            parts = re.split(r'[+&]', original_text)
            for part in parts:
                clean = part.strip().strip('.,!?;:')
                if len(clean) >= 3 and clean.lower() not in self.stop_entities:
                    entities.append(clean.strip())
            if len(entities) >= 2:
                return self._deduplicate_entities(entities)

        # 2. Known products list (exact match + dosage patterns)
        for product in self.known_products:
            if product in text_lower:
                pattern = rf'\b{re.escape(product)}\b\s*(\d+\s*mg|\d+\s*g)?'
                match = re.search(pattern, text_lower)
                if match:
                    full = match.group(0).strip()
                    cap = full.capitalize()
                    if cap not in entities:
                        entities.append(cap)

        # 3. POS Tagging spaCy (proper nouns, nouns, and alphanumeric tokens that are not stop words or punctuation)
        for token in doc:
            t_low = token.text.lower()
            if t_low in self.stop_entities or token.is_punct or token.like_num:
                continue
            if token.pos_ in ("PROPN", "X") and len(t_low) > 2:
                cap = token.text.capitalize()
                if cap not in entities:
                    entities.append(cap)

        # 4. Fallback : first non-stop, non-punctuation token longer than 2 characters
        if not entities:
            for token in doc:
                t_low = token.text.lower()
                if not token.is_stop and not token.is_punct and t_low not in self.stop_entities and len(t_low) > 2:
                    entities.append(token.text.capitalize())
                    break

        return self._deduplicate_entities(entities)

    def _deduplicate_entities(self, entities: List[str]) -> List[str]:
        """Supprime les entités incluses dans d'autres ('Aspirine' vs 'Aspirine 300mg')."""
        sorted_ents = sorted(set(entities), key=len, reverse=True)
        final = []
        for ent in sorted_ents:
            if not any(ent.lower() in other.lower() for other in final):
                final.append(ent)
        return final[:5]

    # ══════════════════════════════════════════════════════════════════════════
    # INTENT DETECTION
    # ══════════════════════════════════════════════════════════════════════════

    def _detect_intent(self, doc, entities: List[str], original_text: str, lang: str) -> tuple:
        text_lower = original_text.lower()
        tokens_lemma = {token.lemma_.lower() for token in doc}

        # Règle 1 : Explicit command words (find, search, show, get, list) + keywords very explicitly indicating intent (product, doctor, ticket, sales, stock, price, contact)
        explicit_commands = {
            "find product": "get_product", "search product": "get_product",
            "cherche produit": "get_product", "trouve produit": "get_product",
            "find doctor": "get_doctor", "find client": "get_client",
            "find ticket": "search_ticket", "cherche ticket": "search_ticket",
            "find sales": "get_sales_summary",
            "find stock": "check_stock", "stock de": "check_stock",
            "find price": "check_price", "prix de": "check_price",
            "find contact": "get_contact_info", "contact de": "get_contact_info",
            "list all": "list_all", "liste tous": "list_all", "affiche tous": "list_all",
        }
        for phrase, intent in explicit_commands.items():
            if phrase in text_lower:
                return intent, 0.95

        # Règle 2 : scoring by keywords
        intent_scores = {}
        for intent_name, config in self.intent_patterns.items():
            score = 0
            for kw in config["keywords"]:
                if kw in text_lower or kw in tokens_lemma:
                    score += config["priority"]
            if score > 0:
                # Contextual boosts:
                if intent_name == "get_sales_summary" and any(w in text_lower for w in ["aujourd'hui", "jour", "today"]):
                    score *= 1.3
                if intent_name == "check_stock" and len(entities) >= 1:
                    score *= 1.2
                if intent_name == "get_contact_info" and len(entities) >= 1:
                    score *= 1.1
                intent_scores[intent_name] = score

        if intent_scores:
            best = max(intent_scores, key=intent_scores.get)
            confidence = min(intent_scores[best] / 50.0, 1.0)
            return best, confidence

        return "get_product", 0.4

    # ══════════════════════════════════════════════════════════════════════════
    # LANGUAGE DETECTION
    # ══════════════════════════════════════════════════════════════════════════

    def _detect_language(self, text: str) -> str:
        text_lower = text.lower()
        words = text_lower.split()

        fr_indicators = [
            "le", "la", "les", "un", "une", "des", "du", "de",
            "est", "sont", "avec", "pour", "dans", "sur", "qui",
            "pourquoi", "quel", "quelle", "combien", "où",
            "ordonnance", "mais", "ni", "car", "mon", "ma", "mes"
        ]
        en_indicators = [
            "the", "a", "an", "is", "are", "with", "for",
            "in", "on", "what", "where", "how", "find",
            "search", "get", "show", "prescription", "my", "me"
        ]

        fr_count = sum(1 for w in words if w in fr_indicators)
        en_count = sum(1 for w in words if w in en_indicators)

        if any(w in text_lower for w in ["find", "search", "show", "get"]):
            en_count += 2
        if any(w in text_lower for w in ["cherche", "trouve", "affiche", "montre"]):
            fr_count += 2

        return "en" if en_count > fr_count else "fr"