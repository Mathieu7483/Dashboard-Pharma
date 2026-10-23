import csv
import os
from datetime import datetime, UTC
from database.data_manager import db
from models.specialite import SpecialiteModel
from models.composition import CompositionModel
from models.cip import CipModel
from utils.text_norm import normalize

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = {
    "CIS": os.path.join(BASE_DIR, "CIS.txt"),
    "COMPO": os.path.join(BASE_DIR, "COMPO.txt"),
    "CIS_CIP": os.path.join(BASE_DIR, "CIS_CIP.txt"), # Fichier des présentations / CIP
}


def _read_local_file(filepath: str) -> list:
    """Lit un fichier texte local encodé en ISO-8859-1."""
    if not os.path.exists(filepath):
        alt_path = os.path.join(BASE_DIR, "utils", os.path.basename(filepath))
        if os.path.exists(alt_path):
            filepath = alt_path
        else:
            raise FileNotFoundError(f"❌ Fichier introuvable : {filepath}")

    print(f"📖 Lecture du fichier : {filepath}")
    with open(filepath, "r", encoding="iso-8859-1") as f:
        reader = csv.reader(f, delimiter="\t")
        return list(reader)


def sync_specialites():
    """Upsert des spécialités à partir de CIS.txt."""
    rows = _read_local_file(SOURCES["CIS"])
    seen_cis = set()
    created, updated = 0, 0

    for row in rows:
        if len(row) < 7:
            continue
        cis = row[0].strip()
        if not cis:
            continue
        seen_cis.add(cis)

        spe = db.session.get(SpecialiteModel, cis)
        if not spe:
            spe = SpecialiteModel(cis=cis)
            db.session.add(spe)
            created += 1
        else:
            updated += 1

        spe.denomination = row[1].strip()
        spe.forme_pharmaceutique = row[2].strip()
        spe.voies_administration = row[3].strip()
        spe.statut_amm = row[4].strip()
        spe.type_procedure = row[5].strip()
        spe.etat_commercialisation = row[6].strip()
        spe.search_name = normalize(row[1])

    db.session.commit()
    print(f"✅ Spécialités : {created} créées, {updated} mises à jour ({len(seen_cis)} au total).")
    return seen_cis


def sync_compositions():
    """Remplace intégralement la table compositions à partir de COMPO.txt."""
    rows = _read_local_file(SOURCES["COMPO"])
    known_cis = {c[0] for c in db.session.query(SpecialiteModel.cis).all()}

    CompositionModel.query.delete()
    inserted = 0

    for row in rows:
        if len(row) < 8:
            continue
        cis = row[0].strip()
        if cis not in known_cis:
            continue

        substance = row[3].strip()
        db.session.add(
            CompositionModel(
                cis=cis,
                code_substance=row[2].strip(),
                denomination_substance=substance,
                dosage_substance=row[4].strip(),
                reference_dosage=row[5].strip(),
                nature_composant=row[6].strip(),
                numero_liaison=row[7].strip(),
                search_substance=normalize(substance),
            )
        )
        inserted += 1

        if inserted % 5000 == 0:
            db.session.flush()

    db.session.commit()
    print(f"✅ Compositions : {inserted} lignes importées.")


def sync_cip():
    """Remplace intégralement la table des CIP à partir de CIS_CIP.txt."""
    rows = _read_local_file(SOURCES["CIS_CIP"])
    known_cis = {c[0] for c in db.session.query(SpecialiteModel.cis).all()}

    CipModel.query.delete()
    inserted = 0

    for row in rows:
        if len(row) < 7:
            continue
        cis = row[0].strip()
        if cis not in known_cis:
            continue

        cip13 = row[6].strip()
        if not cip13:
            continue

        db.session.add(
            CipModel(
                cis=cis,
                cip7=row[1].strip(),
                libelle_presentation=row[2].strip(),
                statut_admin=row[3].strip(),
                etat_commercialisation=row[4].strip(),
                cip13=cip13
            )
        )
        inserted += 1

        if inserted % 5000 == 0:
            db.session.flush()

    db.session.commit()
    print(f"✅ Codes CIP : {inserted} lignes importées.")


def run_full_sync():
    print(f"\n--- 🔄 Importation ANSM démarrée ({datetime.now(UTC).isoformat()}) ---")
    sync_specialites()
    sync_compositions()
    sync_cip()


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        run_full_sync()