"""
Miljodatorn – data & logic layer

Environmental impact data sourced from food_data.xlsx.
All values are per kg of food product:
  CO2   – kg CO2-ekvivalenter  (Carbon footprint, total)
  Land  – m² per år            (Cropland m2*year)
  Water – liter                (Water m3 × 1000)

QR-kodens scannade namn (svenska livsmedelsnamn) mappas till
datamängdsnamnen från food_data.xlsx via FOOD_NAME_MAP.
Alla värden returneras per kg – ingen portionsskalning.
"""

# ── Skannarnamn → datamängdsnamn ──────────────────────────────────────────
FOOD_NAME_MAP = {
    "mellanmjölk fett 1,5% berikad":                 "Cow milk, 1 - 2.9% fat (semi-skimmed milk)",
    "ägg kokt":                                       "Whole egg, chicken",
    "smör fett 80%":                                  "Butter",
    "ost hårdost fett 28%":                           "Firm/semi-hard cheese (gouda and edam type)",
    "bröd fullkorn råg fibrer ca 7%":                 "Rye bread, wholemeal",
    "bröd vitt fibrer ca 5% typ formfranska":         "Wheat bread, white",
    "fruktyoghurt fett 2%":                           "Yoghurt cow milk, with fruit, 1 - 3% fat",
    "mjölkchoklad":                                   "Milk chocolate, plain",
    "apelsinjuice drickf.":                           "Juice, Orange",
    "påläggskorv salami rökt":                        "German salami",
    "äpple m. skal":                                  "Apple (Malus domesticus)",
    "banan":                                          "Bananas (Musa × paradisica)",
    "jordgubbssylt":                                  "Jam, Berries",
    "havregryn fullkorn":                             "Oats, grain",
    "frukostflingor müsli fullkorn m. frukt":         "Muesli, mixed",
    "frukostflingor ris puffat m. socker berikad":    "Breakfast cereals, mixed cereals and honey",
    "munk u. fyllning":                               "Doughnuts",
    "nötkräm chokladkräm":                            "Chocolate spread with nuts",
}

# ── Miljöpåverkan per kg livsmedel ────────────────────────────────────────
# Källa: food_data.xlsx
# CO2  : kg CO2-ekvivalenter per kg
# Land : m² per år per kg
# Water: liter per kg  (ursprungliga m³ × 1000)

ENV_PER_KG = {
    "Cow milk, 1 - 2.9% fat (semi-skimmed milk)":  {"CO2": 1.027627, "Land":  1.462283, "Water":   2.512},
    "Whole egg, chicken":                           {"CO2": 1.264435, "Land":  4.922508, "Water":  22.012},
    "Butter":                                       {"CO2": 7.309092, "Land": 10.921177, "Water":  18.761},
    "Firm/semi-hard cheese (gouda and edam type)":  {"CO2": 6.673850, "Land":  9.848620, "Water":  16.918},
    "Rye bread, wholemeal":                         {"CO2": 0.877910, "Land":  2.404538, "Water":   3.253},
    "Wheat bread, white":                           {"CO2": 1.109815, "Land":  2.523161, "Water":   5.129},
    "Yoghurt cow milk, with fruit, 1 - 3% fat":    {"CO2": 1.137921, "Land":  1.605882, "Water":  38.132},
    "Milk chocolate, plain":                        {"CO2": 2.392347, "Land":  8.495578, "Water": 191.848},
    "Juice, Orange":                                {"CO2": 1.469274, "Land":  1.156571, "Water": 237.700},
    "German salami":                                {"CO2": 6.816144, "Land": 18.036304, "Water": 358.119},
    "Apple (Malus domesticus)":                     {"CO2": 0.586071, "Land":  0.570176, "Water":  58.084},
    "Bananas (Musa × paradisica)":                  {"CO2": 0.707259, "Land":  0.313760, "Water":  88.344},
    "Jam, Berries":                                 {"CO2": 1.935196, "Land":  2.931285, "Water": 303.387},
    "Oats, grain":                                  {"CO2": 0.599691, "Land":  3.631680, "Water":   1.585},
    "Muesli, mixed":                                {"CO2": 1.578385, "Land":  4.782941, "Water":  51.998},
    "Breakfast cereals, mixed cereals and honey":   {"CO2": 1.259911, "Land":  3.326675, "Water": 119.935},
    "Doughnuts":                                    {"CO2": 1.841037, "Land":  3.739613, "Water":  83.893},
    "Chocolate spread with nuts":                   {"CO2": 4.058469, "Land":  4.702116, "Water": 304.252},
}


def get_food_impacts() -> dict:
    """
    Returnerar {skannarnamn: {CO2, Land, Water}} – alla värden per kg, ingen skalning.
    """
    result = {}
    for scanner_name, dataset_name in FOOD_NAME_MAP.items():
        per_kg = ENV_PER_KG[dataset_name]
        result[scanner_name] = {
            "CO2":          per_kg["CO2"],
            "Land":         per_kg["Land"],
            "Water":        per_kg["Water"],
            "dataset_name": dataset_name,
        }
    return result


def calc(foods: dict, food_list: list) -> dict:
    """
    Summerar miljöpåverkan för en lista skannade livsmedel (per kg vardera).
    Returnerar totaler + per-unikt-livsmedel-nedbrytning (dubbletter slås ihop).
    """
    total_co2   = 0.0
    total_land  = 0.0
    total_water = 0.0

    # Slå ihop dubletter – räkna förekomster och multiplicera
    counts: dict = {}
    for name in food_list:
        key = name.strip().lower()
        counts[key] = counts.get(key, 0) + 1

    breakdown = []
    for key, count in counts.items():
        info  = foods.get(key, {})
        co2   = info.get("CO2",   0.0) * count
        land  = info.get("Land",  0.0) * count
        water = info.get("Water", 0.0) * count
        total_co2   += co2
        total_land  += land
        total_water += water
        breakdown.append({
            "name":  key,
            "count": count,
            "CO2":   round(co2,   4),
            "Land":  round(land,  4),
            "Water": round(water, 3),
        })

    return {
        "co2":       round(total_co2,   4),
        "land":      round(total_land,  4),
        "water":     round(total_water, 3),
        "breakdown": breakdown,
    }