from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Config:
    SECRET_KEY = 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///pharma_dashboard.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = 'your_jwt_secret_key'
    JWT_ACCESS_TOKEN_EXPIRES = 3600

class DevelopmentConfig(Config):
      DEBUG = True