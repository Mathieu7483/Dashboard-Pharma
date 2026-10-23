"""
Complète initial_inventory.csv avec les codes CIP13 de la base ANSM locale.

À placer dans Server/utils/ (à côté de initial_inventory.csv), puis, depuis le
dossier Server :

    python -m utils.fill_cip_csv

Produit deux fichiers dans utils/ (le CSV d'origine n'est pas modifié) :
  - initial_inventory_cip.csv : le CSV complété, à relire puis à renommer
  - cip_report.csv            : pour chaque produit, la spécialité et la
                                présentation choisies, avec le niveau de confiance

Statuts du rapport :
  OK_NOM_DOSAGE        nom de marque ou de DCI trouvé + substance + dosage identiques
  OK_SUBSTANCE_DOSAGE  mêmes substances et même dosage (générique choisi automatiquement)
  NOM_SEUL             nom + substance trouvés, mais dosage non vérifiable : à contrôler
  AUCUN                aucune correspondance (normal pour le matériel et la parapharmacie)
  DEJA_RENSEIGNE       le CSV avait déjà un CIP13, conservé tel quel
"""
import csv
import os
import re

from app import create_app
from database.data_manager import db
from models.specialite import SpecialiteModel
from models.composition import CompositionModel
from models.cip import CipModel
from utils.text_norm import normalize

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, 'initial_inventory.csv')
OUT = os.path.join(BASE, 'initial_inventory_cip.csv')
REPORT = os.path.join(BASE, 'cip_report.csv')

FIELDS = ['name', 'active_ingredient', 'dosage', 'stock', 'price',
          'is_prescription_only', 'cip13']
DOSE_RE = re.compile(r'^\d+(?:\.\d+)?(?:mg|g|mcg|ug|ui)$')


def _key(text):
    """'500 mg' / '500mg' / '0,4 mg' -> '500mg' / '500mg' / '0.4mg'."""
    return normalize(text or '').replace(' ', '').replace(',', '.')


def _ingredients(raw):
    """'paracetamol/codeine' -> ['paracetamol', 'codeine'] ; 'n/a' -> []."""
    text = normalize(raw or '').strip()
    if text in ('', 'n/a', 'n.a', 'na'):
        return []
    for delim in (',', '/', '+', ';'):
        text = text.replace(delim, '|')
    return [p.strip() for p in text.split('|') if p.strip()]


def load_reference():
    """Charge les trois tables ANSM en mémoire (quelques secondes)."""
    specs = {}
    for cis, den, sname, etat in db.session.query(
            SpecialiteModel.cis, SpecialiteModel.denomination,
            SpecialiteModel.search_name, SpecialiteModel.etat_commercialisation):
        specs[cis] = {
            'den': den or '',
            'sname': sname or normalize(den or ''),
            'commercial': normalize(etat or '').startswith('commerc'),
        }

    # Substances actives uniquement : (nom normalisé, dosage normalisé)
    subs = {}
    for cis, sub, dose in db.session.query(
            CompositionModel.cis, CompositionModel.denomination_substance,
            CompositionModel.dosage_substance
    ).filter(CompositionModel.nature_composant == 'SA'):
        subs.setdefault(cis, []).append((normalize(sub or ''), _key(dose)))

    # Meilleure présentation par spécialité : active, puis commercialisée
    best_cip = {}
    for cis, cip13, libelle, statut, etat in db.session.query(
            CipModel.cis, CipModel.cip13, CipModel.libelle_presentation,
            CipModel.statut_admin, CipModel.etat_commercialisation):
        if not cip13:
            continue
        st, et = normalize(statut or ''), normalize(etat or '')
        rank = (0 if 'active' in st else 1,
                0 if ('commercialisation' in et and 'arret' not in et) else 1)
        cur = best_cip.get(cis)
        if cur is None or rank < cur[2]:
            best_cip[cis] = (cip13, libelle or '', rank)

    return specs, subs, best_cip


def main():
    specs, subs, best_cip = load_reference()
    sub_sets = {cis: frozenset(s for s, _ in lst) for cis, lst in subs.items()}
    usable = [cis for cis in specs if cis in best_cip]
    print(f"Référentiel : {len(specs)} spécialités, {len(best_cip)} avec présentation, "
          f"{len(subs)} avec composition.")

    def name_hit(cis, name_n):
        sname = specs[cis]['sname']
        return (name_n and sname.startswith(name_n)
                and (len(sname) == len(name_n) or sname[len(name_n)] in ' ,/-'))

    def ing_exact(ings, cis):
        ss = sub_sets.get(cis, frozenset())
        return bool(ings) and len(ss) == len(ings) and all(
            any(i in s for s in ss) for i in ings)

    def ing_loose(ings, cis):
        ss = sub_sets.get(cis, frozenset())
        return bool(ings) and any(i in s for i in ings for s in ss)

    def dose_ok(dose_key, ings, cis):
        return any(ings[0] in s and d == dose_key for s, d in subs.get(cis, []))

    def best(cands, name_n):
        return min(cands, key=lambda c: (
            not name_hit(c, name_n),
            not specs[c]['commercial'],
            best_cip[c][2],
            len(specs[c]['den'])))

    with open(SRC, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))

    out_rows, report, counts = [], [], {}

    for row in rows:
        name = (row.get('name') or '').strip()
        name_n = normalize(name)
        ings = _ingredients(row.get('active_ingredient'))
        dose_raw = _key(row.get('dosage'))
        dose = dose_raw if DOSE_RE.match(dose_raw) else None
        existing = (row.get('cip13') or '').strip()

        chosen, status = None, 'AUCUN'

        if existing:
            status = 'DEJA_RENSEIGNE'
        else:
            # 1) Par nom (marque ou DCI en tête de dénomination)
            by_name = [c for c in usable if name_hit(c, name_n)]
            if by_name and ings:
                if dose:
                    ok = [c for c in by_name if ing_loose(ings, c) and dose_ok(dose, ings, c)]
                    if ok:
                        chosen, status = best(ok, name_n), 'OK_NOM_DOSAGE'
                if not chosen:
                    loose = [c for c in by_name if ing_loose(ings, c)]
                    if loose:
                        chosen, status = best(loose, name_n), 'NOM_SEUL'

            # 2) Par substances + dosage (générique)
            if not chosen and ings and dose:
                ok = [c for c in usable if ing_exact(ings, c) and dose_ok(dose, ings, c)]
                if ok:
                    chosen, status = best(ok, name_n), 'OK_SUBSTANCE_DOSAGE'

        out = {k: (row.get(k) or '').strip() for k in FIELDS}
        if chosen:
            out['cip13'] = best_cip[chosen][0]
        out_rows.append(out)

        counts[status] = counts.get(status, 0) + 1
        report.append({
            'name': name,
            'statut': status,
            'specialite': specs[chosen]['den'] if chosen else '',
            'presentation': best_cip[chosen][1] if chosen else '',
            'cip13': out['cip13'],
        })

    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out_rows)

    with open(REPORT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['name', 'statut', 'specialite', 'presentation', 'cip13'])
        w.writeheader()
        w.writerows(report)

    print(f"\n{len(rows)} produits traités :")
    for status, n in sorted(counts.items()):
        print(f"  {status:<22} {n}")
    print(f"\nCSV complété : {OUT}")
    print(f"Rapport      : {REPORT}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        main()