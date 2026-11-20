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
from models.classe_ansm import ClasseMembreModel
from utils.text_norm import normalize
from datetime import datetime, UTC


# ==============================================================================
# INTERACTION RESOLUTION — constantes et helpers
# ==============================================================================

# Sels / formes à retirer pour obtenir une variante "courte" du nom de substance.
# NB: "sodium"/"potassium" ne sont volontairement PAS retirés seuls : ils font partie
# de vraies substances du thésaurus (ex: "canrenoate de potassium", "sodium (bicarbonate de)").
COMMON_SALTS = [
    r'\bbromhydrate de\b', r'\bchlorhydrate de\b', r'\bsulfate de\b',
    r'\bmaleate de\b', r'\bdihydrate\b', r'\bphosphate de\b',
    r'\bmesilate de\b', r'\btartrate de\b', r'\bacetate de\b',
]

# Noms usuels -> libellé employé par le thésaurus ANSM
SUBSTANCE_ALIASES = {
    "aspirine": "acide acetylsalicylique",
    "vitamine k": "phytomenadione",
}

# Niveaux de gravité (rang plus élevé = plus grave)
SEVERITY_RANK = {"low": 1, "moderate": 2, "high": 3, "critical": 4}

# Cache mémoire substance -> classes (rempli au premier appel, voir FacadeService)
_CLASS_CACHE = {"by_member": None, "classes": None}


def _severity_rank(value) -> int:
    return SEVERITY_RANK.get(str(value or "").lower(), 0)


def _norm(text: str) -> str:
    return normalize(text or "").lower().strip()


def _clean_substance_name(substance: str) -> str:
    """Variante courte d'un nom de substance (sels retirés si le résultat reste non vide)."""
    text = substance.lower()
    cleaned = text
    for salt in COMMON_SALTS:
        cleaned = re.sub(salt, '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned or text.strip()


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

    # --- CLASSES ANSM (table générée depuis le thésaurus) ---

    def _load_class_cache(self):
        """Charge classes_ansm en mémoire (≈1100 lignes) : membre_norm -> {classes}."""
        if _CLASS_CACHE["by_member"] is None:
            rows = db.session.execute(
                db.select(ClasseMembreModel.classe_norm, ClasseMembreModel.membre_norm)
            ).all()
            by_member, classes = {}, set()
            for classe, membre in rows:
                by_member.setdefault(membre, set()).add(classe)
                classes.add(classe)
            _CLASS_CACHE["by_member"], _CLASS_CACHE["classes"] = by_member, classes
        return _CLASS_CACHE["by_member"]

    def reload_class_cache(self):
        """À appeler après un ré-import de classes_ansm."""
        _CLASS_CACHE["by_member"] = _CLASS_CACHE["classes"] = None

    def get_classes_for_substance(self, substance: str) -> set:
        """Classes ANSM d'une substance. Match exact, ou sur le 1er mot pour les membres
        composés (ex: 'dexketoprofene' -> 'dexketoprofene trometamol')."""
        sub = _norm(SUBSTANCE_ALIASES.get(_norm(substance), substance))
        if not sub:
            return set()
        by_member = self._load_class_cache()
        found = set(by_member.get(sub, ()))
        for membre, classes in by_member.items():
            if membre.startswith(sub + " "):
                found |= classes
        return found

    def expand_substance_terms(self, substance: str) -> list:
        """La substance elle-même (+ variante sans sel) + ses classes ANSM."""
        sub = _norm(SUBSTANCE_ALIASES.get(_norm(substance), substance))
        terms = {sub, _norm(_clean_substance_name(sub))}
        terms |= self.get_classes_for_substance(sub)
        terms.discard("")
        return list(terms)

    # --- INTERACTIONS ---

    def get_interactions(self, ingredient_a: str, ingredient_b: str) -> list:
        """
        Toutes les interactions connues entre deux termes (substances OU classes),
        en MATCH EXACT sur le nom normalisé (plus de ilike '%x%' : 'fer' ne matche
        plus 'deferasirox'). Curated (InteractionModel) d'abord, puis thésaurus ANSM.
        """
        norm_a, norm_b = _norm(ingredient_a), _norm(ingredient_b)
        if not norm_a or not norm_b:
            return []
        if norm_a == norm_b:
            return []

        results = list(db.session.execute(
            db.select(InteractionModel).where(
                or_(
                    and_(func.lower(InteractionModel.ingredient_a) == norm_a,
                         func.lower(InteractionModel.ingredient_b) == norm_b),
                    and_(func.lower(InteractionModel.ingredient_a) == norm_b,
                         func.lower(InteractionModel.ingredient_b) == norm_a),
                )
            )
        ).scalars().all())

        results += db.session.execute(
            db.select(InteractionAnsmModel).where(
                or_(
                    and_(InteractionAnsmModel.substance_a_norm == norm_a,
                         InteractionAnsmModel.substance_b_norm == norm_b),
                    and_(InteractionAnsmModel.substance_a_norm == norm_b,
                         InteractionAnsmModel.substance_b_norm == norm_a),
                )
            )
        ).scalars().all()
        return results

    def get_interaction(self, ingredient_a: str, ingredient_b: str):
        """Compat : la plus grave des interactions entre deux termes (ou None)."""
        found = self.get_interactions(ingredient_a, ingredient_b)
        return max(found, key=lambda i: _severity_rank(i.severity)) if found else None

    @staticmethod
    def _interaction_to_dict(interaction, sub_a, sub_b, via=None) -> dict:
        return {
            "severity": interaction.severity,
            "description": interaction.description,
            "mechanism": getattr(interaction, "mechanism", None),
            "conduct": getattr(interaction, "conduct", None),
            "ansm_codes": getattr(interaction, "ansm_codes", None),
            "substance_a": sub_a, "substance_b": sub_b,
            "via": via,  # ex: "classe : anti-inflammatoires non steroidiens"
        }

    def check_drug_interaction(self, term_a: str, term_b: str) -> dict:
        """
        Point d'entrée UNIQUE pour le chatbot : deux noms libres (marque, DCI,
        produit du stock...) -> verdict complet.

        Retourne la plus grave des interactions trouvées (clés historiques
        has_interaction / severity / description / substance_a / substance_b
        conservées) + 'interactions' : la liste complète triée par gravité.
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

        found, seen = [], set()

        def add(interaction, sa, sb, via=None):
            # Le thésaurus liste souvent A->B ET B->A : on dédoublonne les paires symétriques.
            key = (frozenset((_norm(interaction.ingredient_a if hasattr(interaction, "ingredient_a") else interaction.substance_a_norm),
                              _norm(interaction.ingredient_b if hasattr(interaction, "ingredient_b") else interaction.substance_b_norm))),
                   str(interaction.severity).lower(), via)
            if key in seen:
                return
            seen.add(key)
            found.append(self._interaction_to_dict(interaction, sa, sb, via))

        for sa in subs_a:
            clean_sa = _norm(SUBSTANCE_ALIASES.get(_norm(sa), sa))
            for sb in subs_b:
                clean_sb = _norm(SUBSTANCE_ALIASES.get(_norm(sb), sb))

                # A. Même substance des deux côtés -> risque de surdosage
                if clean_sa == clean_sb and clean_sa != "n/a":
                    key = ("overdose", clean_sa)
                    if key not in seen:
                        seen.add(key)
                        found.append({
                            "severity": "Critical",
                            "description": f"Risque de surdosage : les deux traitements contiennent du {clean_sa.title()}.",
                            "mechanism": None, "conduct": None, "ansm_codes": None,
                            "substance_a": clean_sa, "substance_b": clean_sb, "via": "surdosage",
                        })
                    continue

                terms_a = self.expand_substance_terms(sa)
                terms_b = self.expand_substance_terms(sb)

                # B. Recherche croisée substance/classe (curatée + thésaurus ANSM)
                for ta in terms_a:
                    for tb in terms_b:
                        via = None
                        if ta != clean_sa or tb != clean_sb:
                            via = "classe : " + " / ".join(
                                t for t, base in ((ta, clean_sa), (tb, clean_sb)) if t != base
                            )
                        for it in self.get_interactions(ta, tb):
                            add(it, clean_sa, clean_sb, via)

                # C. Interactions intra-classe ("AUTRES <classe>" dans le thésaurus)
                for classe in self.get_classes_for_substance(sa) & self.get_classes_for_substance(sb):
                    for it in self.get_interactions(classe, "autres " + classe):
                        add(it, clean_sa, clean_sb, f"intra-classe : {classe}")

        if not found:
            return {
                "has_interaction": False,
                "term_a": term_a, "term_b": term_b,
                "substances_a": subs_a, "substances_b": subs_b,
                "message": "Aucune interaction trouvée dans les bases disponibles."
            }

        found.sort(key=lambda d: _severity_rank(d["severity"]), reverse=True)
        top = found[0]
        return {
            "has_interaction": True,
            "severity": top["severity"],
            "description": top["description"],
            "mechanism": top["mechanism"],
            "conduct": top["conduct"],
            "ansm_codes": top["ansm_codes"],
            "via": top["via"],
            "substance_a": top["substance_a"], "substance_b": top["substance_b"],
            "term_a": term_a, "term_b": term_b,
            "interactions": found,
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