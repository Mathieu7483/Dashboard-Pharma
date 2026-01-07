from database.data_manager import db
from models.basemodel import BaseModel
from sqlalchemy.orm import relationship 
from models.sale import SaleModel

class ProductModel(BaseModel):
    """
    Model for pharmaceutical products, inheriting CRUD methods from BaseModel.
    Includes fields necessary for inventory management, dosage, and regulatory compliance.
    """
    
    # --------------------------------------------------------
    # Table Definition
    # --------------------------------------------------------
    __tablename__ = 'products'

    # --------------------------------------------------------
    # Core Attributes (Columns) - ENHANCED FOR PHARMACY
    # --------------------------------------------------------
    
    name = db.Column(db.String(120), unique=True, nullable=False)
    
    # New Field 1: Clinical identification
    active_ingredient = db.Column(db.String(120), nullable=True, default='N/A')
    
    # New Field 2: Dosage/Format description
    dosage = db.Column(db.String(80), nullable=True, default='N/A')
    
    stock = db.Column(db.Integer, default=0, nullable=False)
    price = db.Column(db.Float(precision=2), nullable=False)
    
    # New Field 3: Regulatory requirement
    is_prescription_only = db.Column(db.Boolean, default=False)
    
    # --------------------------------------------------------
    # Relationships (Foreign Keys)
    # --------------------------------------------------------
    
    # Foreign key to the user who created the product (Owner)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    # Defines the relationship with the UserModel
    user = relationship("UserModel") 

    # Relationship with sales (many-to-many relationship)
    sales_entries = relationship("SaleItemModel", back_populates='product', lazy=True, cascade="all, delete-orphan")


    def __init__(self, name, active_ingredient, dosage, stock, price, is_prescription_only, user_id):
        """
        Constructor for the ProductModel with all new fields.
        """
        self.name = name
        self.active_ingredient = active_ingredient
        self.dosage = dosage
        self.stock = stock
        self.price = price
        self.is_prescription_only = is_prescription_only
        self.user_id = user_id
    
    def __repr__(self):
        """
        Provides a useful representation for debugging.
        """
        return f'<ProductModel name={self.name} dosage={self.dosage} stock={self.stock}>'
    
    def to_dict(self):
        """Convert product instance to dictionary"""
        return {
            'id': str(self.id),
            'name': self.name,
            'active_ingredient': self.active_ingredient,
            'dosage': self.dosage,
            'stock': self.stock,
            'price': float(self.price),
            'is_prescription_only': self.is_prescription_only,
            'user_id': str(self.user_id) if self.user_id else None
        }