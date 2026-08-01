import re
from database.data_manager import db, bcrypt
from sqlalchemy import func, or_, and_, desc
from models.user import UserModel
from models.product import ProductModel
from models.sale import SaleModel, SaleItemModel
from models.client import ClientModel
from models.doctor import DoctorModel
from models.calendar import CalendarEvent
from models.interaction import InteractionModel
from models.interaction_ansm import InteractionAnsmModel
from models.note import Note
from models.ticket import Ticket
from models.specialite import SpecialiteModel
from models.composition import CompositionModel
from utils.text_norm import normalize
from datetime import datetime, UTC


# ==============================================================================
# INTERACTION RESOLUTION — constantes et helpers (ex utils/checker.py)
# ==============================================================================

COMMON_SALTS = [
    r'\bbromhydrate de\b', r'\bchlorhydrate de\b', r'\bsulfate de\b',
    r'\bsodium\b', r'\bpotassium\b', r'\bmaleate de\b', r'\bdihydrate\b',
    r'\bphosphate de\b', r'\bmesilate de\b', r'\btartrate de\b', r'\bacetate de\b'
]

# Dictionnaire de correspondance DCI -> Classe Thérapeutique ANSM
# (évite de devoir toucher à la BDD pour les grandes familles du thésaurus)
ANSM_CLASS_MAPPING = {
    "citalopram": ["INHIBITEURS SÉLECTIFS DE LA RECAPTURE DE LA SÉROTONINE", "ISRS"],
    "escitalopram": ["INHIBITEURS SÉLECTIFS DE LA RECAPTURE DE LA SÉROTONINE", "ISRS"],
    "fluoxetine": ["INHIBITEURS SÉLECTIFS DE LA RECAPTURE DE LA SÉROTONINE", "ISRS"],
    "paroxetine": ["INHIBITEURS SÉLECTIFS DE LA RECAPTURE DE LA SÉROTONINE", "ISRS"],
    "sertraline": ["INHIBITEURS SÉLECTIFS DE LA RECAPTURE DE LA SÉROTONINE", "ISRS"],
    "tramadol": ["TRAMADOL", "OPIOÏDES"],
    "ibuprofene": ["ANTI-INFLAMMATOIRES NON STÉROÏDIENS", "AINS"],
    "ketoprofene": ["ANTI-INFLAMMATOIRES NON STÉROÏDIENS", "AINS"],
    "aspirine": ["ANTI-INFLAMMATOIRES NON STÉROÏDIENS", "AINS"],
    "krameria": ["HEMOSTATIQUES"],
}


def _clean_substance_name(substance: str) -> str:
    text = substance.lower()
    for salt in COMMON_SALTS:
        text = re.sub(salt, '', text)
    return text.strip()


def _expand_substance_terms(substance: str) -> list:
    """
    Prend une molécule (ex: 'citalopram') et retourne :
    1. La molécule elle-même
    2. Les classes thérapeutiques ANSM associées, si connues
    """
    clean_sub = _clean_substance_name(substance)
    terms = [clean_sub]
    for dci, classes in ANSM_CLASS_MAPPING.items():
        if dci in clean_sub:
            terms.extend(classes)
    return list(set(terms))


def _split_ingredients(raw_str: str) -> list:
    """Découpe les chaînes multi-composants (ex: 'paracétamol / codéine')."""
    if not raw_str:
        return []
    temp_str = raw_str
    for delim in [",", "/", "+", ";"]:
        temp_str = temp_str.replace(delim, "|")
    return [ing.strip().lower() for ing in temp_str.split("|") if ing.strip()]


class FacadeService:
    """
    Service layer (Facade) handling all business logic and database interactions (CRUD).
    Standardized to SQLAlchemy 2.0 syntax.
    """

    # --- USER CRUD & AUTHENTICATION METHODS ---

    def get_user_by_username(self, username):
        return db.session.execute(
            db.select(UserModel).filter_by(username=username)
        ).scalar_one_or_none()

    def get_user_by_email(self, email):
        return db.session.execute(
            db.select(UserModel).filter_by(email=email)
        ).scalar_one_or_none()

    def create_user(self, username, email, password, first_name=None, last_name=None, address=None, is_admin=False):
        if self.get_user_by_username(username):
            return "Username already exists."
        if self.get_user_by_email(email):
            return "Email address already in use."

        try:
            new_user = UserModel(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                address=address,
                is_admin=is_admin
            )
            return new_user if new_user.save_to_db() else "Integrity error."
        except Exception as e:
            print(f"Error creating user: {e}")
            return None

    def authenticate_user(self, username, password):
        user = self.get_user_by_username(username)
        if user and user.check_password(password):
            return user
        return None

    def get_all_users(self):
        return db.session.execute(db.select(UserModel)).scalars().all()

    def get_user_by_id(self, user_id):
        return db.session.get(UserModel, user_id)

    def update_user(self, user_id, data):
        user = self.get_user_by_id(user_id)
        if user:
            if 'password' in data:
                user.set_password(data['password'])
                del data['password']
            for key, value in data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            return user if user.save_to_db() else None
        return None

    def delete_user(self, user_id):
        user = self.get_user_by_id(user_id)
        return user.delete_from_db() if user else False

    # --- PRODUCT CRUD METHODS ---

    def get_all_products(self):
        return db.session.execute(db.select(ProductModel)).scalars().all()

    def get_all_products_detailed(self, user_id=None):
        stmt = db.select(ProductModel).order_by(ProductModel.name)
        if user_id:
            stmt = stmt.filter(ProductModel.user_id == user_id)
        return db.session.execute(stmt).scalars().all()

    def get_product_by_id(self, product_id):
        return db.session.get(ProductModel, product_id)

    def get_product_by_name(self, name):
        return db.session.execute(
            db.select(ProductModel).filter_by(name=name)
        ).scalar_one_or_none()

    def create_product(self, name, active_ingredient, dosage, stock, price, is_prescription_only, user_id,
                        cis=None, cip13=None):
        try:
            new_product = ProductModel(
                name=name, active_ingredient=active_ingredient, dosage=dosage,
                stock=stock, price=price, is_prescription_only=is_prescription_only, user_id=user_id,
                cis=cis, cip13=cip13
            )
            return new_product if new_product.save_to_db() else None
        except Exception as e:
            print(f"Error creating product: {e}")
            return None

    def update_product(self, product_id, data):
        product = self.get_product_by_id(product_id)
        if product:
            for key, value in data.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            return product if product.save_to_db() else None
        return None

    def delete_product(self, product_id):
        product = self.get_product_by_id(product_id)
        return product.delete_from_db() if product else False

    # --- SALE METHODS ---

    def get_all_sales(self, user_id=None):
        stmt = db.select(SaleModel).order_by(desc(SaleModel.sale_date))
        if user_id:
            stmt = stmt.filter(SaleModel.user_id == user_id)
        return db.session.execute(stmt).scalars().all()

    def get_sale_by_id(self, sale_id):
        return db.session.get(SaleModel, sale_id)

    def process_sale(self, client_id, doctor_id, items_data, user_id, created_at=None):
        if not items_data:
            raise ValueError("No items provided for sale.")

        total_amount = 0
        validated_items = []

        for item in items_data:
            product = self.get_product_by_id(item['product_id'])
            if not product:
                raise ValueError(f"Product not found: {item['product_id']}")
            if product.stock < item['quantity']:
                raise ValueError(f"Insufficient stock for {product.name}")
            if product.is_prescription_only and not doctor_id:
                raise ValueError(f"Prescription required for {product.name}")

            total_amount += product.price * item['quantity']
            validated_items.append({'product': product, 'quantity': item['quantity'], 'price': product.price})

        try:
            new_sale = SaleModel(
                user_id=user_id,
                client_id=client_id,
                doctor_id=doctor_id,
                prescription_provided=bool(doctor_id),
                total_amount=total_amount,
                sale_date=created_at
            )
            db.session.add(new_sale)
            db.session.flush()

            for item_data in validated_items:
                item_data['product'].stock -= item_data['quantity']
                db.session.add(SaleItemModel(
                    sale_id=new_sale.id, product_id=item_data['product'].id,
                    quantity=item_data['quantity'], price_at_sale=item_data['price']
                ))

            db.session.commit()
            return new_sale
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Sale failed: {str(e)}")

    # --- ANALYTICS METHODS ---

    def get_sales_revenue_stats(self):
        stmt = (
            db.select(
                func.date(SaleModel.sale_date).label('date'),
                func.sum(SaleModel.total_amount).label('total')
            )
            .group_by(func.date(SaleModel.sale_date))
            .order_by(func.date(SaleModel.sale_date))
        )
        results = db.session.execute(stmt).all()
        return {
            "labels": [str(r.date) for r in results],
            "values": [float(r.total) for r in results]
        }

    def get_stock_alerts(self):
        stmt = db.select(ProductModel).filter(ProductModel.stock <= 10)
        return db.session.execute(stmt).scalars().all()

    def get_daily_stats(self):
        today = datetime.now(UTC).strftime('%Y-%m-%d')
        stmt = (
            db.select(
                func.strftime('%H', SaleModel.sale_date).label('hour'),
                func.sum(SaleModel.total_amount).label('revenue'),
                func.count(SaleModel.id).label('sale_count')
            )
            .filter(func.strftime('%Y-%m-%d', SaleModel.sale_date) == today)
            .group_by('hour')
            .order_by('hour')
        )
        return db.session.execute(stmt).all()

    def get_monthly_stats(self):
        first_day = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0).strftime('%Y-%m-%d')
        stmt = (
            db.select(
                func.strftime('%Y-%m-%d', SaleModel.sale_date).label('day'),
                func.sum(SaleModel.total_amount).label('revenue'),
                func.count(SaleModel.id).label('sale_count')
            )
            .filter(SaleModel.sale_date >= first_day)
            .group_by('day')
            .order_by('day')
        )
        return db.session.execute(stmt).all()

    # --- CLIENT CRUD METHODS ---

    def get_all_clients(self):
        return db.session.execute(db.select(ClientModel)).scalars().all()

    def get_client_by_id(self, client_id):
        return db.session.get(ClientModel, client_id)

    def get_client_by_last_name(self, last_name):
        return db.session.execute(db.select(ClientModel).filter_by(last_name=last_name)).scalar_one_or_none()

    def create_client(self, first_name, last_name, email, phone, address, user_id):
        new_client = ClientModel(first_name=first_name, last_name=last_name, email=email, phone=phone,
                                  address=address, user_id=user_id)
        return new_client if new_client.save_to_db() else None

    def search_clients(self, query):
        stmt = db.select(ClientModel).filter(
            (ClientModel.first_name.ilike(f"%{query}%")) |
            (ClientModel.last_name.ilike(f"%{query}%")) |
            (ClientModel.email.ilike(f"%{query}%"))
        ).limit(20)
        return db.session.execute(stmt).scalars().all()

    def update_client(self, client_id, data):
        client = self.get_client_by_id(client_id)
        if client:
            for key, value in data.items():
                if hasattr(client, key):
                    setattr(client, key, value)
            return client if client.save_to_db() else None
        return None

    def delete_client(self, client_id):
        client = self.get_client_by_id(client_id)
        return client.delete_from_db() if client else False

    # --- DOCTOR CRUD METHODS ---

    def get_all_doctors(self):
        return db.session.execute(db.select(DoctorModel)).scalars().all()

    def get_doctor_by_id(self, doctor_id):
        return db.session.get(DoctorModel, doctor_id)

    def search_doctors(self, query):
        stmt = db.select(DoctorModel).filter(
            (DoctorModel.first_name.ilike(f"%{query}%")) |
            (DoctorModel.last_name.ilike(f"%{query}%")) |
            (DoctorModel.specialty.ilike(f"%{query}%")) |
            (DoctorModel.email.ilike(f"%{query}%"))
        ).limit(20)
        return db.session.execute(stmt).scalars().all()

    def create_doctor(self, first_name, last_name, email, address, specialty, phone, user_id):
        new_doctor = DoctorModel(
            first_name=first_name, last_name=last_name, email=email,
            address=address, specialty=specialty, phone=phone, user_id=user_id
        )
        return new_doctor if new_doctor.save_to_db() else None

    def update_doctor(self, doctor_id, data):
        doctor = self.get_doctor_by_id(doctor_id)
        if doctor:
            for key, value in data.items():
                if hasattr(doctor, key):
                    setattr(doctor, key, value)
            return doctor if doctor.save_to_db() else None
        return None

    def delete_doctor(self, doctor_id):
        doctor = self.get_doctor_by_id(doctor_id)
        return doctor.delete_from_db() if doctor else False

    # ==========================================================================
    # INTERACTION METHODS — point d'entrée unique pour le chatbot
    # ==========================================================================

    def resolve_substances(self, term: str) -> list:
        """
        Identifie toutes les substances actives associées à un terme libre
        (nom de marque, DCI, produit du stock...).

        Ordre de résolution :
        1. Stock local (ProductModel) — priorité, c'est ce que la pharmacie vend réellement
        2. Référentiel ANSM (SpecialiteModel + compositions)
        3. Fallback : le terme nettoyé tel quel

        Le terme nettoyé est TOUJOURS ajouté en plus, même si 1 ou 2 ont donné
        un résultat : le Thésaurus ANSM utilise parfois un nom générique court
        (ex: "millepertuis") alors que la composition BDPM utilise la
        dénomination pharmaceutique complète (ex: "extrait sec de la sommité
        fleurie de millepertuis"), qui ne matche jamais par ilike simple.
        """
        if not term:
            return []

        clean_term = normalize(term).lower().strip()
        clean_base = re.sub(r'\b\d+\s*(mg|g|ml|mcg|ui|gtt)?\b', '', clean_term).strip()
        if not clean_base:
            return []

        resolved = []

        # 1. Stock local
        prod = db.session.execute(
            db.select(ProductModel).where(
                or_(
                    ProductModel.name.ilike(f"%{clean_base}%"),
                    ProductModel.active_ingredient.ilike(f"%{clean_base}%")
                )
            )
        ).scalars().first()

        if prod and prod.active_ingredient and prod.active_ingredient.lower() != 'n/a':
            resolved = _split_ingredients(prod.active_ingredient)

        # 2. Référentiel ANSM
        if not resolved:
            spec = db.session.execute(
                db.select(SpecialiteModel).where(SpecialiteModel.search_name.ilike(f"%{clean_base}%"))
            ).scalars().first()

            if spec:
                subs = [
                    c.denomination_substance.strip().lower()
                    for c in spec.compositions
                    if getattr(c, 'nature_composant', 'SA') == 'SA' and c.denomination_substance
                ]
                if subs:
                    resolved = subs

        # 3. Fallback si rien trouvé du tout
        if not resolved:
            resolved = [clean_base]

        # Toujours garder le terme utilisateur en secours
        if clean_base not in resolved:
            resolved.append(clean_base)

        return resolved

    def get_interaction(self, ingredient_a: str, ingredient_b: str):
        """
        Cherche une interaction déjà connue entre DEUX SUBSTANCES (pas des
        noms de marque — utiliser resolve_substances() en amont).
        Priorité à InteractionModel (curatée), fallback InteractionAnsmModel
        (thésaurus complet).
        """
        norm_a = normalize(ingredient_a).lower().strip()
        norm_b = normalize(ingredient_b).lower().strip()
        if not norm_a or not norm_b or norm_a == norm_b:
            return None

        stmt = db.select(InteractionModel).where(
            or_(
                and_(InteractionModel.ingredient_a.ilike(f"%{norm_a}%"), InteractionModel.ingredient_b.ilike(f"%{norm_b}%")),
                and_(InteractionModel.ingredient_a.ilike(f"%{norm_b}%"), InteractionModel.ingredient_b.ilike(f"%{norm_a}%"))
            )
        )
        result = db.session.execute(stmt).scalars().first()
        if result:
            return result

        stmt_ansm = (
            db.select(InteractionAnsmModel)
            .where(
                or_(
                    and_(InteractionAnsmModel.substance_a_norm.ilike(f"%{norm_a}%"), InteractionAnsmModel.substance_b_norm.ilike(f"%{norm_b}%")),
                    and_(InteractionAnsmModel.substance_a_norm.ilike(f"%{norm_b}%"), InteractionAnsmModel.substance_b_norm.ilike(f"%{norm_a}%"))
                )
            )
            .order_by(func.length(InteractionAnsmModel.substance_a_norm) + func.length(InteractionAnsmModel.substance_b_norm))
        )
        return db.session.execute(stmt_ansm).scalars().first()

    def check_drug_interaction(self, term_a: str, term_b: str) -> dict:
        """
        Point d'entrée UNIQUE pour le chatbot : prend deux noms libres
        (marque, DCI, produit du stock...) et retourne un verdict complet.
        """
        subs_a = self.resolve_substances(term_a)
        subs_b = self.resolve_substances(term_b)

        if not subs_a or not subs_b:
            return {
                "has_interaction": False,
                "term_a": term_a, "term_b": term_b,
                "substances_a": subs_a, "substances_b": subs_b,
                "message": "Impossible de déterminer les substances actives."
            }

        for sa in subs_a:
            clean_sa = _clean_substance_name(sa)
            terms_a = _expand_substance_terms(sa)

            for sb in subs_b:
                clean_sb = _clean_substance_name(sb)

                # A. Alerte surdosage (même substance des deux côtés)
                if normalize(clean_sa).lower() == normalize(clean_sb).lower() and clean_sa != "n/a":
                    return {
                        "has_interaction": True,
                        "severity": "Critical",
                        "description": f"Risque de surdosage : les deux traitements contiennent du {clean_sa.title()}.",
                        "substance_a": clean_sa, "substance_b": clean_sb,
                        "term_a": term_a, "term_b": term_b
                    }

                # B. Recherche croisée (curatée + thésaurus ANSM), avec expansion de classe
                terms_b = _expand_substance_terms(sb)
                for ta in terms_a:
                    for tb in terms_b:
                        interaction = self.get_interaction(ta, tb)
                        if interaction:
                            return {
                                "has_interaction": True,
                                "severity": interaction.severity,
                                "description": interaction.description,
                                "substance_a": clean_sa, "substance_b": clean_sb,
                                "term_a": term_a, "term_b": term_b
                            }

        return {
            "has_interaction": False,
            "term_a": term_a, "term_b": term_b,
            "substances_a": subs_a, "substances_b": subs_b,
            "message": "Aucune interaction trouvée dans les bases disponibles."
        }

    # --- RÉFÉRENTIEL ANSM (Spécialités / Compositions) ---

    def get_substances_by_cis(self, cis: str) -> list:
        """Substances actives pour un code CIS donné."""
        stmt = db.select(CompositionModel.denomination_substance).where(CompositionModel.cis == cis)
        results = db.session.execute(stmt).scalars().all()
        return [r.strip() for r in results if r]

    def find_specialite_by_name(self, term: str, limit: int = 5):
        """Recherche une spécialité ANSM par nom ou par code CIS."""
        clean_term = term.strip()
        if not clean_term:
            return []

        norm_term = normalize(clean_term)

        if clean_term.isdigit():
            stmt = (
                db.select(SpecialiteModel)
                .where(or_(SpecialiteModel.cis.ilike(f"%{clean_term}%"), SpecialiteModel.search_name.ilike(f"%{norm_term}%")))
                .order_by(func.length(SpecialiteModel.denomination))
                .limit(limit)
            )
        else:
            stmt = (
                db.select(SpecialiteModel)
                .where(SpecialiteModel.search_name.ilike(f"%{norm_term}%"))
                .order_by(func.length(SpecialiteModel.denomination))
                .limit(limit)
            )
        return db.session.execute(stmt).scalars().all()

    def get_specialite_by_cis(self, cis: str):
        return db.session.get(SpecialiteModel, cis)

    # --- NOTES METHODS ---

    def get_all_notes(self):
        stmt = db.select(Note).order_by(desc(Note.created_at))
        return db.session.execute(stmt).scalars().all()

    def get_notes_by_user(self, user_id):
        stmt = db.select(Note).filter_by(user_id=user_id).order_by(desc(Note.created_at))
        return db.session.execute(stmt).scalars().all()

    def get_note_by_id(self, note_id):
        return db.session.get(Note, note_id)

    def create_note(self, user_id, text):
        try:
            new_note = Note(user_id=user_id, text=text)
            return new_note if new_note.save_to_db() else None
        except Exception as e:
            print(f"Error creating note: {e}")
            return None

    def update_note_text(self, note_id, new_text):
        note = self.get_note_by_id(note_id)
        if note:
            note.update_text(new_text)
            return note
        return None

    def delete_note(self, note_id):
        note = self.get_note_by_id(note_id)
        if not note:
            print(f"Delete failed: Note {note_id} not found.")
            return False
        try:
            note.delete()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error deleting note {note_id}: {e}")
            return False

    # --- TICKET CRUD METHODS ---

    def get_all_tickets(self, user_id=None):
        stmt = db.select(Ticket).order_by(desc(Ticket.created_at))
        if user_id:
            stmt = stmt.filter(Ticket.user_id == user_id)
        return db.session.execute(stmt).scalars().all()

    def get_ticket_by_id(self, ticket_id):
        str_id = str(ticket_id)
        return db.session.get(Ticket, str_id)

    def create_ticket(self, user_id, subject, description, priority='medium'):
        try:
            new_ticket = Ticket(
                user_id=user_id,
                subject=subject,
                description=description,
                priority=priority
            )
            db.session.add(new_ticket)
            db.session.commit()
            return new_ticket
        except Exception as e:
            db.session.rollback()
            print(f"Error creating ticket: {e}")
            return None

    def update_ticket(self, ticket_id, data):
        ticket = self.get_ticket_by_id(ticket_id)
        if ticket:
            for key, value in data.items():
                if hasattr(ticket, key):
                    setattr(ticket, key, value)
            try:
                db.session.commit()
                return ticket
            except Exception:
                db.session.rollback()
                return None
        return None

    def delete_ticket(self, ticket_id):
        ticket = self.get_ticket_by_id(ticket_id)
        if ticket:
            try:
                db.session.delete(ticket)
                db.session.commit()
                return True
            except Exception:
                db.session.rollback()
                return False
        return False

    # --- CALENDAR METHOD ---

    def get_events_by_date(self, date_str):
        from models.calendar import CalendarEvent
        stmt = (
            db.select(CalendarEvent)
            .filter(func.date(CalendarEvent.start_time) == date_str)
            .order_by(CalendarEvent.start_time)
        )
        return db.session.execute(stmt).scalars().all()