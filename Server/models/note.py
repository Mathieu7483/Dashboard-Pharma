from database.data_manager import db
from models.basemodel import TimeStampedModel
from sqlalchemy.orm import relationship 

class Note(TimeStampedModel):
    __tablename__ = 'notes'
    
    text = db.Column(db.Text, nullable=False)
    
    # Relations
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    user = relationship('UserModel', back_populates='notes')

    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Note {self.id} by User {self.user_id}>"
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    def update_text(self, new_text):
        self.text = new_text
        db.session.commit()
    
    def is_owned_by(self, user_id):
        return self.user_id == user_id
    
notes = db.relationship('NoteModel', back_populates='user', cascade="all, delete-orphan")