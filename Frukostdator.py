import pandas as pd



def get_excel_file():
   
    df = pd.read_excel("LivsmedelsDB_202602231534.xlsx",header = 2)

    return df


def get_food_and_info(df):

    foods = {}

    for index, row in df.iterrows():
        name = row["Livsmedelsnamn"]

        value = {
            "Energi": row["Energi (kcal)"],
            "Fett": row["Fett, totalt (g)"],
            "Protein": row["Protein (g)"],
            "Kolhydrater": row["Kolhydrater, tillgängliga (g)"]
        }

        foods[name] = value
    return foods




my_df = get_excel_file()
my_foods_dict = get_food_and_info(my_df)

#print(list(my_foods_dict.items())[:5])
#print(my_foods_dict.values())[:5]