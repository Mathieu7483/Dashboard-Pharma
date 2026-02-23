"""
Server/core/chatbot/ChatBot_engine.py
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


class ChatBotEngine:

    def __init__(self):
        self.nlu = NLUProcessor()
        self.nlu.load_products_from_db()
        self._temporal_words = {
            "demain", "aujourd'hui", "hier",
            "semaine", "prochaine", "prochain",
            "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"
        }



    def _norm(self, s: str) -> str:
        """Normalise une chaîne : minuscules et suppression des accents."""
        if not s: return ""
        return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii").lower().strip()

    # =========================================================================
    # POINT D'ENTREE
    # =========================================================================

    def process_query(self, user_text: str) -> dict:
        # Empty input -> message d'aide
        if not user_text or not user_text.strip():
            return {
                "intent": "unknown",
                "reply": "Posez une question. Exemples : 'Stock Doliprane' ou 'Ventes du jour'"
            }

        analysis = self.nlu.analyze(user_text)
        intent   = analysis.get("intent", "unknown")
        entities = analysis.get("entity_list", [])

        try:
            response_text = ""

            if intent == "greeting":
                response_text = "Bonjour ! Comment puis-je vous aider ?"

            elif intent == "get_help":
                response_text = self._generate_help_message()

            elif intent == "check_interaction":
                response_text = self._handle_interaction_check(entities)

            elif intent == "get_stock_alerts":
                response_text = self._handle_stock_alerts()

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

            elif intent in ("get_doctor", "get_client", "list_all", "get_product"):
                if not entities:
                    response_text = self._generate_help_message()
                else:
                    response_text = self._execute_multi_category_search(entities[0])

            else:
                if entities:
                    response_text = self._execute_multi_category_search(entities[0])
                else:
                    response_text = self._generate_help_message()
                    intent = "get_help"

            return {
                "intent": intent,
                "reply": response_text
            }

        except Exception as e:
            import traceback
            print(f"ChatBot Error: {e}")
            traceback.print_exc()
            return {
                "intent": "error",
                "reply": "Erreur lors du traitement. Reformulez votre demande."
            }

    # =========================================================================
    # HANDLERS
    # =========================================================================

    def _handle_interaction_check(self, entity_list: list) -> str:
        if len(entity_list) < 2:
            return (
                "Mentionnez au moins DEUX produits pour vérifier la compatibilité.\n\n"
                "Exemples :\n"
                "   - 'Aspirine et Ibuprofène compatibles ?'\n"
                "   - 'Doliprane avec Advil danger ?'"
            )

        resolved, display_names = [], []
        for name in entity_list:
            ingredient, display = self._resolve_to_active_ingredient(name)
            # On stocke le nom propre pour l'affichage, 
            # MAIS on normalise l'ingrédient pour la recherche DB
            resolved.append(self._norm(ingredient))
            display_names.append(display)

        print(f"Resolved (Normalized): {list(zip(display_names, resolved))}")

        conflicts = []
        for i in range(len(resolved)):
            for j in range(i + 1, len(resolved)):
                a, b = resolved[i], resolved[j]
                
                # On utilise la version normalisée (a et b) dans le ILIKE
                result = db.session.execute(
                    db.select(InteractionModel).where(
                        or_(
                            (InteractionModel.ingredient_a.ilike(f"%{a}%")) & 
                            (InteractionModel.ingredient_b.ilike(f"%{b}%")),
                            (InteractionModel.ingredient_a.ilike(f"%{b}%")) & 
                            (InteractionModel.ingredient_b.ilike(f"%{a}%"))
                        )
                    )
                ).scalar_one_or_none()
                
                if result:
                    conflicts.append({
                        "interaction": result, 
                        "name_a": display_names[i], 
                        "name_b": display_names[j]
                    })

        if not conflicts:
            return (
                "✅ Aucune interaction connue\n\n"
                f"Produits analysés : {' + '.join(display_names)}\n\n"
                "⚠️ Consultez toujours un professionnel de santé."
            )

        severity_emoji = {"low": "⚠️", "moderate": "🟠", "high": "🔴", "critical": "🔴🔴"}
        output = ["🚨 ALERTE INTERACTION MÉDICAMENTEUSE\n",
                  f"Analyse pour : {' + '.join(display_names)}\n"]
        
        for c in conflicts:
            ix = c["interaction"]
            emoji = severity_emoji.get(ix.severity.lower(), "⚠️")
            output += [
                f"{emoji} {c['name_a']} + {c['name_b']}",
                f"Gravité : {ix.severity.upper()}",
                f"Détails : {ix.description}",
                "---\n"
            ]
        output.append("⚠️ IMPORTANT : Consultez un pharmacien avant utilisation.")
        return "\n".join(output)
    

    def _handle_stock_query(self, entities: list) -> str:
        if not entities:
            return "Quel produit souhaitez-vous verifier ?"
        products = self._search_database(ProductModel, entities[0])
        if not products:
            return f"Aucun produit trouve pour '{entities[0]}'."
        output = [f" Etat des stocks : {entities[0].capitalize()}"]
        for p in products:
            if p.stock > 100:   emoji, status = "🟢", "Excellent"
            elif p.stock > 50:  emoji, status = "🟢", "Bon"
            elif p.stock > 20:  emoji, status = "🟡", "Moyen"
            elif p.stock > 5:   emoji, status = "🟠", "Faible"
            else:               emoji, status = "⚠️🔴", "CRITIQUE"
            rx = "Ordonnance" if p.is_prescription_only else "Libre"
            output.append(f"   {emoji} {p.name} ({p.dosage}) - {p.stock} unites ({status}) | {p.price:.2f}EUR | {rx}")
        return "\n".join(output)

    def _handle_price_query(self, entities: list) -> str:
        if not entities:
            return "Quel produit cherchez-vous ?"
        product = db.session.execute(
            db.select(ProductModel).where(ProductModel.name.ilike(f"%{entities[0]}%"))
        ).scalar_one_or_none()
        if not product:
            return f"Produit '{entities[0]}' introuvable."
        rx = "Sur ordonnance" if product.is_prescription_only else "Vente libre"
        return (
            f" {product.name}\n"
            f"   Prix : {product.price:.2f} EUR\n"
            f"   Type : {rx}\n"
            f"   Dosage : {product.dosage}\n"
            f"   Stock : {product.stock} unites"
        )

    def _handle_prescription_info(self, entities: list) -> str:
        if not entities:
            return "Quel medicament souhaitez-vous verifier ?"
        product = db.session.execute(
            db.select(ProductModel).where(ProductModel.name.ilike(f"%{entities[0]}%"))
        ).scalar_one_or_none()
        if not product:
            return f"Produit '{entities[0]}' introuvable."
        if product.is_prescription_only:
            return (
                f"{product.name} necessite une ordonnance medicale.\n"
                f"   Principe actif : {product.active_ingredient}\n"
                f"   Dosage : {product.dosage}"
            )
        return (
            f"{product.name} est disponible en vente libre.\n"
            f"   Prix : {product.price:.2f} EUR\n"
            f"   Stock : {product.stock} unites"
        )

    def _handle_stock_alerts(self) -> str:
        threshold = 20
        low_stock = db.session.execute(
            db.select(ProductModel).where(ProductModel.stock < threshold).order_by(ProductModel.stock)
        ).scalars().all()
        if not low_stock:
            return f"🟢 Tous les produits ont un stock suffisant (>={threshold} unites)."
        output = [f"⚠️ Alertes Stock Bas (< {threshold} unites)\n"]
        critical = [p for p in low_stock if p.stock < 5]
        warning  = [p for p in low_stock if 5 <= p.stock < threshold]
        if critical:
            output.append("🔴CRITIQUE (< 5 unites)")
            for p in critical:
                output.append(f"   {p.name} : {p.stock} unites")
            output.append("")
        if warning:
            output.append("🟠FAIBLE (5-19 unites)")
            for p in warning:
                output.append(f"   {p.name} : {p.stock} unites")
        output.append(f"\n{len(low_stock)} produits necessitent un reapprovisionnement.")
        return "\n".join(output)

    def _handle_sales_summary(self) -> str:
        try:
            today      = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())

            def _q(filter_):
                return db.session.query(
                    func.count(SaleModel.id),
                    func.sum(SaleModel.total_amount)
                ).filter(filter_).first()

            ct, rt = _q(cast(SaleModel.sale_date, Date) == today)
            cw, rw = _q(SaleModel.sale_date >= week_start)
            ca, ra = _q(True)
            ct, rt = ct or 0, rt or 0.0
            cw, rw = cw or 0, rw or 0.0
            ca, ra = ca or 0, ra or 0.0

            output = [
                " Performances de Vente\n",
                f" Aujourd'hui ({today.strftime('%d/%m/%Y')})",
                f"   Transactions : {ct}",
                f"   CA : {rt:.2f} EUR\n",
                f" Cette semaine (depuis le {week_start.strftime('%d/%m')})",
                f"   Transactions : {cw}",
                f"   CA : {rw:.2f} EUR\n",
                " Cumule total",
                f"   Transactions : {ca}",
                f"   CA total : {ra:.2f} EUR",
            ]
            if ca > 0:
                output.append(f"   Panier moyen : {ra/ca:.2f} EUR")
            return "\n".join(output)
        except Exception as e:
            return f"Erreur statistiques : {str(e)}"

    def _handle_contact_search(self, entities: list) -> str:
        if not entities:
            return "De qui souhaitez-vous obtenir les coordonnees ?"
        search_term = entities[0]
        person = self._search_database(DoctorModel, search_term)
        category = "Medecin"
        if not person:
            person = self._search_database(ClientModel, search_term)
            category = "Client"
        if not person:
            return f"Aucun contact trouve pour '{search_term}'."
        p = person[0]
        output = [
            f" Coordonnees - {p.first_name} {p.last_name}",
            f"   Poste : {category}",
            f"   Tel : {p.phone or 'Non renseigne'}",
            f"   Email : {p.email or 'Non renseigne'}",
        ]
        if hasattr(p, 'address') and p.address:
            output.append(f"   Adresse : {p.address}")
        return "\n".join(output)

    def _handle_ticket_info(self, entities: list) -> str:
        if not entities:
            return "Quel ticket souhaitez-vous consulter ? Ex: 'Ticket Doliprane' ou 'Ticket #1234'"
        search_term = entities[0].strip()
        if search_term.startswith("#"):
            ticket = db.session.execute(
                db.select(Ticket).where(Ticket.id == search_term[1:])
            ).scalar_one_or_none()
        else:
            ticket = db.session.execute(
                db.select(Ticket).where(Ticket.subject.ilike(f"%{search_term}%"))
            ).scalar_one_or_none()
        if not ticket:
            return f"Aucun ticket trouve pour '{search_term}'."
        output = [
            f"## Ticket #{ticket.id[:8]}...",
            f"   Sujet : {ticket.subject}",
            f"   Description : {ticket.description}",
            f"   Priorite : {ticket.priority.capitalize()}",
            f"   Statut : {ticket.status.capitalize()}",
            f"   Cree le : {ticket.created_at.strftime('%d/%m/%Y %H:%M')}",
            f"   Utilisateur : {ticket.user_id[:8]}...",
        ]
        if ticket.admin_note:
            output.append(f"   Note admin : {ticket.admin_note}")
        return "\n".join(output)

    def _handle_calendar_events(self, entities: list, user_text: str = "") -> str:
        """
        FIX: si mot temporel detecte -> _handle_schedule_query.
        Sinon filtre par titre/type/notes sur les 7 prochains jours.
        """
        text_lower = user_text.lower()

        # Mot temporel -> planning par date
        if any(tw in text_lower for tw in self._temporal_words):
            return self._handle_schedule_query(user_text)

        today_str    = datetime.now().strftime("%Y-%m-%d")
        week_end_str = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        # Pas d'entite -> agenda 7 jours complet
        if not entities:
            events = db.session.execute(
                db.select(CalendarEvent)
                .options(selectinload(CalendarEvent.assigned_user),
                         selectinload(CalendarEvent.creator))
                .where(CalendarEvent.start_date >= today_str,
                       CalendarEvent.start_date <= week_end_str)
                .order_by(CalendarEvent.start_date, CalendarEvent.start_time)
            ).scalars().all()
            if not events:
                return "Aucun evenement prevu dans les 7 prochains jours."
            output = ["📅 Agenda - 7 prochains jours\n"]
            for e in events:
                output += self._format_event(e)
            return "\n".join(output)

        # Entite -> filtre
        search_term = entities[0].strip().lower()
        events = db.session.execute(
            db.select(CalendarEvent)
            .options(selectinload(CalendarEvent.assigned_user),
                     selectinload(CalendarEvent.creator))
            .where(
                CalendarEvent.start_date >= today_str,
                CalendarEvent.start_date <= week_end_str,
                or_(
                    CalendarEvent.title.ilike(f"%{search_term}%"),
                    CalendarEvent.notes.ilike(f"%{search_term}%"),
                    CalendarEvent.type.ilike(f"%{search_term}%"),
                )
            )
            .order_by(CalendarEvent.start_date, CalendarEvent.start_time)
        ).scalars().all()

        if not events:
            return (
                f"Aucun evenement pour '{search_term}' dans les 7 prochains jours.\n\n"
                "Essayez : 'rdv', 'garde', ou le nom d'un collaborateur."
            )
        output = [f"📅 Evenements - '{search_term}'\n"]
        for e in events:
            output += self._format_event(e)
        return "\n".join(output)

    def _handle_schedule_query(self, user_text: str) -> str:
        """
        FIX: desormais appelee depuis _handle_calendar_events.
        Gere aujourd'hui, demain, hier et les jours nommes.
        """
        text_lower = user_text.lower()
        now = datetime.now()

        if "demain" in text_lower:
            target = now + timedelta(days=1)
        elif "hier" in text_lower:
            target = now - timedelta(days=1)
        elif "aujourd" in text_lower:
            target = now
        else:
            jours = {"lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3,
                     "vendredi": 4, "samedi": 5, "dimanche": 6}
            target = now
            for jour, num in jours.items():
                if jour in text_lower:
                    diff = (num - now.weekday()) % 7 or 7
                    target = now + timedelta(days=diff)
                    break

        date_iso = target.strftime("%Y-%m-%d")
        date_fr  = target.strftime("%d/%m/%Y")

        events = db.session.execute(
            db.select(CalendarEvent)
            .options(selectinload(CalendarEvent.assigned_user),
                     selectinload(CalendarEvent.creator))
            .where(CalendarEvent.start_date == date_iso)
            .order_by(CalendarEvent.start_time)
        ).scalars().all()

        if not events:
            return f"Aucun evenement prevu pour le {date_fr}."

        output = [f"📅 Planning du {date_fr}\n"]
        for e in events:
            output += self._format_event(e)
        return "\n".join(output)

    def _format_event(self, e: CalendarEvent) -> List[str]:
        label    = e.title or e.type.capitalize()
        assigned = (e.assigned_user.username if e.assigned_user
                    else e.creator.username  if e.creator
                    else "Non assigne")
        lines = [
            f"### {label}",
            f"Date : {e.start_date} de {e.start_time} a {e.end_time}",
            f"Assigne a : {assigned}",
        ]
        if e.notes:
            lines.append(f"Notes : {e.notes}")
        lines.append("")
        return lines

    # =========================================================================
    # RECHERCHE MULTI-CATEGORIES
    # =========================================================================

    def _execute_multi_category_search(self, search_term: str) -> str:
        results = {
            "products": self._search_database(ProductModel, search_term),
            "clients":  self._search_database(ClientModel, search_term),
            "doctors":  self._search_database(DoctorModel, search_term),
        }
        total = sum(len(v) for v in results.values())

        if total == 0:
            return (
                f"Aucun resultat pour '{search_term}'.\n\n"
                "Suggestions :\n"
                " - Verifiez l'orthographe\n"
                " - Essayez un nom plus court\n"
                " - Utilisez une partie du nom"
            )

        output = [f" Resultats pour \"{search_term}\"",
                  f"{total} resultat(s) trouve(s)\n"]

        if results["products"]:
            output.append(f"💊 PRODUITS ({len(results['products'])})\n")
            for p in results["products"][:5]:
                rx    = "Ordonnance" if p.is_prescription_only else "Libre"
                stock = "🟢" if p.stock >= 20 else ("🟠" if p.stock >= 10 else "🔴")
                output += [
                    f"{p.name}",
                    f"   Stock : {stock} {p.stock} unites",
                    f"   Prix : {p.price:.2f} EUR | {rx}",
                    f"   Compo : {p.active_ingredient} ({p.dosage})", ""
                ]

        if results["clients"]:
            output.append(f"👤 CLIENTS ({len(results['clients'])})\n")
            for c in results["clients"][:3]:
                output += [
                    f"{c.first_name} {c.last_name}".upper(),
                    f"   Tel : {c.phone or 'Non renseigne'}",
                    f"   Email : {c.email or 'Non renseigne'}", ""
                ]

        if results["doctors"]:
            output.append(f"🩺 MEDECINS ({len(results['doctors'])})\n")
            for d in results["doctors"][:3]:
                output += [
                    f"Dr. {d.first_name} {d.last_name}",
                    f"   Specialite : {d.specialty or 'Generaliste'}",
                    f"   Tel : {d.phone or 'Non renseigne'}",
                    f"   Email : {d.email or 'Non renseigne'}", ""
                ]

        if total > 1:
            output += ["---", "Precisez avec 'stock', 'prix', 'Dr' ou 'contact' pour plus de details"]
        return "\n".join(output)

    # =========================================================================
    # UTILITAIRES
    # =========================================================================

    def _resolve_to_active_ingredient(self, product_name: str) -> tuple:
        name = product_name.strip()
        try:
            alias = db.session.execute(
                db.select(ProductAliasModel).where(ProductAliasModel.alias.ilike(name))
            ).scalars().first()
            if alias:
                return alias.active_ingredient, name
            product = db.session.execute(
                db.select(ProductModel)
                .where(ProductModel.name.ilike(f"%{name}%"))
                .order_by(func.length(ProductModel.name))
            ).scalars().first()
            if product:
                return product.active_ingredient, product.name
            return name.capitalize(), name.capitalize()
        except Exception as e:
            print(f"Resolution produit '{name}': {e}")
            return name.capitalize(), name.capitalize()

    def _search_database(self, model, search_term: str) -> list:
        if not model or not search_term:
            return []
        term = search_term.lower().strip()
        for prefix in ['dr ', 'doc ', 'docteur ', 'doctor ', 'mr ', 'mme ', 'mlle ']:
            if term.startswith(prefix):
                term = term[len(prefix):].strip()
        if model == ProductModel:
            condition = or_(
                model.name.ilike(f"%{term}%"),
                model.active_ingredient.ilike(f"%{term}%"),
            )
        else:
            condition = or_(
                model.last_name.ilike(f"%{term}%"),
                model.first_name.ilike(f"%{term}%"),
            )
            if " " in term:
                a, b = term.split(" ", 1)
                condition = or_(
                    condition,
                    model.first_name.ilike(f"%{a}%") & model.last_name.ilike(f"%{b}%"),
                    model.first_name.ilike(f"%{b}%") & model.last_name.ilike(f"%{a}%"),
                )
        return db.session.execute(db.select(model).where(condition).limit(5)).scalars().all()

    def _generate_help_message(self) -> str:
        return (
            "Comment utiliser le Chatbot\n\n"
            "Recherche universelle :\n"
            "- 'Aspirine' -> Produits, clients ET docteurs\n"
            "- 'Dupont' -> Tous les Dupont\n\n"
            "Produits :\n"
            "- 'Stock Doliprane' -> Inventaire\n"
            "- 'Prix Amoxicilline' -> Tarif\n"
            "- 'Aspirine ordonnance ?' -> Prescription ?\n\n"
            "Interactions :\n"
            "- 'Aspirine et Ibuprofene compatibles ?'\n"
            "- 'Doliprane avec Advil danger ?'\n\n"
            "Analyses :\n"
            "- 'Ventes du jour' -> CA et statistiques\n"
            "- 'Produits en rupture' -> Alertes stock\n\n"
            "Agenda :\n"
            "- 'Rdv' -> Rendez-vous cette semaine\n"
            "- 'Garde' -> Gardes planifiees\n"
            "- 'Planning de demain' -> Evenements demain\n\n"
            "Coordonnees :\n"
            "- 'Contact Dr Martin' -> Coordonnees medecin\n"
            "- 'Telephone client Lefevre' -> Numero client"
        )