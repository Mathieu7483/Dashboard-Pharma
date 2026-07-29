"""
Charge le CSV genere par parse_ansm_thesaurus.py dans la table interactions_ansm.

Usage (depuis le dossier Server/) :
    python -m utils.import_interactions_ansm utils/ansm_interactions_precise.csv
"""
import sys
import csv
from database.data_manager import db
from models.interaction_ansm import InteractionAnsmModel


def import_csv(csv_path: str):
    InteractionAnsmModel.query.delete()  # rechargement complet, idempotent
    count = 0
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            db.session.add(InteractionAnsmModel(
                substance_a=row['substance_a'],
                substance_b=row['substance_b'],
                substance_a_norm=row['substance_a_norm'],
                substance_b_norm=row['substance_b_norm'],
                severity=row['severity'],
                ansm_codes=row['ansm_codes'],
                mechanism=row['mechanism'],
                conduct=row['conduct'],
                source_page=int(row['source_page']) if row['source_page'] else None,
            ))
            count += 1
            if count % 500 == 0:
                db.session.flush()
    db.session.commit()
    print(f"✅ {count} interactions ANSM (thésaurus) importées.")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python -m utils.import_interactions_ansm <chemin_csv>")
        sys.exit(1)
    from app import create_app
    app = create_app()
    with app.app_context():
        import_csv(sys.argv[1])