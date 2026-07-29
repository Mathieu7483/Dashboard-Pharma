import csv
import io
import requests
from datetime import datetime, UTC
from database.data_manager import db
from models.specialite import SpecialiteModel
from models.composition import CompositionModel
from utils.text_norm import normalize

ANSM_BASE = "https://base-donnees-publique.medicaments.gouv.fr/download/file"
SOURCES = {
    "CIS": f"{ANSM_BASE}/CIS_bdpm.txt",
    "COMPO": f"{ANSM_BASE}/CIS_COMPO_bdpm.txt",
}


def _fetch_lines(url: str) -> list:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    resp.encoding = "iso-8859-1"
    reader = csv.reader(io.StringIO(resp.text), delimiter="\t")
    return list(reader)


def sync_specialites():
    """Upsert des spécialités (CIS_bdpm.txt)."""
    rows = _fetch_lines(SOURCES["CIS"])
    seen_cis = set()
    created, updated = 0, 0

    for row in rows:
        if len(row) < 7:
            continue
        cis = row[0].strip()
        if not cis:
            continue
        seen_cis.add(cis)

        spe = SpecialiteModel.query.get(cis)
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
    print(f"✅ Spécialités : {created} créées, {updated} mises à jour ({len(seen_cis)} au total ANSM).")
    return seen_cis


def sync_compositions():
    """Remplace intégralement la table (plus simple/fiable qu'un diff ligne à ligne)."""
    rows = _fetch_lines(SOURCES["COMPO"])
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
        db.session.add(CompositionModel(
            cis=cis,
            code_substance=row[2].strip(),
            denomination_substance=substance,
            dosage_substance=row[4].strip(),
            reference_dosage=row[5].strip(),
            nature_composant=row[6].strip(),
            numero_liaison=row[7].strip(),
            search_substance=normalize(substance),
        ))
        inserted += 1

        if inserted % 5000 == 0:
            db.session.flush()

    db.session.commit()
    print(f"✅ Compositions : {inserted} lignes importées.")


def run_full_sync():
    print(f"\n--- 🔄 Resync ANSM démarrée ({datetime.now(UTC).isoformat()}) ---")
    sync_specialites()
    sync_compositions()

    # Rafraîchit le dictionnaire d'entités du chatbot après resync
    try:
        from core.chatbot.NLUProcessor import NLUProcessor
        # Si l'app garde une instance globale du NLU, on la rafraîchit ici.
        # À adapter selon comment l'instance est exposée dans ton app.py.
    except Exception:
        pass

    print("--- ✅ Resync ANSM terminée ---\n")