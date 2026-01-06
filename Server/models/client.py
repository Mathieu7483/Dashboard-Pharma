from database.data_manager import db
from models.basemodel import PersonModel

class ClientModel(PersonModel): 
    """
    Model representing a client, inheriting common human attributes
    from PersonModel (names, email, address, timestamps, ID).
    """
    __tablename__ = 'clients'
    email = db.Column(db.String(120), unique=True, nullable=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)


    def __init__(self, first_name, last_name, email, address, user_id):
        super().__init__()
        
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.address = address
        self.user_id = user_id



    def __repr__(self):
        return f'<ClientModel name={self.last_name} {self.first_name}>'