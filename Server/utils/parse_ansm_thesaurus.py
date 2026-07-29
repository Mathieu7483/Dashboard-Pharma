"""
Parse le Thésaurus des interactions médicamenteuses de l'ANSM (PDF -> CSV).

Usage:
    python3 parse_ansm_thesaurus.py input.pdf output.csv

Le PDF a une mise en page en 2 colonnes par bloc d'interaction :
- colonne gauche (x0 ~ 97) : mécanisme / justification pharmacologique
- colonne droite (x0 >= 300) : niveau de contrainte ANSM (CI/ASDEC/PE/APEC
  ou libellé complet) + conduite à tenir

Structure hiérarchique :
    NOM_CLASSE_OU_SUBSTANCE_A   (x0 ~ 29-40, majuscules, sans '+')
      Voir aussi : ...          (x0 ~ 36, ignoré - juste une référence croisée)
      +SUBSTANCE_B              (x0 ~ 32, commence par '+')
          <mécanisme wrap...>   (x0 ~ 97)
                                            <code sévérité + conduite>  (x0 >= 300)
      +AUTRE_SUBSTANCE_B
          ...
"""

import sys
import csv
import re
import unicodedata
import pdfplumber

HEADER_X_MAX = 50       # x0 < 50  -> ligne de titre (classe, "+substance", "Voir aussi")
RIGHT_COL_X_MIN = 300    # x0 >= 300 -> colonne droite (sévérité / conduite)
FIRST_CONTENT_PAGE = 3   # page 1 = couverture, page 2 = intro -> contenu utile à partir de la page 3 (1-indexed)

# Mapping des codes ANSM -> échelle de risque demandée
SEVERITY_RANK = {
    "CI": (4, "critical"),
    "ASDEC": (3, "high"),
    "PE": (2, "moderate"),
    "APEC": (1, "low"),
}

# Reconnaissance des libellés complets (quand un seul niveau s'applique)
FULL_LABEL_PATTERNS = [
    (re.compile(r"\bcontre-?indication\b", re.IGNORECASE), "CI"),
    (re.compile(r"association\s+d[ée]conseill[ée]e", re.IGNORECASE), "ASDEC"),
    (re.compile(r"pr[ée]caution\s+d['’]emploi", re.IGNORECASE), "PE"),
    (re.compile(r"[àa]\s+prendre\s+en\s+compte", re.IGNORECASE), "APEC"),
]

# Reconnaissance des codes abrégés combinés, ex: "CI - ASDEC - APEC", "ASDEC - APEC"
ABBREV_TOKEN_RE = re.compile(r"\b(CI|ASDEC|PE|APEC)\b")


def normalize(s: str) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii").lower().strip()


def extract_severity_codes(code_line: str) -> list:
    """Retourne la liste des codes ANSM trouvés (ex: ['CI','PE']) dans la 1ere ligne de la colonne droite."""
    codes = set()
    for pattern, code in FULL_LABEL_PATTERNS:
        if pattern.search(code_line):
            codes.add(code)
    for tok in ABBREV_TOKEN_RE.findall(code_line):
        codes.add(tok)
    return sorted(codes, key=lambda c: -SEVERITY_RANK[c][0])


LINE_TOLERANCE = 3  # px : deux mots dont le 'top' diffère de moins de ça sont sur la même ligne


def rows_from_page(page):
    """
    Regroupe les mots d'une page en lignes, en tolérant de petits écarts de
    'top' entre mots d'une même ligne (certains glyphes, notamment '+', ont
    une métrique verticale légèrement différente et un round() strict les
    isole à tort sur leur propre ligne).
    """
    words = sorted(page.extract_words(use_text_flow=False), key=lambda w: (w["top"], w["x0"]))
    rows = []
    current_row = []
    current_top = None
    for w in words:
        if current_top is None or abs(w["top"] - current_top) <= LINE_TOLERANCE:
            current_row.append(w)
            # Recentre la référence sur la moyenne pour éviter la dérive cumulative
            current_top = sum(x["top"] for x in current_row) / len(current_row)
        else:
            rows.append(sorted(current_row, key=lambda x: x["x0"]))
            current_row = [w]
            current_top = w["top"]
    if current_row:
        rows.append(sorted(current_row, key=lambda x: x["x0"]))
    return rows


def parse_pdf(pdf_path: str) -> list:
    records = []

    current_class = None       # substance_a (nom de classe/molécule en tête de section)
    current_substance_b = None
    mechanism_buf = []
    right_buf = []              # toutes les lignes de la colonne droite du bloc courant
    current_page_start = None

    def flush_block():
        if current_substance_b is None:
            return
        mechanism = " ".join(mechanism_buf).strip()
        right_text_lines = [l for l in right_buf if l.strip()]
        if not right_text_lines:
            return  # bloc vide / anomalie de mise en page -> on ignore plutôt que d'inventer une sévérité
        code_line = right_text_lines[0]
        conduct = " ".join(right_text_lines[1:]).strip()
        codes = extract_severity_codes(code_line)
        if not codes:
            # Sécurité : si on n'a pas pu déterminer le(s) code(s), on ne perd pas la ligne,
            # on la marque explicitement comme non classifiée pour revue manuelle.
            severity_key = "unclassified"
            worst_code = ""
        else:
            worst_code = codes[0]
            severity_key = SEVERITY_RANK[worst_code][1]

        records.append({
            "substance_a": current_class or "",
            "substance_b": current_substance_b,
            "substance_a_norm": normalize(current_class or ""),
            "substance_b_norm": normalize(current_substance_b),
            "severity": severity_key,
            "ansm_codes": ";".join(codes),
            "mechanism": mechanism,
            "conduct": conduct,
            "source_page": current_page_start,
        })

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for page_index in range(FIRST_CONTENT_PAGE - 1, total_pages):
            page = pdf.pages[page_index]
            printed_page_no = page_index + 1
            for row in rows_from_page(page):
                if not row:
                    continue

                row_text_all = " ".join(w["text"] for w in row).strip()
                row_top = row[0]["top"]
                if row_top < 40 and row_text_all.isdigit():
                    continue  # numéro de page imprimé en haut de page -> pas du contenu

                is_header = row[0]["x0"] < HEADER_X_MAX

                if is_header:
                    # Une ligne d'en-tete (classe, "+substance", "Voir aussi") peut etre
                    # longue et deborder dans la zone x>=300 : on ne doit PAS la couper
                    # en deux colonnes dans ce cas, sinon la fin du nom est perdue.
                    left_text = " ".join(w["text"] for w in row).strip()
                    right_text = ""
                else:
                    left_words = [w for w in row if w["x0"] < RIGHT_COL_X_MIN]
                    right_words = [w for w in row if w["x0"] >= RIGHT_COL_X_MIN]
                    left_text = " ".join(w["text"] for w in left_words).strip()
                    right_text = " ".join(w["text"] for w in right_words).strip()

                if is_header:
                    if left_text.lower().startswith("voir aussi"):
                        continue  # référence croisée informative, pas une interaction
                    # Les lignes "Voir aussi : ..." peuvent continuer sur 2-3 lignes ;
                    # ces lignes de continuation sont en minuscules (contrairement aux
                    # noms de classe/substance, toujours en MAJUSCULES dans ce document).
                    letters_only = re.sub(r"[^A-Za-zÀ-ÿ]", "", left_text)
                    is_shouting = bool(letters_only) and letters_only == letters_only.upper()
                    if not left_text.startswith("+") and not is_shouting:
                        continue  # suite d'une ligne "Voir aussi" -> ignorer
                    if left_text.startswith("+"):
                        # Nouvelle interaction au sein de la classe courante
                        flush_block()
                        current_substance_b = left_text.lstrip("+").strip()
                        mechanism_buf = []
                        right_buf = []
                        current_page_start = printed_page_no
                    else:
                        # Purement numérique (numéro de page mal classé) -> ignorer
                        if left_text.strip().isdigit():
                            continue
                        # Nouvelle classe/molécule (section A)
                        flush_block()
                        current_class = left_text.strip()
                        current_substance_b = None
                        mechanism_buf = []
                        right_buf = []
                else:
                    if left_text and current_substance_b is not None:
                        mechanism_buf.append(left_text)

                if right_text and current_substance_b is not None:
                    right_buf.append(right_text)

        flush_block()  # dernier bloc du document

    return records


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 parse_ansm_thesaurus.py input.pdf output.csv")
        sys.exit(1)

    pdf_path, csv_path = sys.argv[1], sys.argv[2]
    records = parse_pdf(pdf_path)

    fieldnames = [
        "substance_a", "substance_b", "substance_a_norm", "substance_b_norm",
        "severity", "ansm_codes", "mechanism", "conduct", "source_page",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"✅ {len(records)} interactions extraites -> {csv_path}")

    # Petit rapport de contrôle qualité
    unclassified = sum(1 for r in records if r["severity"] == "unclassified")
    by_sev = {}
    for r in records:
        by_sev[r["severity"]] = by_sev.get(r["severity"], 0) + 1
    print("Répartition par sévérité :", by_sev)
    if unclassified:
        print(f"⚠️ {unclassified} lignes non classifiées (code sévérité introuvable) — à vérifier manuellement.")


if __name__ == "__main__":
    main()