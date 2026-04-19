"""
Converts LivsmedelsDB_202602231534.xlsx → frukost_livsmedel.json
Run once: python export_foods_json.py
Then place frukost_livsmedel.json next to frukostdator.html.
"""
import json
import pandas as pd

df = pd.read_excel("LivsmedelsDB_202602231534.xlsx", header=2)
foods = {}
for _, row in df.iterrows():
    name = str(row["Livsmedelsnamn"]).strip().lower()
    try:
        foods[name] = {
            "Energi":  float(row["Energi (kcal)"])  if pd.notna(row["Energi (kcal)"])  else 0,
            "Fett":    float(row["Fett, totalt (g)"]) if pd.notna(row["Fett, totalt (g)"]) else 0,
            "Protein": float(row["Protein (g)"])     if pd.notna(row["Protein (g)"])     else 0,
            "Socker":  float(row["Fritt socker (g)"]) if pd.notna(row["Fritt socker (g)"]) else 0,
        }
    except Exception:
        pass

with open("frukost_livsmedel.json", "w", encoding="utf-8") as f:
    json.dump(foods, f, ensure_ascii=False, indent=2)

print(f"✅ Exporterade {len(foods)} livsmedel → frukost_livsmedel.json")
