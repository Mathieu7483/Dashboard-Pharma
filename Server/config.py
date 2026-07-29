import os
import secrets
from datetime import timedelta

# --- 1. Path Configuration ---
# Define the base directory (Server/)
basedir = os.path.abspath(os.path.dirname(__file__))
DATABASE_FOLDER = os.path.join(basedir, 'database')

# Ensure the database directory exists
if not os.path.exists(DATABASE_FOLDER):
    os.makedirs(DATABASE_FOLDER)


class Config:
    # Global security and JWT settings (Min 32 bytes for SHA256)
    SECRET_KEY = os.environ.get(
        'SECRET_KEY', 
        'pharma_dashboard_super_secret_key_2026_dev_mode_32bytes'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get(
        'JWT_SECRET_KEY', 
        'pharma_dashboard_jwt_access_secret_key_secure_2026'
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    # ... (other JWT settings)


class DevelopmentConfig(Config):
    DEBUG = True

    # CRITICAL: Use absolute path inside the 'database' folder
    SQLALCHEMY_DATABASE_URI = (
        f'sqlite:///{os.path.join(DATABASE_FOLDER, "database.sqlite")}'
    )


class TestingConfig(Config):
    # CRITICAL: Use a separate, in-memory SQLite DB for fast, clean tests
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_ACCESS_TOKEN_EXPIRES = False