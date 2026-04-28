from database.data_manager import db 
from datetime import datetime
import uuid

class CalendarEvent(db.Model):
    __tablename__ = 'calendar_events'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = db.Column(db.String(20), nullable=False)  # 'rdv' ou 'garde'
    title = db.Column(db.String(200), nullable=True)
    start_date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    end_date = db.Column(db.String(10), nullable=True)
    start_time = db.Column(db.String(5), nullable=False)   # HH:MM
    end_time = db.Column(db.String(5), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    # Foreign Keys
    assigned_user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assigned_user = db.relationship('UserModel', foreign_keys=[assigned_user_id], backref='assigned_events', lazy=True)
    creator = db.relationship('UserModel', foreign_keys=[created_by], backref='created_events', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'startDate': self.start_date,
            'endDate': self.end_date or self.start_date,
            'startTime': self.start_time,
            'endTime': self.end_time,
            'notes': self.notes,
            'assignedUserId': self.assigned_user_id,
            'assignedUserName': self.assigned_user.username if self.assigned_user else None,
            'createdBy': self.created_by,
            'creatorName': self.creator.username if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<CalendarEvent {self.id} | {self.type} | {self.start_date}>'