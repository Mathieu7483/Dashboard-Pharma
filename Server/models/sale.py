from database.data_manager import db
from sqlalchemy.sql import func
from models.basemodel import BaseModel
from sqlalchemy.orm import relationship
import uuid

# ==========================================================
# 1. SaleItemModel (The Line Item)
# ==========================================================

class SaleItemModel(db.Model):
    __tablename__ = 'sale_items'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign Keys
    sale_id = db.Column(db.String(36), db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)
    
    quantity = db.Column(db.Integer, nullable=False)
    price_at_sale = db.Column(db.Float(precision=2), nullable=False) # Price per unit at the time of sale
    
    # Relations
    sale = db.relationship('SaleModel', back_populates='items')
    product = db.relationship('ProductModel')
    
    def __init__(self, sale_id, product_id, quantity, price_at_sale):
        self.sale_id = sale_id
        self.product_id = product_id
        self.quantity = quantity
        self.price_at_sale = price_at_sale

    def __repr__(self):
        return f'<SaleItem SaleID={self.sale_id} ProductID={self.product_id} Qty={self.quantity}>'

# ==========================================================
# 2. SaleModel (The Global Transaction)
# ==========================================================

class SaleModel(BaseModel):
    """
    Represents the overarching sale transaction (the 'receipt' or 'ticket').
    It stores global details like date, total, user, and client.
    """
    __tablename__ = 'sales'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # --- Transaction Details ---
    # The sum of all SaleItems linked to this transaction.
    total_amount = db.Column(db.Float(precision=2), nullable=False, default=0.00)
    
    # Timestamps
    sale_date = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    
    # Pharmacy-specific flag
    prescription_provided = db.Column(db.Boolean, default=False, nullable=True)

    # --- Relationships (Foreign Keys) ---
    # Doctor who issued the prescription (Optional)
    doctor_id = db.Column(db.String(36), db.ForeignKey('doctors.id'), nullable=True)
    
    # Employee who made the sale (Mandatory)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    # Note: Assumes a relationship defined on the UserModel class (e.g., 'sales')
    
    # Client associated with the sale (Optional, for prescription tracking)
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=True)
    # Note: Assumes a relationship defined on the ClientModel class (e.g., 'sales')
    
    # CRITICAL RELATIONSHIP: Links the transaction to all its constituent line items.
    items = relationship("SaleItemModel", back_populates="sale", lazy=True, cascade="all, delete-orphan")

    def __init__(self, user_id, client_id=None, doctor_id=None, prescription_provided=False, total_amount=0.0, sale_date=None):
        """
        Initializes a new sale. Added sale_date for historical data support.
        """
        self.user_id = user_id
        self.client_id = client_id
        self.doctor_id = doctor_id
        self.prescription_provided = prescription_provided
        self.total_amount = total_amount
        if sale_date:
            self.sale_date = sale_date

    def __repr__(self):
        return f'<SaleModel ID={self.id} Total={self.final_total} Date={self.sale_date}>'

    # --- Utility Methods ---
    
    def calculate_total(self):
        """Calculates the total revenue from all linked SaleItems."""
        total = sum(item.quantity * item.price_at_sale for item in self.items)
        self.final_total = total
        return total
