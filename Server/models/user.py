from database.data_manager import bcrypt, db
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
