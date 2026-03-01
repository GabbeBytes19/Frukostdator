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
import Frukostdator
my_df = Frukostdator.get_excel_file() #lstan
my_foods_dict = Frukostdator.get_food_and_info(my_df) # sortera upp info


Window.clearcolor = (0.08, 0.08, 0.1, 1)







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

        # Bilden blir väldigt liten, vet inte varför än
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

        # Bara en placeholder för input just nu
        self.input = TextInput(
            hint_text="Skriv matvara (tomat, banan, bröd)...",
            size_hint=(1, 0.1),
            font_size=20
        )
        self.add_widget(self.input)

        self.button = Button(
            text="Visa näringsinfo",
            size_hint=(1, 0.1),
            font_size=20,
            background_color=(0.3, 0.6, 1, 1)
        )
        self.button.bind(on_press=self.show_food)
        self.add_widget(self.button)

        self.scroll = ScrollView()
        self.cards_layout = GridLayout(cols=4, spacing=15, size_hint_y=None)
        self.cards_layout.bind(minimum_height=self.cards_layout.setter('height'))
        self.scroll.add_widget(self.cards_layout)

        self.add_widget(self.scroll)

    def clear_cards(self):
        self.cards_layout.clear_widgets()




##################################################################
    
    
    
     

    
    

    def show_food(self, instance):
            scanned_data = self.input.text

            result_total = Frukostdator.get_data_from_scanner(my_foods_dict,scanned_data)
            self.clear_cards()

            if scanned_data not in my_foods_dict:
                self.cards_layout.add_widget(
                    NutrientCard("Hittades inte", "Testa någon annan mat", (0.4, 0.1, 0.1, 1))
                )
                return
            print("hej")
            # Energi → meter löpning (ca 1 kcal ≈ 12 meter)
            meters = round(result_total[0] * 12)
            self.cards_layout.add_widget(
                NutrientCard(
                    "Energi",
                    f"Du kan springa ca {meters} meter",
                    (0.9, 0.6, 0.1, 1),
                    image_path="images/Energi.png"
                )
            )

            # Socker → sockerbitar (1 bit ≈ 3 g)
            sugar_cubes = round(result_total[3] / 3, 1)
            self.cards_layout.add_widget(
                NutrientCard(
                    "Socker",
                    f"{sugar_cubes} socker",
                    (0.9, 0.3, 0.4, 1),
                    image_path="images/Socker.png"
                )
            )

            # Fett → matskedar (1 msk ≈ 14 g)
            tablespoons = round(result_total[1] / 14, 2)
            self.cards_layout.add_widget(
                NutrientCard(
                    "Fett",
                    f"{tablespoons} matskedar fett",
                    (0.8, 0.5, 0.2, 1),
                    image_path="images/Fett.png"
                )
            )

            # Protein → gram
            self.cards_layout.add_widget(
                NutrientCard(
                    "Protein",
                    f" {result_total[2]} gram protein",
                    (0.2, 0.6, 0.3, 1),
                    image_path="images/Protein.png"
                )
            )


class FoodApp(App):
    def build(self):
        return FoodAppLayout()


FoodApp().run()