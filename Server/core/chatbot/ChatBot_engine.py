"""
Server/core/chatbot/ChatBot_engine.py
Code: English | UI/Outputs: French
"""

from typing import List
from sqlalchemy import or_, and_, func, cast, Date
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from database.data_manager import db
from models.product import ProductModel
from models.client import ClientModel
from models.doctor import DoctorModel
from models.sale import SaleModel
from models.interaction import InteractionModel
from models.product_alias import ProductAliasModel
from models.ticket import Ticket
from models.calendar import CalendarEvent
from core.chatbot.NLUProcessor import NLUProcessor
import unicodedata
import re
from services.facade import FacadeService

class ChatBotEngine:

    def __init__(self):
        self.nlu = NLUProcessor()
        self.facade = FacadeService()
        self._temporal_words = {
            "demain", "aujourd'hui", "hier",
            "semaine", "prochaine", "prochain",
            "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"
        }

    def _norm(self, s: str) -> str:
        """Normalize string: lowercase and remove accents."""
        if not s: return ""
        return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii").lower().strip()

    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================

    def process_query(self, user_text: str, user_id: str = None) -> dict:
        """
        Main engine logic. Analyzes intent and returns a French response.
        """
        print(f"DEBUG: Received text: '{user_text}' | UserID: {user_id}")

        clean_text = user_text.lower().strip()

        # Security: block basic SQL injection patterns
        if re.search(r"[;'\"\\]|--|\b(drop|truncate|delete|insert)\b", clean_text):
            return {"intent": "unknown", "reply": "Requête non valide pour des raisons de sécurité."}

        # 1. Profile / Identity check
        profile_triggers = ["qui suis je", "qui suis-je", "mon profil", "c'est qui"]
        if any(trigger in clean_text for trigger in profile_triggers):
            if not user_id:
                return {
                    "intent": "auth_check", 
                    "reply": "Je ne parviens pas à vous identifier. Assurez-vous d'être connecté."
                }
            
            user = self.facade.get_user_by_id(user_id)
            if user:
                display_name = f"{user.first_name} {user.last_name}".strip()
                if not display_name or "None" in display_name:
                    display_name = user.username

                return {
                    "intent": "user_identify",
                    "reply": f"Vous êtes {display_name}, connecté sous l'identifiant {user.username}."
                }

        # 2. Empty input check
        if not clean_text:
            return {"intent": "unknown", "reply": "Veuillez poser une question."}

        # 3. NLU Analysis
        analysis = self.nlu.analyze(user_text)
        intent   = analysis.get("intent", "unknown")
        entities = analysis.get("entity_list", [])

        try:
            response_text = ""

            # 4. Intent Routing
            if intent == "greeting":
                user = self.facade.get_user_by_id(user_id) if user_id else None
                name = user.username if user else "collègue"
                response_text = f"Bonjour {name} ! Comment puis-je vous aider aujourd'hui ?"

            elif intent == "get_help":
                response_text = self._generate_help_message()

            elif intent == "check_interaction":
                response_text = self._handle_interaction_check(entities)

            elif intent == "get_stock_alerts":
                response_text = self._handle_stock_alerts()

            elif intent == "get_sales_daily":
                response_text = self._handle_sales_daily()

            elif intent == "get_sales_summary":
                response_text = self._handle_sales_summary()

            elif intent == "check_stock":
                response_text = self._handle_stock_query(entities)

            elif intent == "check_price":
                response_text = self._handle_price_query(entities)

            elif intent == "get_prescription_info":
                response_text = self._handle_prescription_info(entities)

            elif intent == "get_contact_info":
                response_text = self._handle_contact_search(entities)

            elif intent == "search_ticket":
                response_text = self._handle_ticket_info(entities)

            elif intent == "calendar":
                response_text = self._handle_calendar_events(entities, user_text)

            # 5. Multi-category search for ambiguous queries
            elif intent in ("get_doctor", "get_client", "list_all", "get_product"):
                if not entities:
                    response_text = self._generate_help_message()
                else:
                    response_text = self._execute_multi_category_search(entities[0])

            # 6. Fallback
            else:
                if entities:
                    response_text = self._execute_multi_category_search(entities[0])
                else:
                    response_text = self._generate_help_message()
                    intent = "get_help"

            return {"intent": intent, "reply": response_text}

        except Exception as e:
            import traceback
            print(f"ChatBot Error: {e}")
            traceback.print_exc()
            return {
                "intent": "error",
                "reply": "Une erreur est survenue lors du traitement de votre demande. Veuillez réessayer."
            }

    # =========================================================================
    # INTENT HANDLERS (Outputs in French)
    # =========================================================================

    def _handle_interaction_check(self, entity_list: list) -> str:
        """Handles drug interaction checking logic."""
        if len(entity_list) < 2:
            return (
                "Veuillez mentionner au moins DEUX produits pour vérifier leur compatibilité.\n\n"
                "Exemples :\n"
                "   - 'Aspirine et Ibuprofène compatibles ?'\n"
                "   - 'Doliprane avec Advil danger ?'"
            )

        resolved, display_names = [], []
        for name in entity_list:
            ingredient, display = self._resolve_to_active_ingredient(name)
            resolved.append(self._norm(ingredient))
            display_names.append(display)

        conflicts = []
        for i in range(len(resolved)):
            for j in range(i + 1, len(resolved)):
                result = self.facade.get_interaction(resolved[i], resolved[j])
                if result:
                    conflicts.append({
                        "interaction": result, 
                        "name_a": display_names[i], 
                        "name_b": display_names[j]
                    })

        if not conflicts:
            return (
                "✅ Aucune interaction connue détectée.\n\n"
                f"Produits analysés : {' + '.join(display_names)}\n\n"
                "⚠️ Toujours consulter un pharmacien ou la base Vidal."
            )

        severity_emoji = {"low": "⚠️", "moderate": "🟠", "high": "🔴", "critical": "🛑"}
        
        output = ["🚨 ALERTE INTERACTION MÉDICAMENTEUSE\n", f"Analyse pour : {' + '.join(display_names)}\n"]
        for c in conflicts:
            ix = c["interaction"]
            emoji = severity_emoji.get(ix.severity.lower(), "⚠️")
            output += [
                f"{emoji} {c['name_a']} + {c['name_b']}",
                f"Sévérité : {ix.severity.upper()}",
                f"Détails : {ix.description}",
                "---\n"
            ]
        output.append("⚠️ IMPORTANT : Avis médical requis avant délivrance.")
        return "\n".join(output)

    def _handle_stock_query(self, entities: list) -> str:
        """Queries product stock levels."""
        if not entities:
            return "Quel produit souhaitez-vous vérifier ?"
        products = self._search_database(ProductModel, entities[0])
        if not products:
            return f"Aucun produit trouvé pour '{entities[0]}'."
        output = [f"📊 État des stocks : {entities[0].capitalize()}"]
        for p in products:
            if p.stock > 100:   emoji, status = "🟢", "Optimal"
            elif p.stock > 50:  emoji, status = "🟢", "Correct"
            elif p.stock > 20:  emoji, status = "🟡", "À surveiller"
            elif p.stock > 5:   emoji, status = "🟠", "Faible"
            else:               emoji, status = "⚠️🔴", "CRITIQUE"
            rx = "Sur ordonnance" if p.is_prescription_only else "Vente libre"
            output.append(f"   {emoji} {p.name} ({p.dosage}) - {p.stock} unités ({status}) | {p.price:.2f}€ | {rx}")
        return "\n".join(output)

    def _handle_price_query(self, entities: list) -> str:
        """Queries product pricing."""
        if not entities:
            return "Quel produit cherchez-vous ?"
        product = db.session.execute(
            db.select(ProductModel).where(ProductModel.name.ilike(f"%{entities[0]}%"))
        ).scalar_one_or_none()
        if not product:
            return f"Produit '{entities[0]}' introuvable."
        rx = "Sur ordonnance" if product.is_prescription_only else "Vente libre"
        return (
            f"💊 {product.name}\n"
            f"   Prix : {product.price:.2f} €\n"
            f"   Régime : {rx}\n"
            f"   Dosage : {product.dosage}\n"
            f"   Stock : {product.stock} unités"
        )

    def _handle_prescription_info(self, entities: list) -> str:
        """Checks if a product requires a prescription."""
        if not entities:
            return "Quel médicament souhaitez-vous vérifier ?"
        product = db.session.execute(
            db.select(ProductModel).where(ProductModel.name.ilike(f"%{entities[0]}%"))
        ).scalar_one_or_none()
        if not product:
            return f"Produit '{entities[0]}' introuvable."
        if product.is_prescription_only:
            return (
                f"📝 {product.name} nécessite obligatoirement une ordonnance.\n"
                f"   Molécule : {product.active_ingredient}\n"
                f"   Dosage : {product.dosage}"
            )
        return (
            f"✅ {product.name} est disponible en vente libre.\n"
            f"   Prix : {product.price:.2f} €\n"
            f"   Stock : {product.stock} unités"
        )

    def _handle_stock_alerts(self) -> str:
        """Lists products with low stock levels."""
        threshold = 20
        low_stock = db.session.execute(
            db.select(ProductModel).where(ProductModel.stock < threshold).order_by(ProductModel.stock)
        ).scalars().all()
        if not low_stock:
            return f"🟢 Stock satisfaisant pour tous les produits (>= {threshold} unités)."
        output = [f"⚠️ Alertes Stock Bas (< {threshold} unités)\n"]
        critical = [p for p in low_stock if p.stock < 5]
        warning  = [p for p in low_stock if 5 <= p.stock < threshold]
        if critical:
            output.append("🔴 CRITIQUE (< 5 unités)")
            for p in critical:
                output.append(f"   {p.name} : {p.stock} unités")
            output.append("")
        if warning:
            output.append("🟠 FAIBLE (5-19 unités)")
            for p in warning:
                output.append(f"   {p.name} : {p.stock} unités")
        output.append(f"\nTotal : {len(low_stock)} produits à réapprovisionner.")
        return "\n".join(output)

    def _handle_sales_summary(self) -> str:
        """Generates performance statistics for daily and weekly sales."""
        try:
            now = datetime.now()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = (start_of_day - timedelta(days=now.weekday()))

            def _get_stats(filter_condition):
                return db.session.query(
                    func.count(SaleModel.id),
                    func.sum(SaleModel.total_amount)
                ).filter(filter_condition).first()

            ct, rt = _get_stats(SaleModel.sale_date >= start_of_day)
            cw, rw = _get_stats(SaleModel.sale_date >= week_start)
            ca, ra = _get_stats(True)

            ct, rt = (ct or 0), (rt or 0.0)
            cw, rw = (cw or 0), (rw or 0.0)
            ca, ra = (ca or 0), (ra or 0.0)

            output = [
                "📈 PERFORMANCE DES VENTES\n",
                f"Aujourd'hui ({now.strftime('%d/%m/%Y')})",
                f"   Transactions : {ct} | CA : {rt:.2f} €\n",
                f"Cette semaine (depuis le {week_start.strftime('%d/%m')})",
                f"   Transactions : {cw} | CA : {rw:.2f} €\n",
                f"Cumul Total",
                f"   Transactions : {ca} | CA : {ra:.2f} €",
            ]
            if ca > 0:
                output.append(f"   Panier moyen : {ra/ca:.2f} €")
            return "\n".join(output)
        except Exception as e:
            return f"Erreur statistiques : {str(e)}"

    def _handle_sales_daily(self) -> str:
        """Retrieves a list of today's sales."""
        try:
            now = datetime.now()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

            sales = db.session.query(
                SaleModel.id, SaleModel.total_amount, SaleModel.sale_date, SaleModel.user_id
            ).filter(and_(SaleModel.sale_date >= start_of_day, SaleModel.sale_date <= end_of_day)).all()

            if not sales:
                return f"Aucune vente enregistrée pour aujourd'hui ({now.strftime('%d/%m/%Y')})."

            output = [f"📋 Ventes du jour ({now.strftime('%d/%m/%Y')})\n"]
            for s in sales:
                output.append(f"Ticket #{str(s.id)[:8]}... - {s.total_amount:.2f} € - {s.sale_date.strftime('%H:%M')}")
            
            output.append(f"\nTotal transactions : {len(sales)}")
            output.append(f"CA journalier : {sum(s.total_amount for s in sales):.2f} €")
            return "\n".join(output)
        except Exception as e:
            return f"Erreur : {str(e)}"

    def _handle_contact_search(self, entities: list) -> str:
        """Searches for doctors or clients contact information."""
        if not entities:
            return "Qui recherchez-vous ?"
        search_term = entities[0]
        person = self._search_database(DoctorModel, search_term)
        category = "Médecin"
        if not person:
            person = self._search_database(ClientModel, search_term)
            category = "Client"
        if not person:
            return f"Aucun contact trouvé pour '{search_term}'."
        p = person[0]
        output = [
            f"👤 Fiche Contact - {p.first_name} {p.last_name}",
            f"   Rôle : {category}",
            f"   Tél : {p.phone or 'Non renseigné'}",
            f"   Email : {p.email or 'Non renseigné'}",
        ]
        if hasattr(p, 'address') and p.address:
            output.append(f"   Adresse : {p.address}")
        return "\n".join(output)

    def _handle_ticket_info(self, entities: list) -> str:
        """Retrieves support ticket details."""
        if not entities:
            return "Quel ticket souhaitez-vous consulter ? (ex: 'Ticket #1234')"
        search_term = entities[0].strip()
        if search_term.startswith("#"):
            ticket = db.session.execute(db.select(Ticket).where(Ticket.id == search_term[1:])).scalar_one_or_none()
        else:
            ticket = db.session.execute(db.select(Ticket).where(Ticket.subject.ilike(f"%{search_term}%"))).scalar_one_or_none()
        if not ticket:
            return f"Ticket '{search_term}' introuvable."
        
        output = [
            f"🎫 Ticket {ticket.id[:8]}...",
            f"   Sujet : {ticket.subject}",
            f"   Description : {ticket.description}",
            f"   Priorité : {ticket.priority.capitalize()}",
            f"   Statut : {ticket.status.replace('open','Ouvert').replace('closed','Fermé')}",
            f"   Créé le : {ticket.created_at.strftime('%d/%m/%Y %H:%M')}",
        ]
        return "\n".join(output)

    def _handle_calendar_events(self, entities: list, user_text: str = "") -> str:
        """Handles calendar and schedule queries."""
        text_lower = user_text.lower()
        if any(tw in text_lower for tw in self._temporal_words):
            return self._handle_schedule_query(user_text)

        today_str = datetime.now().strftime("%Y-%m-%d")
        week_end_str = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        if not entities:
            events = db.session.execute(
                db.select(CalendarEvent)
                .options(selectinload(CalendarEvent.assigned_user), selectinload(CalendarEvent.creator))
                .where(CalendarEvent.start_date >= today_str, CalendarEvent.start_date <= week_end_str)
                .order_by(CalendarEvent.start_date, CalendarEvent.start_time)
            ).scalars().all()
            if not events:
                return "Aucun événement prévu cette semaine."
            output = ["📅 Agenda - 7 prochains jours\n"]
            for e in events:
                output += self._format_event(e)
            return "\n".join(output)

        search_term = entities[0].strip().lower()
        events = db.session.execute(
            db.select(CalendarEvent).options(selectinload(CalendarEvent.assigned_user), selectinload(CalendarEvent.creator))
            .where(CalendarEvent.start_date >= today_str,
                   or_(CalendarEvent.title.ilike(f"%{search_term}%"),
                       CalendarEvent.notes.ilike(f"%{search_term}%"),
                       CalendarEvent.type.ilike(f"%{search_term}%")))
            .order_by(CalendarEvent.start_date, CalendarEvent.start_time)
        ).scalars().all()

        if not events:
            return f"Aucun événement trouvé pour '{search_term}'."
        output = [f"📅 Résultats Agenda - '{search_term}'\n"]
        for e in events:
            output += self._format_event(e)
        return "\n".join(output)

    def _handle_schedule_query(self, user_text: str) -> str:
        """Processes temporal queries (tomorrow, monday, etc.)."""
        text_lower = user_text.lower()
        now = datetime.now()
        if "demain" in text_lower:      target = now + timedelta(days=1)
        elif "hier" in text_lower:      target = now - timedelta(days=1)
        elif "aujourd" in text_lower:   target = now
        else:
            days = {"lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, "vendredi": 4, "samedi": 5, "dimanche": 6}
            target = now
            for day, num in days.items():
                if day in text_lower:
                    diff = (num - now.weekday()) % 7 or 7
                    target = now + timedelta(days=diff)
                    break
        date_iso, date_fr = target.strftime("%Y-%m-%d"), target.strftime("%d/%m/%Y")
        events = db.session.execute(
            db.select(CalendarEvent).options(selectinload(CalendarEvent.assigned_user), selectinload(CalendarEvent.creator))
            .where(CalendarEvent.start_date == date_iso).order_by(CalendarEvent.start_time)
        ).scalars().all()

        if not events: return f"Rien de prévu pour le {date_fr}."
        output = [f"📅 Planning du {date_fr}\n"]
        for e in events: output += self._format_event(e)
        return "\n".join(output)

    def _format_event(self, e: CalendarEvent) -> List[str]:
        """Formatting helper for calendar events with multi-day support."""
        label = e.title or e.type.capitalize()
        assigned = (e.assigned_user.username if e.assigned_user else "Non assigné")
        
        # Format dates to FR
        start_dt_fr = datetime.strptime(e.start_date, '%Y-%m-%d').strftime('%d/%m/%Y')
        end_dt_fr   = datetime.strptime(e.end_date, '%Y-%m-%d').strftime('%d/%m/%Y')
        
        # Logic: If the event ends on a different day, show both dates
        if e.start_date == e.end_date:
            time_info = f"Le {start_dt_fr} de {e.start_time} à {e.end_time}"
        else:
            time_info = f"Du {start_dt_fr} ({e.start_time}) au {end_dt_fr} ({e.end_time})"
            
        lines = [
            f"📍 {label}",
            f"   {time_info}",
            f"   Assigné : {assigned}"
        ]
        
        if e.notes:
            lines.append(f"   Note : {e.notes}")
            
        lines.append("")
        return lines

    def _execute_multi_category_search(self, search_term: str) -> str:
        """Searches across products, clients, and doctors for a given term."""
        results = {
            "products": self._search_database(ProductModel, search_term),
            "clients":  self._search_database(ClientModel, search_term),
            "doctors":  self._search_database(DoctorModel, search_term),
        }
        total = sum(len(v) for v in results.values())
        if total == 0:
            return f"Aucun résultat pour '{search_term}'."

        output = [f"🔍 Résultats pour \"{search_term}\" ({total} trouvés)\n"]
        if results["products"]:
            output.append("💊 PRODUITS")
            for p in results["products"][:3]:
                output.append(f"   - {p.name} ({p.stock} unités) {p.price:.2f}€")
        if results["clients"]:
            output.append("\n👤 CLIENTS")
            for c in results["clients"][:3]:
                output.append(f"    {c.first_name} {c.last_name}")
                output.append(f"     📧 {c.email if c.email else 'Non renseigné'}")
                output.append(f"     📞 {c.phone if c.phone else 'Non renseigné'}")
        if results["doctors"]:
            output.append("\n🩺 MÉDECINS")
            for d in results["doctors"][:3]:
                output.append(f"    Dr. {d.last_name} {d.first_name} ({d.specialty})")
                output.append(f"     📧 {d.email if d.email else 'Non renseigné'}")
                output.append(f"     📞 {d.phone if d.phone else 'Non renseigné'}")
                              
        return "\n".join(output)    

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _resolve_to_active_ingredient(self, product_name: str) -> tuple:
        """Resolves trade names to active ingredients using aliases."""
        name = product_name.strip()
        try:
            alias = db.session.execute(db.select(ProductAliasModel).where(ProductAliasModel.alias.ilike(name))).scalars().first()
            if alias: return alias.active_ingredient, name
            product = db.session.execute(db.select(ProductModel).where(ProductModel.name.ilike(f"%{name}%"))).scalars().first()
            if product: return product.active_ingredient, product.name
            return name.capitalize(), name.capitalize()
        except: return name.capitalize(), name.capitalize()

    def _search_database(self, model, search_term: str) -> list:
        """Helper to search specific model in DB."""
        if not model or not search_term: return []
        term = search_term.lower().strip()
        for prefix in ['dr ', 'doc ', 'docteur ', 'mr ', 'mme ']:
            if term.startswith(prefix): term = term[len(prefix):].strip()
        if model == ProductModel:
            condition = or_(model.name.ilike(f"%{term}%"), model.active_ingredient.ilike(f"%{term}%"))
        else:
            condition = or_(model.last_name.ilike(f"%{term}%"), model.first_name.ilike(f"%{term}%"))
        return db.session.execute(db.select(model).where(condition).limit(5)).scalars().all()

    def _generate_help_message(self) -> str:
        """Help instructions in French."""
        return (
            "💡 Aide du Chatbot Pharmacie\n\n"
            "• Recherche : 'Doliprane', 'Dupont'\n"
            "• Stock : 'Stock Aspirine', 'Produits en rupture'\n"
            "• Prix : 'Prix Amoxicilline'\n"
            "• Interactions : 'Aspirine et Advil danger ?'\n"
            "• Ventes : 'Ventes du jour', 'Bilan des ventes'\n"
            "• Agenda : 'Planning de demain', 'Mes rendez-vous'\n"
            "• Contact : 'Contact Dr Martin'\n"
            "• RDV : 'RDV du jour' 'Agenda de la semaine prochaine'\n"
            "• Ticket : 'Ticket #1234', 'Ticket sur imprimante'\n"
            "• Garde : 'Garde du week-end', 'Garde demain'"
        )