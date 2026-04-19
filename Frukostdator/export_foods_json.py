"""
Injects the full food database from LivsmedelsDB_202602231534.xlsx
directly into frukostdator.html so it works with file:// on Raspberry Pi
(no server needed).

Run once after cloning:
    python3 export_foods_json.py
"""
import json, re, sys
import pandas as pd

XLSX = "LivsmedelsDB_202602231534.xlsx"
HTML = "frukostdator.html"

df = pd.read_excel(XLSX, header=2)
foods = {}
for _, row in df.iterrows():
    name = str(row["Livsmedelsnamn"]).strip().lower()
    try:
        foods[name] = {
            "Energi":  float(row["Energi (kcal)"])   if pd.notna(row["Energi (kcal)"])   else 0,
            "Fett":    float(row["Fett, totalt (g)"]) if pd.notna(row["Fett, totalt (g)"]) else 0,
            "Protein": float(row["Protein (g)"])      if pd.notna(row["Protein (g)"])      else 0,
            "Socker":  float(row["Fritt socker (g)"]) if pd.notna(row["Fritt socker (g)"]) else 0,
        }
    except Exception:
        pass

with open(HTML, encoding="utf-8") as f:
    html = f.read()

json_str = json.dumps(foods, ensure_ascii=False)
placeholder = "/* __FULL_FOODS_PLACEHOLDER__ */"
injection   = f"const FULL_FOODS = {json_str};"

if placeholder in html:
    html = html.replace(placeholder, injection)
elif "const FULL_FOODS = " in html:
    html = re.sub(r"const FULL_FOODS = \{.*?\};", injection, html, flags=re.DOTALL)
else:
    print("❌ Kunde inte hitta platshållaren i HTML-filen. Har du rätt version?")
    sys.exit(1)

with open(HTML, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Inbäddade {len(foods)} livsmedel direkt i {HTML}")
