from typing import Optional, List, Dict
from models.user import UserModel
from models.product import ProductModel
from models.sale import SaleModel
from database.data_manager import db

class FacadeService:
    """
    Provides a simplified interface for business logic and basic CRUD access.
    """

    # --- Shared Read Methods (Internal use) ---

    def _get_entity(self, model_class, entity_id: int):
        """Generic method to retrieve an entity by ID."""
        return model_class.query.get(entity_id)

    def _get_all_entities(self, model_class):
        """Generic method to retrieve all entities."""
        return model_class.query.all()
    
    def _get_by_attribute(self, model_class, attribute_name: str, value: str):
        """Generic method to retrieve an entity by an attribute (e.g., name, email)."""
        return model_class.query.filter_by(**{attribute_name: value}).first()

    # ======================================================================
    # USER CRUD
    # ======================================================================

    def create_user(self, username: str, email: str, password: str, is_admin: bool = False) -> Optional[UserModel]:
        """Creates a new user, hashes the password, and saves it."""
        if UserModel.query.filter_by(username=username).first():
            return None # User already exists
        
        new_user = UserModel(username=username, email=email, is_admin=is_admin)
        new_user.set_password(password) # Uses UserModel's secured method
        new_user.save_to_db() # Uses method inherited from BaseModel
        return new_user

    def get_user_by_id(self, user_id: int) -> Optional[UserModel]:
        """Retrieves a user by their ID."""
        return self._get_entity(UserModel, user_id)

    def get_user_by_username(self, username: str) -> Optional[UserModel]:
        """Retrieves a user by their username."""
        return self._get_by_attribute(UserModel, 'username', username)

    def get_all_users(self) -> List[UserModel]:
        """Retrieves a list of all users."""
        return self._get_all_entities(UserModel)

    def update_user_profile(self, user_id: int, data: Dict) -> Optional[UserModel]:
        """Updates authorized fields by a user or an administrator."""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        # Update logic (applies data to the model)
        if 'email' in data:
            user.email = data['email']
        if 'is_admin' in data:
            user.is_admin = data['is_admin'] # Requires administrator check in the API layer

        user.save_to_db()
        return user

    def delete_user(self, user_id: int) -> bool:
        """Deletes a user."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        user.delete_from_db()
        return True

    # ======================================================================
    # PRODUCT CRUD
    # ======================================================================

    def create_product(self, name: str, stock: int, price: float, user_id: int) -> ProductModel:
        """Creates a new product."""
        new_product = ProductModel(name=name, stock=stock, price=price, user_id=user_id)
        new_product.save_to_db()
        return new_product

    def get_product_by_id(self, product_id: int) -> Optional[ProductModel]:
        """Retrieves a product by its ID."""
        return self._get_entity(ProductModel, product_id)

    def get_all_products(self) -> List[ProductModel]:
        """Retrieves all products."""
        return self._get_all_entities(ProductModel)
    
    def get_product_by_name(self, product_name: str) -> Optional[ProductModel]:
        """Retrieves a product by its exact name."""
        return self._get_by_attribute(ProductModel, 'name', product_name)

    def search_products_by_name(self, search_term: str) -> List[ProductModel]:
        """Searches for products whose name contains the specified term."""
        return ProductModel.query.filter(
            ProductModel.name.ilike(f'%{search_term}%')
        ).all()

    def update_product(self, product_id: int, data: Dict) -> Optional[ProductModel]:
        """Updates an existing product."""
        product = self.get_product_by_id(product_id)
        if not product:
            return None
        
        # Simple attribute update
        if 'name' in data: product.name = data['name']
        if 'stock' in data: product.stock = data['stock']
        if 'price' in data: product.price = data['price']
        
        product.save_to_db()
        return product

    def delete_product(self, product_id: int) -> bool:
        """Deletes a product."""
        product = self.get_product_by_id(product_id)
        if not product:
            return False
        product.delete_from_db()
        return True

    # ======================================================================
    # SALE CRUD
    # ======================================================================

    # Note: Sale CRUD methods are often more complex (purchase process)
    
    def create_sale(self, product_id: int, quantity: int, user_id: int) -> Optional[SaleModel]:
        """
        Records a sale (complex business logic: stock verification, recording, update).
        """
        product = self.get_product_by_id(product_id)
        
        # Business logic: Stock verification before sale
        if not product or product.stock < quantity:
            return None
            
        total_price = product.price * quantity
        
        # 1. Update product stock (Transaction)
        product.stock -= quantity
        product.save_to_db()
        
        # 2. Create sale record (Transaction)
        new_sale = SaleModel(
            product_id=product_id,
            quantity=quantity,
            total_price=total_price,
            user_id=user_id
        )
        new_sale.save_to_db()
        
        return new_sale

    def get_sale_by_id(self, sale_id: int) -> Optional[SaleModel]:
        """Retrieves a sale by its ID."""
        return self._get_entity(SaleModel, sale_id)

    def get_all_sales(self) -> List[SaleModel]:
        """Retrieves all sales."""
        return self._get_all_entities(SaleModel)
        
    def delete_sale(self, sale_id: int) -> bool:
        """Deletes a sale record (often restricted to admins)."""
        sale = self.get_sale_by_id(sale_id)
        if not sale:
            return False
            
        # Business logic: Restore stock upon sale cancellation
        product = self.get_product_by_id(sale.product_id)
        if product:
             product.stock += sale.quantity
             product.save_to_db()
        
        sale.delete_from_db()
        return True