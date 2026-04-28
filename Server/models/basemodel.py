from database.data_manager import db
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
import uuid

# --- 1. CORE FUNCTIONALITY & TRANSACTION MANAGEMENT ---
class BaseModel(db.Model):
    """
    Modèle de base abstrait pour gérer les clés primaires (UUID) et
    les opérations CRUD de base avec gestion des transactions (rollback).
    """
    __abstract__ = True

    # primary key UUID
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id}>"

    def save_to_db(self):
        """
        Ajoute et valide l'instance dans la base de données.
        Gère les IntegrityError (conflits d'unicité, clés étrangères) et les erreurs générales.
        """
        try:
            db.session.add(self)
            db.session.commit()
            return True
        except IntegrityError as e:
            # constraint violation (e.g., unique constraint, foreign key constraint)
            db.session.rollback()
            # inform about the specific integrity error
            print(f"Error saving {self}: Integrity constraint violated. {e}") 
            return False
        except Exception as e:
            # other unexpected errors
            db.session.rollback()
            print(f"Unexpected error saving {self}: {e}")
            return False

    def delete_from_db(self):
        """
        Supprime l'instance de la base de données de manière sécurisée.
        """
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error deleting {self}: {e}")
            return False

# --- 2. TIMESTAMP FUNCTIONALITY ---
class TimeStampedModel(BaseModel):
    """
    Modèle abstrait ajoutant les champs de date de création et de mise à jour.
    """
    __abstract__ = True
    
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

# --- 3. COMMON PERSON/ENTITY FIELDS ---
class PersonModel(TimeStampedModel):
    """
    Modèle abstrait regroupant les attributs communs aux entités 'Personne' 
    (User, Client, Doctor) et incluant les horodatages.
    """
    __abstract__ = True

    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True) 
    address = db.Column(db.String(255), nullable=True)