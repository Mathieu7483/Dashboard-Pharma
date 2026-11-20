"""Importe utils/classes_ansm.csv (généré par parse_classes.py) dans classes_ansm. Idempotent.

Usage (depuis le dossier Server) : python -m utils.import_classes_ansm [chemin_csv]
"""
import csv
import sys
from pathlib import Path


def run(csv_path: Path):
    from app import create_app  # adapter si votre factory s'appelle autrement
    from database.data_manager import db
    from models.classe_ansm import ClasseMembreModel

    app = create_app()
    with app.app_context():
        db.create_all()
        db.session.query(ClasseMembreModel).delete()
        with open(csv_path, encoding="utf-8", newline="") as f:
            rows = {(r["classe_norm"], r["membre_norm"]) for r in csv.DictReader(f)}
        db.session.add_all(ClasseMembreModel(classe_norm=c, membre_norm=m) for c, m in sorted(rows))
        db.session.commit()
        print(f"{len(rows)} liens classe/membre importés.")


if __name__ == "__main__":
    run(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("classes_ansm.csv"))
