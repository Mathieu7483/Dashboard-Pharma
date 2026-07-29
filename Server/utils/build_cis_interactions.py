import pandas as pd
import os
import csv

script_dir = os.path.dirname(os.path.abspath(__file__))

# Chemins des fichiers
interactions_input = os.path.join(script_dir, "ansm_interactions.csv")
bdpm_compo_file = os.path.join(script_dir, "CIS_COMPO_bdpm.txt")  # Fichier officiel BDPM
output_csv = os.path.join(script_dir, "ansm_interactions_cis.csv")

def map_severity(text):
    t = str(text).lower()
    if "contre-indication" in t or "critical" in t:
        return "critical", "Danger imminent"
    elif "deconseillee" in t or "high" in t:
        return "high", "Danger élevé"
    elif "precaution" in t or "moderate" in t:
        return "moderate", "Danger relatif"
    elif "prendre en compte" in t or "low" in t:
        return "low", "Information / Risque faible"
    return "moderate", "Danger relatif"

def load_cis_substance_mapping():
    """Charge le mapping {substance: [codes_cis]} depuis CIS_COMPO_bdpm.txt si présent."""
    substance_to_cis = {}
    if not os.path.exists(bdpm_compo_file):
        print(f"⚠️ Fichier BDPM '{bdpm_compo_file}' introuvable. Les codes CIS seront générés au besoin.")
        return substance_to_cis

    print("⏳ Chargement de la base BDPM (CIS <-> Substances)...")
    # CIS_COMPO_bdpm.txt : 0=CIS, 1=Element, 2=Code Substance, 3=Nom Substance
    with open(bdpm_compo_file, mode='r', encoding='latin-1') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if len(row) >= 4:
                cis_code = row[0].strip()
                substance_name = row[3].strip().lower()
                if substance_name not in substance_to_cis:
                    substance_to_cis[substance_name] = []
                substance_to_cis[substance_name].append(cis_code)
    return substance_to_cis

def generate_precise_cis_csv():
    if not os.path.exists(interactions_input):
        print(f"❌ Fichier source introuvable : {interactions_input}")
        return

    substance_map = load_cis_substance_mapping()
    
    print("⏳ Génération du CSV enrichi avec les codes CIS...")
    df_inter = pd.read_csv(interactions_input, dtype=str)
    
    enriched_rows = []

    for idx, row in df_inter.iterrows():
        ing_a = str(row.get("ingredient_a", "")).lower().strip()
        ing_b = str(row.get("ingredient_b", "")).lower().strip()
        raw_sev = str(row.get("severity", "moderate"))
        desc = str(row.get("description", "Interaction à surveiller."))

        sev_code, danger_label = map_severity(raw_sev)

        # Récupération des codes CIS correspondants si disponibles
        cis_a_list = substance_map.get(ing_a, ["N/A"])
        cis_b_list = substance_map.get(ing_b, ["N/A"])

        # On prend le premier code CIS représentatif ou "N/A"
        cis_a = cis_a_list[0] if cis_a_list else "N/A"
        cis_b = cis_b_list[0] if cis_b_list else "N/A"

        enriched_rows.append({
            "cis_a": cis_a,
            "ingredient_a": ing_a,
            "cis_b": cis_b,
            "ingredient_b": ing_b,
            "severity": sev_code,
            "danger_level": danger_label,
            "description": desc.replace("\n", " ").strip()
        })

    df_out = pd.DataFrame(enriched_rows)
    df_out.drop_duplicates(subset=["ingredient_a", "ingredient_b", "severity"], inplace=True)
    df_out.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print(f"✅ CSV final généré avec succès : {output_csv}")
    print(f"📊 Nombre de règles intégrées : {len(df_out)}")

if __name__ == "__main__":
    generate_precise_cis_csv()