from database.data_manager import db, bcrypt
from sqlalchemy import func, or_, desc
from models.user import UserModel
from models.product import ProductModel
from models.sale import SaleModel, SaleItemModel
from models.client import ClientModel
from models.doctor import DoctorModel
from models.calendar import CalendarEvent
from models.interaction import InteractionModel
from models.ticket import Ticket
from datetime import datetime, UTC

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

    def create_product(self, name, active_ingredient, dosage, stock, price, is_prescription_only, user_id):
        try:
            new_product = ProductModel(
                name=name, active_ingredient=active_ingredient, dosage=dosage, 
                stock=stock, price=price, is_prescription_only=is_prescription_only, user_id=user_id
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
                sale_date=created_at  # <--- Ajout crucial
            )
            db.session.add(new_sale)
            db.session.flush()  # Get new_sale.id before committing

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
        """
        Calculate total sales revenue grouped by date.
        """

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
        """fetch products with low stock (<=10 units)."""
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
                func.count(SaleModel.id).label('sale_count') # <--- AJOUTE CETTE LIGNE
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
    
    def create_client(self, first_name, last_name, email,phone, address, user_id):
        new_client = ClientModel(first_name=first_name, last_name=last_name, email=email,phone=phone, address=address, user_id=user_id)
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


    # --- INTERACTION METHODS ---
    def get_interaction(self, ingredient_a, ingredient_b):
        """
        Queries the database for an interaction between two active ingredients.
        Standardized to SQLAlchemy 2.0 syntax.
        """
        stmt = (
            db.select(InteractionModel)
            .where(
                or_(
                    (InteractionModel.ingredient_a.ilike(f"%{ingredient_a}%")) & 
                    (InteractionModel.ingredient_b.ilike(f"%{ingredient_b}%")),
                    (InteractionModel.ingredient_a.ilike(f"%{ingredient_b}%")) & 
                    (InteractionModel.ingredient_b.ilike(f"%{ingredient_a}%"))
                )
            )
        )
        # We use scalar_one_or_none() to get a single object or None
        return db.session.execute(stmt).scalar_one_or_none()

    
    # --- TICKET CRUD METHODS ---
    def get_all_tickets(self, user_id=None):
        """
        Fetch tickets. If user_id is provided, only fetch tickets for that user.
        If None, fetch all (for Admin).
        """
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
        """
        Generic update for tickets. Handles both User updates (subject/desc)
        and Admin updates (status/admin_note).
        """
        ticket = self.get_ticket_by_id(ticket_id)
        if ticket:
            for key, value in data.items():
                if hasattr(ticket, key):
                    setattr(ticket, key, value)
            try:
                db.session.commit()
                return ticket
            except Exception as e:
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
            except Exception as e:
                db.session.rollback()
                return False
        return False


# --- CALENDAR METHOD ---
    def get_events_by_date(self, date_str):
        """
        fetch events (RDV) for a specific date. This can be used to populate the calendar view.
        """
        from models.calendar import CalendarEvent
        
        stmt = (
            db.select(CalendarEvent)
            .filter(func.date(CalendarEvent.start_time) == date_str)
            .order_by(CalendarEvent.start_time)
        )
        return db.session.execute(stmt).scalars().all()