from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.gridlayout import GridLayout
from kivy.uix.progressbar import ProgressBar
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Ellipse, Rectangle, Line
from kivy.core.text import Label as CoreLabel
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
    def __init__(self, title, value_text, color, status_text="", progress_val=0, show_progress=False, image_path=None, **kwargs):
        super().__init__(orientation="vertical", padding=[15, 12, 15, 12], spacing=6, size_hint_y=None, height=500, **kwargs)
        with self.canvas.before:
            Color(*color)
            self.bg = RoundedRectangle(radius=[20])
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.add_widget(Label(text=title, font_size=34, bold=True, size_hint_y=None, height=48))

        if status_text:
            self.add_widget(Label(text=status_text, font_size=26, bold=True, size_hint_y=None, height=40))

        if show_progress:
            self.add_widget(ProgressBar(max=100, value=min(progress_val, 100), size_hint=(1, None), height=26))

        lbl = Label(text=value_text, font_size=18, halign="center", valign="top", size_hint_y=None, height=220)
        lbl.bind(size=lambda *a: setattr(lbl, 'text_size', lbl.size))
        self.add_widget(lbl)

        if image_path:
            try: self.add_widget(Image(source=image_path, size_hint=(1, None), height=80))
            except: pass

        self.opacity = 0
        Animation(opacity=1, duration=0.4).start(self)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

class _SugarCubesDisplay(Widget):
    """Draws a grid of sugar-cube squares. Green = within daily max, red = over."""
    def __init__(self, actual_cubes, daily_max_cubes, **kwargs):
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', 260)
        super().__init__(**kwargs)
        self.actual = max(actual_cubes, 0)
        self.daily_max = max(daily_max_cubes, 1)
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *args):
        self.canvas.clear()
        cube_sz = 32
        gap = 5
        per_row = max(1, int((self.width - gap) / (cube_sz + gap)))
        total = max(self.actual, self.daily_max)

        with self.canvas:
            for i in range(total):
                col = i % per_row
                row = i // per_row
                x = self.x + gap + col * (cube_sz + gap)
                y = self.y + self.height - gap - (row + 1) * (cube_sz + gap)
                if y < self.y:
                    break
                if i < self.actual and i < self.daily_max:
                    Color(0.15, 0.75, 0.25, 1)   # green: consumed, within limit
                elif i < self.actual:
                    Color(0.85, 0.15, 0.1, 1)    # red: consumed but over limit
                else:
                    Color(0.22, 0.22, 0.26, 1)   # dark grey: not consumed
                RoundedRectangle(pos=(x, y), size=(cube_sz, cube_sz), radius=[5])

            # Vertical line after the daily_max-th cube
            max_col = self.daily_max % per_row
            max_row = self.daily_max // per_row
            line_x = self.x + gap + max_col * (cube_sz + gap) - gap // 2 - 1
            line_y_top = self.y + self.height - gap - max_row * (cube_sz + gap) + gap
            line_y_bot = self.y + 4
            Color(1, 1, 1, 0.85)
            Line(points=[line_x, line_y_top, line_x, line_y_bot], width=2.5)

            # "Max" label drawn as texture
            core_lbl = CoreLabel(text="Max", font_size=14, bold=True)
            core_lbl.refresh()
            tex = core_lbl.texture
            Color(1, 1, 1, 0.85)
            Rectangle(texture=tex,
                      pos=(line_x - tex.width // 2, self.y + self.height - tex.height - 2),
                      size=tex.size)


class SugarCubesCard(BoxLayout):
    def __init__(self, sugar_g, sugar_max_breakfast_g, sugar_max_day_g, **kwargs):
        super().__init__(orientation="vertical", padding=[15, 12, 15, 12], spacing=5,
                         size_hint_y=None, height=500, **kwargs)

        actual_cubes = round(sugar_g / 4)
        max_breakfast_cubes = max(round(sugar_max_breakfast_g / 4), 1)
        daily_max_cubes = max(round(sugar_max_day_g / 4), 1)

        if sugar_g <= sugar_max_breakfast_g * 0.5:
            status, card_color = "Jattebra!", (0.08, 0.45, 0.15, 1)
        elif sugar_g <= sugar_max_breakfast_g:
            status, card_color = "Bra!", (0.1, 0.38, 0.12, 1)
        elif sugar_g <= sugar_max_breakfast_g * 1.3:
            status, card_color = "~ Okej", (0.5, 0.32, 0.04, 1)
        else:
            status, card_color = "! For mycket", (0.5, 0.08, 0.08, 1)

        with self.canvas.before:
            Color(*card_color)
            self.bg = RoundedRectangle(radius=[20])
        self.bind(pos=self._upd, size=self._upd)

        self.add_widget(Label(text="Socker", font_size=34, bold=True, size_hint_y=None, height=48))
        self.add_widget(Label(text=status, font_size=24, bold=True, size_hint_y=None, height=36))

        sub = Label(
            text=f"{actual_cubes} sockerbitar (max {max_breakfast_cubes}/frukost  |  {daily_max_cubes}/dag)",
            font_size=15, halign="center", size_hint_y=None, height=30
        )
        sub.bind(size=lambda *a: setattr(sub, 'text_size', sub.size))
        self.add_widget(sub)

        self.add_widget(_SugarCubesDisplay(actual_cubes=actual_cubes, daily_max_cubes=daily_max_cubes))

        self.opacity = 0
        Animation(opacity=1, duration=0.4).start(self)

    def _upd(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size


class _CircleDisplay(Widget):
    """Draws a solid colored circle with centered text."""
    def __init__(self, color, line1, line2, **kwargs):
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', 260)
        super().__init__(**kwargs)
        self.circle_color = color
        self.line1 = line1
        self.line2 = line2
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *args):
        self.canvas.clear()
        r = min(self.width, self.height) / 2 - 12
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2

        with self.canvas:
            Color(0.1, 0.1, 0.12, 1)
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
            Color(*self.circle_color)
            ir = r - 10
            Ellipse(pos=(cx - ir, cy - ir), size=(ir * 2, ir * 2))

            # Line 1 (large value)
            lbl1 = CoreLabel(text=self.line1, font_size=26, bold=True, halign='center')
            lbl1.refresh()
            t1 = lbl1.texture
            Color(1, 1, 1, 1)
            Rectangle(texture=t1, pos=(cx - t1.width / 2, cy + 4), size=t1.size)

            # Line 2 (small label)
            lbl2 = CoreLabel(text=self.line2, font_size=16, halign='center')
            lbl2.refresh()
            t2 = lbl2.texture
            Rectangle(texture=t2, pos=(cx - t2.width / 2, cy - t2.height - 2), size=t2.size)


class CircleNutrientCard(BoxLayout):
    def __init__(self, title, value_g, min_g, max_g, unit="g", fun_text="", **kwargs):
        super().__init__(orientation="vertical", padding=[15, 12, 15, 12], spacing=5,
                         size_hint_y=None, height=500, **kwargs)

        if value_g < min_g * 0.5:
            status, card_color = "For lite!", (0.5, 0.08, 0.08, 1)
        elif value_g < min_g:
            status, card_color = "~ Lite lite", (0.5, 0.32, 0.04, 1)
        elif value_g <= max_g:
            status, card_color = "Bra!", (0.08, 0.42, 0.14, 1)
        elif value_g <= max_g * 1.4:
            status, card_color = "~ Lite mycket", (0.5, 0.32, 0.04, 1)
        else:
            status, card_color = "! For mycket", (0.5, 0.08, 0.08, 1)

        with self.canvas.before:
            Color(*card_color)
            self.bg = RoundedRectangle(radius=[20])
        self.bind(pos=self._upd, size=self._upd)

        self.add_widget(Label(text=title, font_size=34, bold=True, size_hint_y=None, height=48))
        self.add_widget(Label(text=status, font_size=24, bold=True, size_hint_y=None, height=36))

        circle_line1 = f"{value_g}{unit}"
        circle_line2 = f"mal {min_g}-{max_g}{unit}"
        self.add_widget(_CircleDisplay(color=card_color, line1=circle_line1, line2=circle_line2))

        if fun_text:
            sub = Label(text=fun_text, font_size=15, halign="center", size_hint_y=None, height=40)
            sub.bind(size=lambda *a: setattr(sub, 'text_size', sub.size))
            self.add_widget(sub)

        self.opacity = 0
        Animation(opacity=1, duration=0.4).start(self)

    def _upd(self, *args):
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
        self.finish_button = Button(text="Beräkna", background_color=(0.2, 0.6, 0.2, 1))
        self.finish_button.bind(on_press=self.show_food)
        self.new_breakfast_button = Button(text="Ny frukost", background_color=(0.2, 0.4, 0.8, 1))
        self.new_breakfast_button.bind(on_press=self.new_breakfast)
        self.reset_button = Button(text="Reset (Nollställ)", background_color=(0.6, 0.2, 0.2, 1))
        self.reset_button.bind(on_press=self.reset_foods)
        btn_layout.add_widget(self.finish_button)
        btn_layout.add_widget(self.new_breakfast_button)
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
        
        fenomenmagsinet = (58.3912, 15.5608)
        phi1 = math.radians(fenomenmagsinet[0])
        lambda1 = math.radians(fenomenmagsinet[1])
        R = 6371.0
 

        for key,value in destinations.linkoping_locations.items():
            phi2 = value[0]
            lambda2 = value[1]
            delta_phi = math.radians(phi2 - phi1)
            delta_lambda = math.radians(lambda2 - lambda1)

            #Haversine beräkning
            a = math.sin(delta_phi / 2)**2 + \
                math.cos(phi1) * math.cos(phi2) * \
                math.sin(delta_lambda / 2)**2
            
            c= 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

            result = c * R

            self.lst[key] = result

        return self.lst

    def get_place(self):
        self.get_nearast_point()
        best_match = ""
        smallest_diff= 10000000
        for key,distance_to_place in self.lst.items():
            diff = abs(self.distance_to_run - distance_to_place)
            if diff < smallest_diff:
                smallest_diff = diff
                best_match = key
        return best_match



    def _get_status(self, value, min_val, max_val, invert=False):
        """Returns (status_text, card_color, progress_percent).
        invert=True means lower is better (e.g. sugar)."""
        progress = min(round((value / max_val) * 100), 100) if max_val > 0 else 0
        if invert:
            if value <= max_val * 0.5:
                return "Jattebra!", (0.1, 0.55, 0.2, 1), progress
            elif value <= max_val:
                return "Bra!", (0.15, 0.5, 0.15, 1), progress
            elif value <= max_val * 1.3:
                return "~ Okej", (0.65, 0.4, 0.05, 1), progress
            else:
                return "! For mycket", (0.65, 0.1, 0.1, 1), progress
        else:
            progress = min(round((value / max_val) * 100), 100) if max_val > 0 else 0
            if value < min_val * 0.5:
                return "For lite!", (0.55, 0.35, 0.05, 1), progress
            elif value < min_val:
                return "~ Lite lite", (0.65, 0.4, 0.05, 1), progress
            elif value <= max_val:
                return "Bra!", (0.1, 0.55, 0.2, 1), progress
            elif value <= max_val * 1.3:
                return "~ Lite mycket", (0.65, 0.4, 0.05, 1), progress
            else:
                return "! For mycket", (0.65, 0.1, 0.1, 1), progress

    def show_food(self, instance):
        self.has_pressed_button = True # Registrera aktivitet
        self.food_input.text = ""
        if not self.food_list:
            self.show_error("Tom lista", "Scanna livsmedel först.")
            Clock.schedule_once(self.set_food_focus, 0.1)
            return
        
        res = Frukostdator.get_data_from_scanner(my_foods_dict, self.food_list)
        self.clear_cards()

        

        age = int(self.age)

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
        sugar_percent_day = round((sugar_g / sugar_max_day) * 100) if sugar_max_day > 0 else 0
        


        self.distance_to_run = 10000000 * kcal / estimate_weight(self.age)
        dimension = "meter"
        if self.distance_to_run > 1000:
            self.distance_to_run = round(self.distance_to_run/1000,2)
            dimension = "km"
        if self.distance_to_run >10000:
            self.distance_to_run = round(self.distance_to_run / 10000,2)
            dimension = "mil"

     




        energy_status, energy_color, energy_prog = self._get_status(kcal, kcal_min_breakfast, kcal_max_breakfast)
        nearest = self.get_place()
        self.cards_layout.add_widget(
            NutrientCard(
                "Energi",
                f"{kcal} kcal\nMal: {kcal_min_breakfast}-{kcal_max_breakfast} kcal\n{percent}% av dagsintaget\nDu kan springa {self.distance_to_run} {dimension}\n(till {nearest}!)",
                energy_color,
                status_text=energy_status,
                progress_val=energy_prog,
                show_progress=True,
                image_path="../images/Energi.png"
            )
        )


        self.cards_layout.add_widget(
            SugarCubesCard(
                sugar_g=sugar_g,
                sugar_max_breakfast_g=sugar_max_breakfast,
                sugar_max_day_g=sugar_max_day
            )
        )







        

        tablespoons = round(fat_g / 14, 1)
        self.cards_layout.add_widget(
            CircleNutrientCard(
                title="Fett",
                value_g=fat_g,
                min_g=fat_min_breakfast,
                max_g=fat_max_breakfast,
                fun_text=f"= {tablespoons} matskedar"
            )
        )

        eggs = round(protein_g / 6, 1)
        self.cards_layout.add_widget(
            CircleNutrientCard(
                title="Protein",
                value_g=protein_g,
                min_g=protein_min_breakfast,
                max_g=protein_max_breakfast,
                fun_text=f"= {eggs} agg  (bygger muskler!)"
            )
        )

        Clock.schedule_once(self.set_food_focus, 0.5)

    def clear_cards(self):
        self.cards_layout.clear_widgets()

    def new_breakfast(self, instance):
        self.food_list = []
        self.clear_cards()
        self.food_input.text = ""
        self.food_input.disabled = False
        self.selection_stage = "food"
        self.timer_seconds = 0
        self.has_pressed_button = True
        Clock.schedule_once(self.set_food_focus, 0.1)

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










   








      

