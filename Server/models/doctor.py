from database.data_manager import db
from models.basemodel import PersonModel


class DoctorModel(PersonModel): 
    """
    Model representing a doctor. Inherits common person fields (names, email, 
    address, timestamps, ID) from PersonModel.
    """
    __tablename__ = 'doctors'

    email = db.Column(db.String(120), unique=True, nullable=True) 
    
    specialty = db.Column(db.String(80), nullable=True)
    phone = db.Column(db.String(20), nullable=True)

    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<DoctorModel name={self.last_name} specialty={self.specialty}>'