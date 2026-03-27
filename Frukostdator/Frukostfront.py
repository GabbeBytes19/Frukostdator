from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.image import Image
from kivy.uix.spinner import Spinner
import Frukostdator

my_df = Frukostdator.get_excel_file()
my_foods_dict = Frukostdator.get_food_and_info(my_df)

Window.clearcolor = (0.08, 0.08, 0.1, 1)


def estimate_weight(age):
    if age <= 10:
        return (age + 4) * 2
    elif age <= 20:
        return (age * 3) + 7
    else:
        return 75


def get_energy_multiplier(age):
    weight = estimate_weight(age)
    return 1000 / weight


def get_daily_calories(age, gender):
    if age <= 3:
        return 1100
    elif age <= 6:
        return 1510
    elif age <= 10:
        return 1860
    elif age <= 14:
        if gender == "man":
            return 2510
        elif gender == "kvinna":
            return 2200
        else:
            return (2510 + 2200) / 2
    elif age <= 17:
        if gender == "man":
            return 3040
        elif gender == "kvinna":
            return 2410
        else:
            return (3040 + 2410) / 2
    else:
        if age <= 24:
            male = 2800
            female = 2200
        elif age <= 50:
            male = 2700
            female = 2200
        elif age <= 70:
            male = 2500
            female = 2000
        else:
            male = 2400
            female = 2000

        if gender == "man":
            return male
        elif gender == "kvinna":
            return female
        else:
            return (male + female) / 2


class NutrientCard(BoxLayout):
    def __init__(self, title, value_text, color, image_path=None, **kwargs):
        super().__init__(orientation="vertical", padding=15, size_hint_y=None, height=500, **kwargs)

        with self.canvas.before:
            Color(*color)
            self.bg = RoundedRectangle(radius=[20])

        self.bind(pos=self.update_bg, size=self.update_bg)

        self.title = Label(text=title, font_size=40, bold=True)
        self.value = Label(text=value_text, font_size=24)

        self.add_widget(self.title)
        self.add_widget(self.value)

        if image_path:
            self.image = Image(source=image_path, size_hint=(1, 0.6))
            self.add_widget(self.image)

        self.opacity = 0
        Animation(opacity=1, duration=0.5).start(self)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size


class FoodAppLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=20, spacing=15, **kwargs)
        self.food_list = []
        self.gender = "other"

        self.input = TextInput(
            hint_text="Skriv matvara (tomat, banan, bröd)...",
            size_hint=(1, 0.1),
            font_size=20
        )
        self.add_widget(self.input)

        self.age_spinner = Spinner(
            text="Välj ålder",
            values=[str(i) for i in range(1,101)],
            size_hint=(1,0.1),
            font_size=20
        )
        self.add_widget(self.age_spinner)

        gender_layout = BoxLayout(size_hint=(1,0.1), spacing=10)

        self.male_button = Button(text="Man")
        self.female_button = Button(text="Kvinna")
        self.other_button = Button(text="Vill ej ange")

        self.male_button.bind(on_press=lambda x: setattr(self, "gender", "man"))
        self.female_button.bind(on_press=lambda x: setattr(self, "gender", "kvinna"))
        self.other_button.bind(on_press=lambda x: setattr(self, "gender", "other"))

        gender_layout.add_widget(self.male_button)
        gender_layout.add_widget(self.female_button)
        gender_layout.add_widget(self.other_button)

        self.add_widget(gender_layout)

        self.add_button = Button(
            text="Lägg till livsmedel",
            size_hint=(1, 0.1),
            font_size=20,
            background_color=(0.3, 0.6, 1, 1)
        )

        self.finish_button = Button(
            text="Handlat klart",
            size_hint=(1, 0.1),
            font_size=20,
            background_color=(0.3, 0.6, 1, 1)
        )

        self.reset_button = Button(
            text="Nollställ räknaren",
            size_hint=(1, 0.1),
            font_size=20,
            background_color=(0.3, 0.6, 1, 1)
        )

        self.add_button.bind(on_press=self.add_food)
        self.finish_button.bind(on_press=self.show_food)
        self.reset_button.bind(on_press=self.reset_foods)

        self.add_widget(self.add_button)
        self.add_widget(self.finish_button)
        self.add_widget(self.reset_button)

        self.scroll = ScrollView()
        self.cards_layout = GridLayout(cols=4, spacing=15, size_hint_y=None)
        self.cards_layout.bind(minimum_height=self.cards_layout.setter('height'))
        self.scroll.add_widget(self.cards_layout)

        self.add_widget(self.scroll)

    def clear_cards(self):
        self.cards_layout.clear_widgets()


##################################################################

    def add_food(self, instance):
        scanned_data = self.input.text.strip()
        if not scanned_data:
            return 

        if scanned_data in my_foods_dict:
            self.food_list.append(scanned_data)
            self.input.text = ""  
        else:
            self.clear_cards()
            self.cards_layout.add_widget(
                NutrientCard("Hittades inte", f"{scanned_data} finns inte i databasen", (0.4, 0.1, 0.1, 1))
            )
            return

        self.clear_cards()

    def show_food(self, instance):

        result_total = Frukostdator.get_data_from_scanner(my_foods_dict, self.food_list)

        if self.food_list == []:
            self.clear_cards()
            self.cards_layout.add_widget(
                NutrientCard("Du har ej lagt till något livsmedel ännu", "gör detta innan du handlat klart", (0.4, 0.1, 0.1, 1))
            )
            return

        if self.age_spinner.text == "Välj ålder":
            return

        age = int(self.age_spinner.text)

        self.clear_cards()

        daily_kcal = get_daily_calories(age, self.gender)

        kcal = result_total[0]
        fat_g = result_total[1]
        protein_g = result_total[2]
        sugar_g = result_total[3]

        percent = round((kcal / daily_kcal) * 100) if daily_kcal > 0 else 0


        protein_min_day = (daily_kcal * 0.10) / 4
        protein_max_day = (daily_kcal * 0.20) / 4

        fat_min_day = (daily_kcal * 0.25) / 9
        fat_max_day = (daily_kcal * 0.40) / 9

        sugar_max_day = (daily_kcal * 0.10) / 4


        protein_min_breakfast = round(protein_min_day * 0.20)
        protein_max_breakfast = round(protein_max_day * 0.25)

        fat_min_breakfast = round(fat_min_day * 0.20)
        fat_max_breakfast = round(fat_max_day * 0.25)

        sugar_max_breakfast = round(sugar_max_day * 0.25)

        kcal_min_breakfast = round(daily_kcal * 0.20)
        kcal_max_breakfast = round(daily_kcal * 0.25)


        protein_percent_day = round((protein_g / protein_max_day) * 100) if protein_max_day > 0 else 0
        fat_percent_day = round((fat_g / fat_max_day) * 100) if fat_max_day > 0 else 0
        sugar_percent_day = round((sugar_g / sugar_max_day) * 100) if sugar_max_day > 0 else 0


        self.cards_layout.add_widget(
            NutrientCard(
                "Energi",
                f"{kcal} kcal (mål {kcal_min_breakfast}-{kcal_max_breakfast} kcal)\n{percent}% av dagsintag ({round(daily_kcal)})",
                (0.9, 0.6, 0.1, 1),
                image_path="../images/Energi.png"
            )
        )


        self.cards_layout.add_widget(
            NutrientCard(
                "Socker",
                f"{sugar_g} g (max {sugar_max_breakfast} g)\n{sugar_g} g / {round(sugar_max_day)} g",
                (0.9, 0.3, 0.4, 1),
                image_path="../images/Socker.png"
            )
        )


        self.cards_layout.add_widget(
            NutrientCard(
                "Fett",
                f"{fat_g} g (mål {fat_min_breakfast}-{fat_max_breakfast} g)\n{fat_percent_day}% av dagsintag ({round(fat_min_day)}-{round(fat_max_day)} g)",
                (0.8, 0.5, 0.2, 1),
                image_path="../images/Fett.png"
            )
        )


        self.cards_layout.add_widget(
            NutrientCard(
                "Protein",
                f"{protein_g} g (mål {protein_min_breakfast}-{protein_max_breakfast} g)\n{protein_percent_day}% av dagsintag ({round(protein_min_day)}-{round(protein_max_day)} g)",
                (0.2, 0.6, 0.3, 1),
                image_path="../images/Protein.png"
            )
        )


    def reset_foods(self, instance):
        self.food_list = []
        self.clear_cards()
        self.input.text = ""


class FoodApp(App):
    def build(self):
        return FoodAppLayout()


FoodApp().run()