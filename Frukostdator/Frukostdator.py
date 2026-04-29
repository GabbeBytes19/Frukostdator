import pandas as pd

# Portionsvikter (gram) för valda livsmedel
PORTION_WEIGHTS = {
    "mellanmjölk fett 1,5% berikad": 250,
    "ägg kokt": 60,
    "smör normalsaltat": 10,
    "ost hårdost fett 28%": 20,
    "bröd fullkorn råg fibrer ca 7%": 35,
    "bröd vitt fibrer ca 5% typ formfranska": 35,
    "fruktyoghurt fett 2%": 200,
    "mjölkchoklad": 25,
    "apelsinjuice drickf.": 250,
    "påläggskorv salami rökt": 15,
    "äpple m. skal": 150,
    "banan": 120,
    "jordgubbssylt": 20,
    "havregryn fullkorn": 40,
    "frukostflingor müsli fullkorn m. frukt": 50,
    "frukostflingor ris puffat m. socker berikad": 30,
    "munk u. fyllning": 70,
    "nötkräm chokladkräm": 15,
}

def get_excel_file():
    # Se till att filnamnet stämmer med din fil
    df = pd.read_excel("LivsmedelsDB_202602231534.xlsx", header=2)
    return df


def get_food_and_info(df):
    foods = {}

    for index, row in df.iterrows():
        name = str(row["Livsmedelsnamn"]).strip().lower()

        # Hämta portionsvikt (default 100g)
        weight = PORTION_WEIGHTS.get(name, 100)
        factor = weight / 100

        value = {
            "Energi": row["Energi (kcal)"] * factor,
            "Fett": row["Fett, totalt (g)"] * factor,
            "Protein": row["Protein (g)"] * factor,
            "Socker": row["Fritt socker (g)"] * factor,
            "Fibrer": row["Fibrer (g)"] * factor,
        }

        foods[name] = value

    return foods

#används inte?
def get_data_from_scanner(foods, food_list):
    total_energi = 0
    total_fett = 0
    total_protein = 0
    total_socker = 0
    total_fibrer = 0

    for food in food_list:
        if food in foods:
            info = foods[food]
            total_energi += info["Energi"]
            total_fett += info["Fett"]
            total_protein += info["Protein"]
            total_socker += info["Socker"]
            total_fibrer += info["Fibrer"]

    return [total_energi, total_fett, total_protein, total_socker, total_fibrer]
