from database.data_manager import db
from models.basemodel import PersonModel

class ClientModel(PersonModel): 
    """
    Model representing a client, inheriting common human attributes
    from PersonModel (names, email, address, timestamps, ID).
    """
    __tablename__ = 'clients'
    
    # Declarative columns for SQLAlchemy
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)

    def __init__(self, first_name, last_name, email, address, phone, user_id):
        # We initialize the parent (PersonModel handles id and timestamps)
        super().__init__()
        
        # Explicit assignment
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.address = address
        self.phone = phone
        self.user_id = user_id

    def __repr__(self):
        return f'<ClientModel name={self.last_name} {self.first_name}>'