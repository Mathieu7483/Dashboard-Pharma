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

DEFAULT_SQLITE_URI = f'sqlite:///{os.path.join(DATABASE_FOLDER, "database.sqlite")}'


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


class Config:
    """Base settings shared by every environment. Secrets are read from the
    environment only: no secret value is ever stored in the source code."""

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', DEFAULT_SQLITE_URI)

    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    # Single source of truth for the access token lifetime (default: 15 min).
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.environ.get('JWT_EXPIRES_MINUTES', '15'))
    )

    DEBUG = False
    # Required by Flask-RESTX to hand JWT errors over to Flask-JWT-Extended's handlers
    # (401 missing/expired token, 422 malformed token). Without it, and with DEBUG off,
    # every unauthenticated call would answer 500 instead of 401.
    PROPAGATE_EXCEPTIONS = True
    # Public self-registration is OFF unless explicitly enabled.
    ALLOW_PUBLIC_REGISTRATION = _env_bool('ALLOW_PUBLIC_REGISTRATION', False)
    # Comma-separated list of allowed browser origins for CORS (empty = same origin only).
    CORS_ORIGINS = [o.strip() for o in os.environ.get('CORS_ORIGINS', '').split(',') if o.strip()]


class DevelopmentConfig(Config):
    DEBUG = _env_bool('FLASK_DEBUG', False)

    # Random per-process keys: convenient for local work, never reused in production.
    # Tokens simply become invalid when the dev server restarts.
    SECRET_KEY = Config.SECRET_KEY or secrets.token_hex(32)
    JWT_SECRET_KEY = Config.JWT_SECRET_KEY or secrets.token_hex(32)
    CORS_ORIGINS = Config.CORS_ORIGINS or [
        'http://127.0.0.1:5000', 'http://localhost:5000',
        'http://127.0.0.1:5500', 'http://localhost:5500',  # VS Code Live Server
    ]


class ProductionConfig(Config):
    """No fallback: the application refuses to start without real secrets."""

    @classmethod
    def validate(cls):
        missing = [k for k in ('SECRET_KEY', 'JWT_SECRET_KEY') if not getattr(cls, k)]
        if missing:
            raise RuntimeError(
                "Missing required environment variable(s): " + ", ".join(missing)
                + ". Generate them with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        for key in ('SECRET_KEY', 'JWT_SECRET_KEY'):
            if len(getattr(cls, key)) < 32:
                raise RuntimeError(f"{key} must be at least 32 characters long.")


class TestingConfig(Config):
    # Separate, in-memory SQLite DB for fast, clean tests
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-only-secret-key-not-for-production-32b'
    JWT_SECRET_KEY = 'test-only-jwt-secret-key-not-for-production'
    JWT_ACCESS_TOKEN_EXPIRES = False


def get_config():
    """Pick the config from APP_ENV (development by default, production in Docker)."""
    env = os.environ.get('APP_ENV', 'development').lower()
    if env == 'production':
        return ProductionConfig
    if env == 'testing':
        return TestingConfig
    return DevelopmentConfig
