"""Development entry point.

    python run.py          -> create tables, seed (dev only by default), start the dev server
    python run.py --seed   -> create tables, full demo seed (fake sales included), then exit
    python run.py --create-admin
                           -> create tables and ONLY the first admin account, then exit
                              (the production bootstrap; reads ADMIN_* variables)

In production the app is served by gunicorn through wsgi.py (see the Dockerfile).
"""
import os
import sys

from app import create_app
from database.data_manager import db
from utils.seeder import seed_all_initial_data, _seed_admin

app = create_app()


def init_database(seed):
    with app.app_context():
        db.create_all()
        if seed:
            print("\n--- 🌱 Seeding Process ---")
            try:
                seed_all_initial_data()
            except Exception as e:
                print(f"❌ Seeding failed: {e}")


if __name__ == "__main__":
    is_production = os.environ.get('APP_ENV', 'development').lower() == 'production'

    if '--create-admin' in sys.argv:
        with app.app_context():
            db.create_all()
            sys.exit(0 if _seed_admin() else 1)

    if '--seed' in sys.argv:
        init_database(seed=True)
        sys.exit(0)

    # Seeding on every start is a development convenience only.
    seed_on_startup = os.environ.get('SEED_ON_STARTUP', 'false' if is_production else 'true')
    init_database(seed=seed_on_startup.strip().lower() in ('1', 'true', 'yes', 'on'))

    if is_production:
        sys.exit("Refusing to start the Flask development server with APP_ENV=production. "
                 "Use gunicorn (see Dockerfile).")

    host = os.environ.get('HOST', '127.0.0.1')
    print("\n--- 🚀 Starting Pharma Server (development) ---")
    print(f"Documentation: http://{host}:5000/docs")
    app.run(host=host, port=5000, debug=app.config.get('DEBUG', False), use_reloader=False)
