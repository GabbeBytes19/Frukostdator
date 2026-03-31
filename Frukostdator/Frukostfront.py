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

# Hämta data från Excel-logiken
my_df = Frukostdator.get_excel_file()
my_foods_dict = Frukostdator.get_food_and_info(my_df)

Window.clearcolor = (0.08, 0.08, 0.1, 1)

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
                self.show_error("Ogiltigt val", "Skriv: man, kvinna, annan eller vill ej ange")
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

    def show_food(self, instance):
        self.has_pressed_button = True # Registrera aktivitet
        self.food_input.text = ""
        if not self.food_list:
            self.show_error("Tom lista", "Scanna livsmedel först.")
            Clock.schedule_once(self.set_food_focus, 0.1)
            return
        
        res = Frukostdator.get_data_from_scanner(my_foods_dict, self.food_list)
        self.clear_cards()
        self.cards_layout.add_widget(NutrientCard("Energi", f"{round(res[0])} kcal", (0.9, 0.6, 0.1, 1)))
        self.cards_layout.add_widget(NutrientCard("Socker", f"{round(res[3], 1)} g", (0.9, 0.3, 0.4, 1)))
        self.cards_layout.add_widget(NutrientCard("Fett", f"{round(res[1], 1)} g", (0.8, 0.5, 0.2, 1)))
        self.cards_layout.add_widget(NutrientCard("Protein", f"{round(res[2], 1)} g", (0.2, 0.6, 0.3, 1)))
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