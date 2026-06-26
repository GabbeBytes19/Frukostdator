"""
Miljodatorn – data & logic layer

Environmental impact data sourced from food_data.xlsx.
All base values are per kg of food product:
  CO2   – kg CO2-ekvivalenter  (Carbon footprint, total)
  Land  – m² per år            (Cropland m2*year)
  Water – liter                (Water m3 × 1000)

Två beräkningslägen:
  calc_meal()   – "Din måltid":  portionsvikter × antal skanningar
  calc_per_kg() – "Per kg":      normaliserat per kg, dubletter ignoreras
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
    "påläggskorv salami rökt":                        "Cooked salami",
    "äpple m. skal":                                  "Apple (Malus domesticus)",
    "banan":                                          "Bananas (Musa × paradisica)",
    "jordgubbssylt":                                  "Jam, Berries",
    "havregryn fullkorn":                             "Oats, grain",
    "frukostflingor müsli fullkorn m. frukt":         "Muesli, mixed",
    "frukostflingor ris puffat m. socker berikad":    "Breakfast cereals, mixed cereals and honey",
    "munk u. fyllning":                               "Doughnuts",
    "nötkräm chokladkräm":                            "Chocolate spread with nuts",
}

# ── Portionsvikter (gram) per skannat livsmedel ───────────────────────────
PORTION_WEIGHTS_G = {
    "mellanmjölk fett 1,5% berikad":                250,
    "ägg kokt":                                      60,
    "smör fett 80%":                                 10,
    "ost hårdost fett 28%":                          20,
    "bröd fullkorn råg fibrer ca 7%":                35,
    "bröd vitt fibrer ca 5% typ formfranska":        35,
    "fruktyoghurt fett 2%":                         200,
    "mjölkchoklad":                                  25,
    "apelsinjuice drickf.":                         250,
    "påläggskorv salami rökt":                       15,
    "äpple m. skal":                                150,
    "banan":                                        120,
    "jordgubbssylt":                                 20,
    "havregryn fullkorn":                            40,
    "frukostflingor müsli fullkorn m. frukt":        50,
    "frukostflingor ris puffat m. socker berikad":   30,
    "munk u. fyllning":                              70,
    "nötkräm chokladkräm":                           15,
}

# ── Miljöpåverkan per kg livsmedel ────────────────────────────────────────
# Källa: food_data.xlsx (SAFAD, SLU)
# CO2  : kg CO2-ekvivalenter per kg
# Land : m² per år per kg
# Water: liter per kg  (ursprungliga m³ × 1000)

ENV_PER_KG = {
    "Cow milk, 1 - 2.9% fat (semi-skimmed milk)":   {"CO2": 1.027627, "Land":  1.462283, "Water":   2.512},
    "Whole egg, chicken":                           {"CO2": 1.264435, "Land":  4.922508, "Water":  22.012},
    "Butter":                                       {"CO2": 7.309092, "Land": 10.921177, "Water":  18.761},
    "Firm/semi-hard cheese (gouda and edam type)":  {"CO2": 6.673850, "Land":  9.848620, "Water":  16.918},
    "Rye bread, wholemeal":                         {"CO2": 0.877910, "Land":  2.404538, "Water":   3.253},
    "Wheat bread, white":                           {"CO2": 1.109815, "Land":  2.523161, "Water":   5.129},
    "Yoghurt cow milk, with fruit, 1 - 3% fat":     {"CO2": 1.137921, "Land":  1.605882, "Water":  38.132},
    "Milk chocolate, plain":                        {"CO2": 2.392347, "Land":  8.495578, "Water": 191.848},
    "Juice, Orange":                                {"CO2": 1.469274, "Land":  1.156571, "Water": 237.700},
    "Cooked salami":                                {"CO2": 7.955274, "Land": 20.847473, "Water": 413.393},
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
    Returnerar {skannarnamn: {CO2, Land, Water, portion_g}} – råvärden per kg
    plus portionsvikt för läget "Din måltid".
    """
    result = {}
    for scanner_name, dataset_name in FOOD_NAME_MAP.items():
        per_kg = ENV_PER_KG[dataset_name]
        result[scanner_name] = {
            "CO2":      per_kg["CO2"],
            "Land":     per_kg["Land"],
            "Water":    per_kg["Water"],
            "portion_g": PORTION_WEIGHTS_G.get(scanner_name, 100),
        }
    return result


def _make_result(counts: dict, foods: dict, use_portions: bool) -> dict:
    """Intern hjälpfunktion – beräknar totaler och nedbrytning."""
    total_co2 = total_land = total_water = 0.0
    breakdown = []
    for key, count in counts.items():
        info = foods.get(key, {})
        if use_portions:
            factor = info.get("portion_g", 100) / 1000.0 * count
        else:
            factor = 1.0   # per kg, count ignoreras
        co2   = info.get("CO2",   0.0) * factor
        land  = info.get("Land",  0.0) * factor
        water = info.get("Water", 0.0) * factor
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


def calc_meal(foods: dict, food_list: list) -> dict:
    """
    Läge 'Din måltid': portionsvikt × antal skanningar.
    Dubletter räknas – varje skanning = en portion.
    """
    counts: dict = {}
    for name in food_list:
        key = name.strip().lower()
        counts[key] = counts.get(key, 0) + 1
    return _make_result(counts, foods, use_portions=True)


def calc_per_kg(foods: dict, food_list: list) -> dict:
    """
    Läge 'Per kg': normaliserat per kg, varje unikt livsmedel räknas exakt en gång.
    Dubletter ignoreras.
    """
    unique = {name.strip().lower(): 1 for name in food_list}
    return _make_result(unique, foods, use_portions=False)


def _strip_swedish(s):
    return (s.replace('å', '').replace('ä', '').replace('ö', '').replace('ü', '')
             .replace('Å', '').replace('Ä', '').replace('Ö', '').replace('Ü', ''))

def build_barcode_map(foods_dict):
    """Returns {barcode_string: canonical_swedish_name} built by stripping å/ä/ö/ü."""
    return {_strip_swedish(name): name for name in foods_dict}

def resolve_scan(text, barcode_map):
    """Translates a barcode string (no special chars) to the canonical Swedish food name."""
    return barcode_map.get(text, text)