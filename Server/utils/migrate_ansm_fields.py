from sqlalchemy import inspect, text
from database.data_manager import db


def ensure_ansm_columns():
    """
    Ajoute les colonnes cis / cip13 à la table products si elles n'existent pas.
    Idempotent : safe à appeler à chaque démarrage.
    """
    inspector = inspect(db.engine)
    existing_cols = [c['name'] for c in inspector.get_columns('products')]

    with db.engine.connect() as conn:
        if 'cis' not in existing_cols:
            conn.execute(text('ALTER TABLE products ADD COLUMN cis VARCHAR(8)'))
            print("✅ Colonne 'cis' ajoutée à products.")
        if 'cip13' not in existing_cols:
            conn.execute(text('ALTER TABLE products ADD COLUMN cip13 VARCHAR(13)'))
            print("✅ Colonne 'cip13' ajoutée à products.")
        conn.commit()