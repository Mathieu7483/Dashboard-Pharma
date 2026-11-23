"""Production entry point: gunicorn --preload -b 0.0.0.0:5000 wsgi:app

The app is built once in the gunicorn master (--preload) so that the tables are
created a single time, before the workers are forked.
"""
from app import create_app
from database.data_manager import db

app = create_app()

with app.app_context():
    db.create_all()
