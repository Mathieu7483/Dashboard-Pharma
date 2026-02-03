from database.data_manager import db
from models.basemodel import BaseModel
from sqlalchemy.orm import relationship 
from models.user import UserModel
from utils.decorator import admin_required
from datetime import datetime

class Ticket(db.Model):
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='medium') # low, medium, high
    status = db.Column(db.String(20), default='open') # open, in_progress, closed
    
    # Relations
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Admin can add notes to the ticket
    admin_note = db.Column(db.Text, nullable=True)