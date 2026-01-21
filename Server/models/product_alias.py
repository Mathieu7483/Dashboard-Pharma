"""
Server/models/product_alias.py
Maps commercial names to active ingredients for chatbot flexibility
"""

from database.data_manager import db

class ProductAliasModel(db.Model):
    """
    Stores product name aliases (commercial names → active ingredients).
    
    Examples:
    - alias: "Aspirine" → active_ingredient: "Acide Acétylsalicylique"
    - alias: "Doliprane" → active_ingredient: "Paracétamol"
    - alias: "Advil" → active_ingredient: "Ibuprofène"
    
    This allows the chatbot to understand user-friendly names without hardcoding.
    """
    __tablename__ = 'product_aliases'

    id = db.Column(db.Integer, primary_key=True)
    
    # The commercial/common name users might type
    alias = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # The active ingredient to match in InteractionModel
    active_ingredient = db.Column(db.String(100), nullable=False)
    
    # Optional: category for filtering
    category = db.Column(db.String(50), nullable=True)  # e.g., "analgesic", "antibiotic"

    def __repr__(self):
        return f"<ProductAlias '{self.alias}' → {self.active_ingredient}>"
    
    @classmethod
    def get_active_ingredient(cls, user_input: str):
        """
        Resolve a user input to its active ingredient.
        
        Args:
            user_input: User's product name (case-insensitive)
            
        Returns:
            active_ingredient string or None
        """
        result = db.session.execute(
            db.select(cls).where(cls.alias.ilike(user_input))
        ).scalar_one_or_none()
        
        return result.active_ingredient if result else None