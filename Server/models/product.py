from database.data_manager import db
from models.basemodel import BaseModel
from sqlalchemy.orm import relationship
from models.sale import SaleModel


class ProductModel(BaseModel):
    """
    Model for pharmaceutical products, inheriting CRUD methods from BaseModel.
    Includes fields necessary for inventory management, dosage, and regulatory compliance.
    """

    __tablename__ = 'products'

    name = db.Column(db.String(120), unique=True, nullable=False)
    active_ingredient = db.Column(db.String(120), nullable=True, default='N/A')
    dosage = db.Column(db.String(80), nullable=True, default='N/A')
    stock = db.Column(db.Integer, default=0, nullable=False)
    price = db.Column(db.Float(precision=2), nullable=False)
    is_prescription_only = db.Column(db.Boolean, default=False)

    # Lien optionnel vers le référentiel ANSM
    cis = db.Column(db.String(8), db.ForeignKey('specialites.cis'), nullable=True)
    cip13 = db.Column(db.String(13), nullable=True)  # code-barres exact de la boîte réellement en stock

    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)

    user = relationship("UserModel")
    sales_entries = relationship("SaleItemModel", back_populates='product', lazy=True, cascade="all, delete-orphan")
    specialite = relationship("SpecialiteModel")

    def __init__(self, name, active_ingredient, dosage, stock, price, is_prescription_only, user_id,
                 cis=None, cip13=None):
        self.name = name
        self.active_ingredient = active_ingredient
        self.dosage = dosage
        self.stock = stock
        self.price = price
        self.is_prescription_only = is_prescription_only
        self.user_id = user_id
        self.cis = cis
        self.cip13 = cip13

    def __repr__(self):
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
            'user_id': str(self.user_id) if self.user_id else None,
            'cis': self.cis,
            'cip13': self.cip13,
        }