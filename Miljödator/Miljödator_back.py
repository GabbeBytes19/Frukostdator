

##Inspiration kanske ? 
#https://matkalkylatorn.se 



import json

def get_data():
    with open("Food-Carbon-Footprint.json","r") as file:
        data = json.load(file)

    print(data)

get_data()