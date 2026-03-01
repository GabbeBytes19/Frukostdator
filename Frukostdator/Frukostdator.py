import pandas as pd



def get_excel_file():
   
    df = pd.read_excel("LivsmedelsDB_202602231534.xlsx",header = 2) #Källa:Livsmedelsverket

    return df


def get_food_and_info(df):

    foods = {}

    for index, row in df.iterrows():
        name = row["Livsmedelsnamn"]

        value = {
            "Energi": row["Energi (kcal)"],
            "Fett": row["Fett, totalt (g)"],
            "Protein": row["Protein (g)"],
            "Socker": row["Sockerarter, totalt (g)"]
        }

        foods[name] = value
    return foods

def get_data_from_scanner(foods,scanned_data):
    total_energi = 0
    total_fett = 0
    total_protein = 0
    total_socker = 0

    while True:
        
        if scanned_data in foods:
            info = foods[scanned_data]
            total_energi += info["Energi"]
            total_fett += info["Fett"]
            total_protein += info["Protein"]
            total_socker += info["Socker"]
        else:
            return None
        
        return [total_energi,total_fett,total_protein,total_socker]





#print(list(my_foods_dict.items())[:5])
#print(my_foods_dict.values())[:5]