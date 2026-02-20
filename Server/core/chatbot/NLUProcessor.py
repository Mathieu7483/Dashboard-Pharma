"""
Server/core/chatbot/NLUProcessor.py
NLU bilingue FR/EN — version finale avec emojis

Bugs corriges :
- Double definition de intent_patterns (ecrasement silencieux)
- "Bonjour" / "Hello" -> greeting
- "Aide moi" -> get_help
- stop_entities complet
- _detect_interaction_pattern : regle "2 entites courtes" supprimee (faux positifs)
- Intent calendar : priority 9, keywords rdv/garde
- Intent check_stock : priority 6
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
            print("⚠️  Fallback to fr_core_news_sm")
            self.nlp_fr = spacy.load("fr_core_news_sm")

        try:
            self.nlp_en = spacy.load("en_core_web_sm")
            print("✅ Loaded en_core_web_sm")
        except OSError:
            print("⚠️  EN model not available — using FR for all")
            self.nlp_en = None

        # ── 👋 Salutations ────────────────────────────────────────────────────
        self.greetings = {
            "fr": ["bonjour", "salut", "bonsoir", "coucou", "allo"],
            "en": ["hello", "hi", "good morning", "good evening", "greetings"]
        }

        # ── ❓ Aide (message court uniquement) ────────────────────────────────
        self.help_keywords = {
            "fr": ["aide", "aider", "guide", "besoin d'aide", "comment utiliser"],
            "en": ["help me", "assist me", "need help", "how do i use"]
        }

        # ── 📅 Mots-cles temporels calendrier ────────────────────────────────
        self.temporal_keywords = {
            "demain", "aujourd'hui", "hier",
            "semaine", "prochaine", "prochain",
            "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"
        }

        # ── 🚫 Stop entities : mots a ne JAMAIS extraire comme entite ─────────
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
            # Verbes / mots commandes
            "cherche", "trouve", "trouver", "recherche", "affiche", "montre",
            "find", "search", "show", "get", "list",
            # Articles / mots vides FR
            "le", "la", "les", "un", "une", "des", "du", "de", "d",
            "ce", "cet", "cette", "ces", "mon", "ma", "mes", "son", "sa", "ses",
            "et", "ou", "avec", "pour", "dans", "sur", "sous", "par",
            "est", "sont", "a", "ont", "ai", "as",
            "je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles",
            "me", "te", "se", "moi", "toi", "lui",
            "que", "qui", "quoi", "quel", "quelle", "quels",
            "comment", "combien", "pourquoi", "quand",
            "puis", "peut", "faut", "faire", "prendre",
            # Articles EN
            "the", "an", "some", "any",
            "is", "are", "was", "were", "has", "have", "do", "does",
            "can", "could", "would", "should", "may", "might",
            "i", "you", "he", "she", "we", "they", "it",
        }

        # ── 💊 Produits connus (detection directe) ───────────────────────────
        self.known_products = {
            # ── Sans accents (normalisé) ──────────────────────────────────────
            "paracetamol", "doliprane", "ibuprofene", "ibuprofen",
            "amoxicilline", "aspirine", "omeprazole", "cetirizine",
            "vitamine", "vitamines", "serum", "hydrocortisone",
            "clarithromycine", "metronidazole", "loratadine",
            "furosemide", "pantoprazole", "insuline", "tramadol",
            "warfarine", "augmentin", "ventoline", "dexamethasone",
            "azithromycine", "fluconazole", "montelukast", "plavix",
            "clopidogrel", "coumadine", "metformine",
            "acetaminophen", "tylenol", "advil",
            "nurofen", "aspirin", "amoxicillin",
            # ── Avec accents FR (FIX: "ibuprofène" ne matchait pas "ibuprofene") ──
            "ibuprofène", "paracétamol", "oméprazole", "cétirizine",
            "sérum", "furosémide", "métronidazole", "dexaméthasone",
            "azithromycine", "métformine", "résorcinol",
        }

        # ── 🧠 Intent patterns — UNE SEULE definition ─────────────────────────
        self.intent_patterns = {

            # 💊 + 💊 Interactions medicamenteuses
            "check_interaction": {
                "keywords": [
                    "incompatible", "interaction", "melange", "melanger",
                    "ensemble", "combiner", "conflit",
                    "compatible", "contre-indication", "associer", "puis-je", "peut-on",
                    "mix", "together", "combine", "contraindication", "can i take", "conflict",
                ],
                "priority": 10
            },

            # 📦 Alertes stock bas / rupture
            "get_stock_alerts": {
                "keywords": [
                    "alerte", "manque", "rupture", "stock faible", "faible stock",
                    "reapprovisionner", "commander", "stock bas", "critique",
                    "alert", "shortage", "out of stock", "low stock", "reorder", "critical",
                ],
                "priority": 8
            },

            # 💶 Ventes et statistiques
            "get_sales_summary": {
                "keywords": [
                    "vente", "ventes", "chiffre", "ca", "revenue",
                    "argent", "vendu", "total", "stat", "statistique",
                    "sales", "earnings", "sold", "statistics", "stats",
                ],
                "priority": 7
            },

            # 📋 Ordonnance / prescription
            "get_prescription_info": {
                "keywords": [
                    "ordonnance", "prescription", "obligatoire",
                    "necessite", "prescrit",
                    "required", "prescribed", "mandatory",
                ],
                "priority": 6
            },

            # 📞 Coordonnees contact
            "get_contact_info": {
                "keywords": [
                    "telephone", "numero", "tel",
                    "joindre", "appeler", "email", "mail", "adresse",
                    "phone", "number", "call", "address", "reach",
                ],
                "priority": 9
            },

            # 🩺 Medecin
            "get_doctor": {
                "keywords": [
                    "docteur", "dr", "medecin", "praticien", "specialiste",
                    "doctor", "physician", "practitioner", "specialist",
                ],
                "priority": 5
            },

            # 👤 Client
            "get_client": {
                "keywords": [
                    "client", "patient", "acheteur",
                    "customer", "buyer",
                ],
                "priority": 5
            },

            # 📦 Stock produit (priority 6 — FIX: etait 4, doit surpasser interaction sans marqueur)
            "check_stock": {
                "keywords": [
                    "stock", "combien", "quantite", "disponible",
                    "reste", "niveau", "dispo", "restant", "inventaire",
                    "how many", "quantity", "available", "remaining", "level", "inventory",
                ],
                "priority": 6
            },

            # 💰 Prix
            "check_price": {
                "keywords": [
                    "prix", "coute", "tarif",
                    "montant", "euro",
                    "price", "cost", "how much", "fee", "rate",
                ],
                "priority": 6
            },

            # 🎫 Tickets support
            "search_ticket": {
                "keywords": [
                    "ticket", "incident",
                    "issue", "problem",
                ],
                "priority": 7
            },

            # 📅 Calendrier / agenda (priority 9 — FIX: etait 4)
            "calendar": {
                "keywords": [
                    "calendrier", "agenda", "planning", "rendez-vous", "rdv",
                    "garde", "reunion", "seance", "evenement",
                    "calendar", "schedule", "appointments", "meeting", "event", "shift",
                ],
                "priority": 9
            },

            # 📋 Lister tout
            "list_all": {
                "keywords": [
                    "liste", "tous", "toutes", "affiche", "montre",
                    "list", "all", "show", "display", "every",
                ],
                "priority": 3
            },
        }

    # ══════════════════════════════════════════════════════════════════════════
    # 🔍 POINT D'ENTREE PRINCIPAL
    # ══════════════════════════════════════════════════════════════════════════

    def analyze(self, text: str) -> Dict:
        """
        Analyse le texte et retourne :
            intent, entity, entity_list, confidence, language
        """
        if not text or not text.strip():
            return {"intent": "unknown", "entity": "", "entity_list": [], "confidence": 0.0, "language": "fr"}

        lang       = self._detect_language(text)
        text_lower = text.lower().strip()

        # 👋 Salutation — detectee en premier, avant tout le reste
        # FIX: verifie FR + EN pour ne pas rater "Hello" detecte en FR
        if self._is_greeting(text_lower, lang):
            return {"intent": "greeting", "entity": "", "entity_list": [], "confidence": 1.0, "language": lang}

        # ❓ Aide — seulement si message court (<=5 mots)
        if self._is_help_request(text_lower, lang):
            return {"intent": "get_help", "entity": "", "entity_list": [], "confidence": 1.0, "language": lang}

        # 📅 Calendrier — court-circuit immediat si mot-cle agenda/rdv/garde detecte
        if self._is_calendar_query(text_lower):
            entities = self._extract_calendar_entities(text_lower)
            return {
                "intent": "calendar",
                "entity": entities[0] if entities else "",
                "entity_list": entities,
                "confidence": 0.95,
                "language": lang
            }

        # 🧠 Pipeline NLU principal
        nlp = self.nlp_fr if lang == "fr" else (self.nlp_en or self.nlp_fr)
        doc = nlp(text)

        entities       = self._extract_entities(doc, text)
        intent, conf   = self._detect_intent(doc, entities, text, lang)

        # 💊 Interaction — uniquement si marqueurs EXPLICITES dans le texte
        # FIX: suppression de la regle "2 entites courtes = interaction" (faux positifs)
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

    # ══════════════════════════════════════════════════════════════════════════
    # ⚡ DETECTIONS RAPIDES (avant pipeline NLU)
    # ══════════════════════════════════════════════════════════════════════════

    def _is_greeting(self, text_lower: str, lang: str) -> bool:
        """
        Vrai seulement si message court ET commence par une salutation.
        FIX: verifie FR + EN ensemble — 'Hello' detecte en FR ne ratait plus.
        """
        if len(text_lower.split()) > 4:
            return False
        all_greets = self.greetings.get("fr", []) + self.greetings.get("en", [])
        return any(text_lower.startswith(g) or text_lower == g for g in all_greets)

    def _is_help_request(self, text_lower: str, lang: str) -> bool:
        """Vrai seulement si message court (<= 5 mots) contenant un mot d'aide."""
        if len(text_lower.split()) > 5:
            return False
        return any(kw in text_lower for kw in self.help_keywords.get(lang, []))

    def _is_calendar_query(self, text_lower: str) -> bool:
        """Vrai si le texte contient un mot-cle calendrier evident."""
        calendar_triggers = {
            "rdv", "r.d.v", "rendez-vous", "garde", "gardes",
            "planning", "agenda", "calendrier",
            "calendar", "schedule", "shift", "appointment",
        }
        words = set(re.split(r'\W+', text_lower))
        return bool(words & calendar_triggers)

    def _extract_calendar_entities(self, text_lower: str) -> List[str]:
        """
        Pour les requetes calendrier, extrait :
        - les types d'evenements (rdv, garde)
        - les mots temporels (demain, lundi...)
        """
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
        Interaction UNIQUEMENT si :
        1. Au moins 2 entites distinctes dans le TEXTE
        2. ET un marqueur explicite (symbole, mot-cle interaction, conjonction)

        FIX: suppression de "2 entites courtes = interaction" (source des faux positifs sur aspirine)
        """
        if len(entities) < 2:
            return False

        # Symboles forts
        if "+" in text_lower or "&" in text_lower:
            return True

        # Mots-cles interaction explicites
        interaction_keywords = [
            "interaction", "compatible", "incompatible", "melanger", "melange",
            "ensemble", "danger", "puis-je", "peut-on", "associer",
            "mix", "combine", "together", "safe to take", "can i take",
        ]
        if any(kw in text_lower for kw in interaction_keywords):
            return True

        # Conjonction + 2 entites (mais PAS si mot de commande present)
        conjunctions  = ["et", "avec", "plus", "and", "with"]
        command_words = ["find", "search", "cherche", "liste", "list", "show", "montre", "affiche"]
        has_conj      = any(f" {w} " in f" {text_lower} " for w in conjunctions)
        has_command   = any(w in text_lower for w in command_words)

        return has_conj and not has_command

    # ══════════════════════════════════════════════════════════════════════════
    # 🏷️  EXTRACTION D'ENTITES
    # ══════════════════════════════════════════════════════════════════════════

    def _normalize(self, text: str) -> str:
        """Supprime les accents pour la comparaison (ibuprofène → ibuprofene)."""
        import unicodedata
        return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii").lower()

    def _extract_entities(self, doc, original_text: str) -> List[str]:
        """
        Extrait les noms propres / produits du texte.
        Ordre : symboles → produits connus → POS tagging → fallback
        """
        text_lower      = original_text.lower()
        text_normalized = self._normalize(original_text)  # FIX: version sans accents pour matching
        entities        = []

        # 1️⃣  Separation par symboles + / &
        if "+" in original_text or "&" in original_text:
            parts = re.split(r"[+&]", original_text)
            for part in parts:
                clean = part.strip().strip(".,!?;:")
                if len(clean) >= 3 and clean.lower() not in self.stop_entities:
                    entities.append(clean.strip())
            if len(entities) >= 2:
                return self._deduplicate_entities(entities)

        # 2️⃣  Produits connus (dictionnaire)
        # FIX: on cherche dans text_lower (accents) ET text_normalized (sans accents)
        for product in self.known_products:
            product_norm = self._normalize(product)
            # Match dans le texte original (avec accents) OU normalisé (sans accents)
            search_text = text_lower if product in text_lower else text_normalized
            search_prod = product    if product in text_lower else product_norm

            if search_prod in search_text:
                pattern = rf"\b{re.escape(search_prod)}\b\s*(\d+\s*mg|\d+\s*g)?"
                match   = re.search(pattern, search_text)
                if match:
                    # Récupère le mot original depuis le texte source (avec accents)
                    start, end = match.start(), match.end()
                    cap = original_text[start:end].strip().capitalize()
                    if cap and cap not in entities:
                        entities.append(cap)

        # 3️⃣  POS Tagging spaCy (noms propres ET noms communs longs = médicaments)
        for token in doc:
            t_low = token.text.lower()
            if t_low in self.stop_entities or token.is_punct or token.like_num:
                continue
            # FIX: NOUN accepté si >= 6 lettres (médicaments rarement tagués PROPN)
            is_relevant = (token.pos_ in ("PROPN", "X")) or (token.pos_ == "NOUN" and len(t_low) >= 6)
            if is_relevant and len(t_low) > 2:
                cap = token.text.capitalize()
                if cap not in entities:
                    entities.append(cap)

        # 4️⃣  Fallback : premier mot non-stop si rien trouve
        if not entities:
            for token in doc:
                t_low = token.text.lower()
                if not token.is_stop and not token.is_punct and t_low not in self.stop_entities and len(t_low) > 2:
                    entities.append(token.text.capitalize())
                    break

        return self._deduplicate_entities(entities)

    def _deduplicate_entities(self, entities: List[str]) -> List[str]:
        """Supprime les entites incluses dans d'autres (ex: 'Aspirine' vs 'Aspirine 300mg')."""
        sorted_ents = sorted(set(entities), key=len, reverse=True)
        final       = []
        for ent in sorted_ents:
            if not any(ent.lower() in other.lower() for other in final):
                final.append(ent)
        return final[:5]

    # ══════════════════════════════════════════════════════════════════════════
    # 🎯 DETECTION D'INTENT
    # ══════════════════════════════════════════════════════════════════════════

    def _detect_intent(self, doc, entities: List[str], original_text: str, lang: str) -> tuple:
        text_lower   = original_text.lower()
        tokens_lemma = {token.lemma_.lower() for token in doc}

        # 🔑 Regle 1 : commandes explicites (priorite absolue)
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

        # 📊 Regle 2 : scoring par mots-cles
        intent_scores = {}
        for intent_name, config in self.intent_patterns.items():
            score = 0
            for kw in config["keywords"]:
                if kw in text_lower or kw in tokens_lemma:
                    score += config["priority"]
            if score > 0:
                # 🔁 Bonus contextuels
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

    # ══════════════════════════════════════════════════════════════════════════
    # 🌍 DETECTION DE LANGUE
    # ══════════════════════════════════════════════════════════════════════════

    def _detect_language(self, text: str) -> str:
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

        if any(w in text_lower for w in ["find", "search", "show", "get"]):
            en_count += 2
        if any(w in text_lower for w in ["cherche", "trouve", "affiche", "montre"]):
            fr_count += 2

        return "en" if en_count > fr_count else "fr"