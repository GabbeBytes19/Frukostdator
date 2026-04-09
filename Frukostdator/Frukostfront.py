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
import destinations
import math
# Hämta data från Excel-logiken
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
        super().__init__(orientation="vertical", padding=15, size_hint_y=None, height=450, **kwargs)
        with self.canvas.before:
            Color(*color)
            self.bg = RoundedRectangle(radius=[20])
        self.bind(pos=self.update_bg, size=self.update_bg)
        self.add_widget(Label(text=title, font_size=32, bold=True))
        self.add_widget(Label(text=value_text, font_size=20, halign="center"))
        if image_path:
            try: self.add_widget(Image(source=image_path, size_hint=(1, 0.5)))
            except: pass
        self.opacity = 0
        Animation(opacity=1, duration=0.4).start(self)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

class FoodAppLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=20, spacing=15, **kwargs)
        self.food_list = []
        self.gender = None
        self.age = 0
        self.selection_stage = "gender"
        self.lst = {}
        self.distance_to_run = 0
        
        # Timer-variabler
        self.timer_seconds = 0
        self.has_pressed_button = False

        # Inputfält
        self.gender_input = TextInput(hint_text="Kön: man, kvinna, annan, vill ej ange", multiline=False, font_size=20, size_hint=(1, 0.08))
        self.gender_input.bind(on_text_validate=self.process_input)
        
        self.age_input = TextInput(hint_text="Ålder (siffror)", multiline=False, font_size=20, size_hint=(1, 0.08), disabled=True)
        self.age_input.bind(on_text_validate=self.process_input)

        self.food_input = TextInput(hint_text="Scanna livsmedel, 'reset' eller 'finish'...", multiline=False, font_size=20, size_hint=(1, 0.08), disabled=True)
        self.food_input.bind(on_text_validate=self.process_input)
        self.food_input.bind(text=self.on_food_text_change)

        self.add_widget(self.gender_input)
        self.add_widget(self.age_input)
        self.add_widget(self.food_input)

        # Knappar
        btn_layout = BoxLayout(size_hint=(1, 0.08), spacing=10)
        self.finish_button = Button(text="Finish (Visa Resultat)", background_color=(0.2, 0.6, 0.2, 1))
        self.finish_button.bind(on_press=self.show_food)
        self.reset_button = Button(text="Reset (Nollställ)", background_color=(0.6, 0.2, 0.2, 1))
        self.reset_button.bind(on_press=self.reset_foods)
        btn_layout.add_widget(self.finish_button)
        btn_layout.add_widget(self.reset_button)
        self.add_widget(btn_layout)

        self.scroll = ScrollView()
        self.cards_layout = GridLayout(cols=4, spacing=15, size_hint_y=None)
        self.cards_layout.bind(minimum_height=self.cards_layout.setter('height'))
        self.scroll.add_widget(self.cards_layout)
        self.add_widget(self.scroll)

        # Starta fokus och timern
        Clock.schedule_once(self.set_gender_focus, 0.5)
        Clock.schedule_interval(self.update_timer, 1) # Körs varje sekund

    def set_gender_focus(self, dt):
        self.gender_input.focus = True

    def set_food_focus(self, dt):
        self.food_input.focus = True

    def update_timer(self, dt):
        # Om något har hänt, nollställ klockan och vänta på nästa händelse
        if self.has_pressed_button:
            self.timer_seconds = 0
            self.has_pressed_button = False
        else:
            self.timer_seconds += 1
            
        # Om 60 sekunder gått utan aktivitet
        if self.timer_seconds >= 60:
            print("Auto-reset pga inaktivitet")
            self.reset_foods(None)

    def on_food_text_change(self, instance, value):
        scanned = value.strip().lower()
        if not scanned: return
        
        self.has_pressed_button = True # Registrera aktivitet
        
        if scanned == "reset":
            self.reset_foods(None)
        elif scanned == "finish":
            self.show_food(None)
        elif scanned in my_foods_dict:
            self.add_food()

    def process_input(self, instance):
        text = instance.text.strip().lower()
        self.has_pressed_button = True # Registrera aktivitet
        
        if self.selection_stage == "gender":
            if text in ["man", "kvinna", "annan", "vill ej ange"]:
                self.gender = text
                self.gender_input.disabled = True
                self.age_input.disabled = False
                self.clear_cards()
                Clock.schedule_once(lambda dt: setattr(self.age_input, 'focus', True), 0.1)
                self.selection_stage = "age"
            else:
                self.show_error("Ogiltigt val", "Ange: man, kvinna, annan eller vill ej ange")
                self.gender_input.text = ""
                Clock.schedule_once(self.set_gender_focus, 0.1)

        elif self.selection_stage == "age":
            if text.isdigit():
                self.age = int(text)
                self.age_input.disabled = True
                self.food_input.disabled = False
                self.clear_cards()
                Clock.schedule_once(self.set_food_focus, 0.1)
                self.selection_stage = "food"
            else:
                self.show_error("Fel format", "Ange ålder med siffror.")
                self.age_input.text = ""
                Clock.schedule_once(lambda dt: setattr(self.age_input, 'focus', True), 0.1)

        elif self.selection_stage == "food":
            if text == "reset": self.reset_foods(None)
            elif text == "finish": self.show_food(None)
            else: self.add_food()

    def add_food(self):
        scanned_data = self.food_input.text.strip().lower()
        self.has_pressed_button = True # Registrera aktivitet
        
        if not scanned_data: return
        self.clear_cards()
        if scanned_data in my_foods_dict:
            self.food_list.append(scanned_data)
            self.cards_layout.add_widget(NutrientCard("Tillagd!", f"{scanned_data.capitalize()} tillagd.", (0.1, 0.4, 0.1, 1)))
        else:
            self.show_error("Hittades inte", f"'{scanned_data}' saknas.")
        self.food_input.text = ""
        Clock.schedule_once(self.set_food_focus, 0.1)

    def show_error(self, title, msg):
        self.clear_cards()
        self.cards_layout.add_widget(NutrientCard(title, msg, (0.5, 0.1, 0.1, 1)))

  
    def get_nearast_point(self):
        self.lst = {}
        fenomenmagsinet = (58.3912, 15.5608)
        phi1 = math.radians(fenomenmagsinet[0])
        lambda1 = math.radians(fenomenmagsinet[1])
        R = 6371.0
 

        for key,value in destinations.linkoping_locations.items():
            phi2 = math.radians(value[0])
            lambda2 = math.radians(value[1])

            delta_phi = phi2 - phi1
            delta_lambda = lambda2 - lambda1

            a = math.sin(delta_phi / 2)**2 + \
                math.cos(phi1) * math.cos(phi2) * \
                math.sin(delta_lambda / 2)**2
            
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

            result = R * c

            self.lst[key] = result

        return self.lst

    def get_place(self):
        self.get_nearast_point()
        best_match = ""
        smallest_diff= 10000000
        for key,distance_to_place in self.lst.items():
            diff = abs(self.distance_in_km - distance_to_place)
            if diff < smallest_diff:
                smallest_diff = diff
                best_match = key
        return best_match



    def show_food(self, instance):
        self.has_pressed_button = True # Registrera aktivitet
        self.food_input.text = ""
        if not self.food_list:
            self.show_error("Tom lista", "Scanna livsmedel först.")
            Clock.schedule_once(self.set_food_focus, 0.1)
            return
        
        res = Frukostdator.get_data_from_scanner(my_foods_dict, self.food_list)
        self.clear_cards()

        


        self.clear_cards()

        daily_kcal = get_daily_calories(self.age, self.gender)

        kcal = res[0]
        fat_g = res[1]
        protein_g = res[2]
        sugar_g = res[3]

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
        


        self.distance_to_run = 1000 * kcal / estimate_weight(self.age)
        dimension = "meter"
        self.distance_in_km = self.distance_to_run / 1000

        if self.distance_to_run >10000:
            self.distance_to_run = round(self.distance_to_run / 10000,2)
            dimension = "mil"
        elif self.distance_to_run > 1000:
            self.distance_to_run = round(self.distance_to_run/1000,2)
            dimension = "km"
        

     




        self.cards_layout.add_widget(
            NutrientCard(
                "Energi",
                f"{kcal} kcal (mål {kcal_min_breakfast}-{kcal_max_breakfast} kcal)\n{percent}% av dagsintag ({round(daily_kcal)})\n Du kan springa {self.distance_to_run} {dimension}, detta är till {self.get_place()} ",
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

        Clock.schedule_once(self.set_food_focus, 0.5)

    def clear_cards(self):
        self.cards_layout.clear_widgets()

    def reset_foods(self, instance):
        self.food_list = []
        self.clear_cards()
        self.selection_stage = "gender"
        self.timer_seconds = 0
        self.has_pressed_button = False # Nollställ flaggan vid reset
        
        self.gender_input.disabled = False
        self.gender_input.text = ""
        self.age_input.disabled = True
        self.age_input.text = ""
        self.food_input.disabled = True
        self.food_input.text = ""
        Clock.schedule_once(self.set_gender_focus, 0.5)

class FoodApp(App):
    def build(self):
        return FoodAppLayout()

if __name__ == "__main__":
    FoodApp().run()
