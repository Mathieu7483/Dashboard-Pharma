from database.data_manager import bcrypt, db
<<<<<<< HEAD
from models.basemodel import PersonModel
import uuid


class UserModel(PersonModel):
    __tablename__ = "users"

    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


    def set_password(self, password):
        """Hashe le mot de passe avant de le stocker."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        
    def check_password(self, password):
        """Vérifie le mot de passe fourni contre le hash stocké."""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    @classmethod
    def find_by_username(cls, username):
        """Trouve un utilisateur par nom d'utilisateur."""
        return cls.query.filter_by(username=username).first()

    def __init__(self, username, email, password, first_name=None, last_name=None, address=None, is_admin=False):
        """Initialise le UserModel, prenant désormais les noms."""
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.address = address
        self.is_admin = is_admin
        self.set_password(password)

    def __repr__(self):
        return f'<UserModel ID={self.id} Username={self.username}>'
=======
from models.basemodel import BaseModel


class UserModel(BaseModel):
  __tablename__ = "users"
  username = db.Column(db.String(80), unique=True, nullable=False)
  password_hash = db.Column(db.String(128), nullable=False)

  email = db.Column(db.String(120), unique=True, nullable=False)
  is_admin = db.Column(db.Boolean, default=False)

  def set_password(self, password):
      self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
  def check_password(self, password):
      return bcrypt.check_password_hash(self.password_hash, password)
  
  @classmethod
  def find_by_username(cls, username):
      return cls.query.filter_by(username=username).first()
>>>>>>> main
