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
from kivy.clock import Clock
import Frukostdator

# Data från Excel
my_df = Frukostdator.get_excel_file()
my_foods_dict = Frukostdator.get_food_and_info(my_df)

Window.clearcolor = (0.08, 0.08, 0.1, 1)

# ---- Beräkningsfunktioner ----
def estimate_weight(age):
    if age <= 10:
        return (age + 4) * 2
    elif age <= 20:
        return (age * 3) + 7
    else:
        return 75

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

# ---- Nutrient Card ----
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

# ---- App Layout ----
class FoodAppLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=20, spacing=15, **kwargs)
        self.food_list = []
        self.gender = None
        self.selection_stage = "gender"  # stages: gender -> age -> food

        # --- Gender Input ---
        self.gender_input = TextInput(
            hint_text="Ange kön: man, kvinna, annan",
            multiline=False,
            font_size=20,
            size_hint=(1, 0.1)
        )
        self.gender_input.bind(on_text_validate=self.process_input)
        self.add_widget(self.gender_input)

        # --- Age Input ---
        self.age_input = TextInput(
            hint_text="Ange ålder (år)",
            multiline=False,
            font_size=20,
            size_hint=(1, 0.1),
            disabled=True
        )
        self.age_input.bind(on_text_validate=self.process_input)
        self.add_widget(self.age_input)

        # --- Food Input ---
        self.food_input = TextInput(
            hint_text="Skriv matvara (tomat, banan...)",
            multiline=False,
            font_size=20,
            size_hint=(1,0.1),
            disabled=True
        )
        self.food_input.bind(on_text_validate=self.process_input)
        self.add_widget(self.food_input)

        # --- Buttons ---
        self.finish_button = Button(
            text="Handlat klart",
            size_hint=(1,0.1),
            font_size=20,
            background_color=(0.3, 0.6, 1, 1)
        )
        self.finish_button.bind(on_press=self.show_food)
        self.add_widget(self.finish_button)

        self.reset_button = Button(
            text="Nollställ räknaren",
            size_hint=(1,0.1),
            font_size=20,
            background_color=(0.3, 0.6, 1, 1)
        )
        self.reset_button.bind(on_press=self.reset_foods)
        self.add_widget(self.reset_button)

        # --- Scroll och Cards ---
        self.scroll = ScrollView()
        self.cards_layout = GridLayout(cols=4, spacing=15, size_hint_y=None)
        self.cards_layout.bind(minimum_height=self.cards_layout.setter('height'))
        self.scroll.add_widget(self.cards_layout)
        self.add_widget(self.scroll)

        # --- Sätt initial fokus på kön-input ---
        Clock.schedule_once(lambda dt: setattr(self.gender_input, 'focus', True), 0.1)

    # --- Hantera Enter ---
    def process_input(self, instance):
        text = instance.text.strip()
        if self.selection_stage == "gender":
            if text.lower() in ["man", "kvinna", "annan"]:
                self.gender = text.lower()
                self.gender_input.disabled = True
                self.age_input.disabled = False
                self.age_input.focus = True
                self.selection_stage = "age"
        elif self.selection_stage == "age":
            if text.isdigit():
                self.age = int(text)
                self.age_input.disabled = True
                self.food_input.disabled = False
                self.food_input.focus = True
                self.selection_stage = "food"
        elif self.selection_stage == "food":
            self.add_food(None)

    # --- Lägg till matvara ---
    def add_food(self, instance):
        scanned_data = self.food_input.text.strip()
        if not scanned_data:
            return

        self.clear_cards()  # rensa gamla kort

        if scanned_data in my_foods_dict:
            self.food_list.append(scanned_data)
        else:
            self.cards_layout.add_widget(
                NutrientCard(
                    "Hittades inte",
                    f"{scanned_data} finns inte i databasen",
                    (0.4, 0.1, 0.1, 1)
                )
            )

        # Töm och sätt fokus igen
        self.food_input.text = ""
        Clock.schedule_once(lambda dt: setattr(self.food_input, 'focus', True), 0.05)

    # --- Visa resultat ---
    def show_food(self, instance):
        if not hasattr(self, "age") or self.gender is None:
            return
        if not self.food_list:
            self.clear_cards()
            self.cards_layout.add_widget(
                NutrientCard(
                    "Du har ej lagt till något livsmedel ännu",
                    "Lägg till livsmedel innan du avslutar",
                    (0.4, 0.1, 0.1,1)
                )
            )
            return

        result_total = Frukostdator.get_data_from_scanner(my_foods_dict, self.food_list)
        daily_kcal = get_daily_calories(self.age, self.gender)
        kcal, fat_g, protein_g, sugar_g = result_total
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

        protein_percent_day = round((protein_g / protein_max_day) * 100) if protein_max_day>0 else 0
        fat_percent_day = round((fat_g / fat_max_day) *100) if fat_max_day>0 else 0
        sugar_percent_day = round((sugar_g / sugar_max_day) *100) if sugar_max_day>0 else 0

        self.clear_cards()

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

    # --- Rensa kort ---
    def clear_cards(self):
        self.cards_layout.clear_widgets()

    def reset_foods(self, instance):
        self.food_list = []
        self.clear_cards()
        self.gender = None
        self.selection_stage = "gender"
        self.gender_input.disabled = False
        self.gender_input.text = ""
        self.age_input.disabled = True
        self.age_input.text = ""
        self.food_input.disabled = True
        self.food_input.text = ""
        Clock.schedule_once(lambda dt: setattr(self.gender_input, 'focus', True), 0.1)

# ---- App ----
class FoodApp(App):
    def build(self):
        return FoodAppLayout()

FoodApp().run()