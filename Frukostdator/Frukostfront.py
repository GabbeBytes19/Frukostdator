import math

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.graphics import (
    Color, RoundedRectangle, Ellipse, Line, Rectangle
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

import destinations
import Frukostdator

my_df = Frukostdator.get_excel_file()
my_foods_dict = Frukostdator.get_food_and_info(my_df)

Window.clearcolor = (0.06, 0.07, 0.10, 1)

# ── palette ──────────────────────────────────────────────────────────────────
C_BG        = (0.06, 0.07, 0.10, 1)
C_CARD      = (0.10, 0.11, 0.16, 1)
C_CARD2     = (0.13, 0.14, 0.20, 1)
C_ACCENT    = (0.30, 0.85, 0.55, 1)
C_TEXT      = (0.95, 0.95, 0.95, 1)
C_MUTED     = (0.50, 0.52, 0.62, 1)
C_KCAL      = (1.00, 0.72, 0.20, 1)
C_SUGAR_OK  = (0.25, 0.80, 0.50, 1)
C_SUGAR_BAD = (0.95, 0.30, 0.35, 1)
C_FAT       = (1.00, 0.60, 0.15, 1)
C_PROTEIN   = (0.35, 0.65, 1.00, 1)
C_DIST      = (0.65, 0.45, 1.00, 1)

INPUT_STYLE = dict(
    multiline=False,
    font_size=20,
    size_hint=(1, 0.08),
    background_color=(0.11, 0.11, 0.18, 1),
    foreground_color=(0.95, 0.95, 0.95, 1),
    cursor_color=C_ACCENT,
    hint_text_color=(0.38, 0.40, 0.52, 1),
    padding=[16, 14, 16, 14],
)


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
            male, female = 2800, 2200
        elif age <= 50:
            male, female = 2700, 2200
        elif age <= 70:
            male, female = 2500, 2000
        else:
            male, female = 2400, 2000

    if gender == "man":
        return male
    elif gender == "kvinna":
        return female
    else:
        return (male + female) / 2


def _status(value, lo, hi):
    """Return (label, color) based on whether value is low/ok/high."""
    if value < lo:
        return "FOR LITE", (1.0, 0.75, 0.20, 1)
    elif value <= hi:
        return "BRA!", C_SUGAR_OK
    else:
        return "FOR MYCKET", C_SUGAR_BAD


# ─────────────────────────────────────────────────────────────────────────────
#  PillButton
# ─────────────────────────────────────────────────────────────────────────────
class PillButton(Button):
    def __init__(self, btn_color=C_ACCENT, **kwargs):
        kwargs.setdefault('background_color', (0, 0, 0, 0))
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_down', '')
        kwargs.setdefault('color', (0.05, 0.06, 0.09, 1))
        kwargs.setdefault('bold', True)
        kwargs.setdefault('font_size', 18)
        super().__init__(**kwargs)
        self._btn_color = btn_color
        with self.canvas.before:
            self._col_inst = Color(*btn_color)
            self._bg = RoundedRectangle(radius=[24])
        self.bind(pos=self._upd, size=self._upd)
        self.bind(on_press=self._press, on_release=self._release)

    def _upd(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def _press(self, *_):
        r, g, b, a = self._btn_color
        self._col_inst.rgba = (r * 0.75, g * 0.75, b * 0.75, a)

    def _release(self, *_):
        self._col_inst.rgba = self._btn_color


# ─────────────────────────────────────────────────────────────────────────────
#  NutrientCard  (generic — used for Energi, Distans, errors)
# ─────────────────────────────────────────────────────────────────────────────
class NutrientCard(BoxLayout):
    def __init__(self, title, value_text, color, image_path=None, **kwargs):
        super().__init__(
            orientation="vertical", padding=18, spacing=8,
            size_hint_y=None, height=400, **kwargs
        )
        # shadow
        with self.canvas.before:
            Color(0, 0, 0, 0.45)
            self._shadow = RoundedRectangle(radius=[22])
            Color(*color)
            self._bg = RoundedRectangle(radius=[20])
        self.bind(pos=self._upd, size=self._upd)

        self.add_widget(Label(
            text=title, font_size=30, bold=True,
            color=C_TEXT, size_hint_y=None, height=44
        ))
        # divider
        div = Widget(size_hint_y=None, height=2)
        with div.canvas:
            Color(1, 1, 1, 0.12)
            self._div_rect = Rectangle(size=(self.width, 2))
        div.bind(pos=lambda w, p: setattr(self._div_rect, 'pos', p),
                 size=lambda w, s: setattr(self._div_rect, 'size', s))
        self.add_widget(div)

        self.add_widget(Label(
            text=value_text, font_size=17,
            halign="center", valign="middle",
            color=C_TEXT, text_size=(None, None)
        ))
        if image_path:
            try:
                self.add_widget(Image(source=image_path, size_hint=(1, 0.45)))
            except Exception:
                pass
        self.opacity = 0
        Animation(opacity=1, duration=0.35).start(self)

    def _upd(self, *_):
        ox, oy = 5, -5
        self._shadow.pos  = (self.x + ox, self.y + oy)
        self._shadow.size = self.size
        self._bg.pos      = self.pos
        self._bg.size     = self.size


# ─────────────────────────────────────────────────────────────────────────────
#  3-D Sugar Cubes
# ─────────────────────────────────────────────────────────────────────────────
class _SugarCubesDisplay(Widget):
    """Draws 3-D sugar cubes.  Green = consumed (ok), Red = over limit,
    dark = budget remaining.  A dashed MAX line shows the limit."""

    def __init__(self, consumed_g, max_g, **kwargs):
        super().__init__(size_hint_y=None, height=220, **kwargs)
        self.consumed_g = consumed_g
        self.max_g      = max_g
        self.bind(size=self._draw, pos=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        w, h   = self.size
        ox, oy = self.pos

        G_PER_CUBE = 3.0
        total_cubes = max(1, math.ceil(max(self.consumed_g, self.max_g) / G_PER_CUBE) + 2)
        consumed_cubes = self.consumed_g / G_PER_CUBE
        max_cubes      = self.max_g      / G_PER_CUBE

        CUBE  = min(40, (w - 40) / max(total_cubes, 1))
        GAP   = CUBE * 0.22
        DEPTH = CUBE * 0.28
        cols  = max(1, int((w - 20) // (CUBE + GAP)))
        rows  = math.ceil(total_cubes / cols)

        base_x = ox + (w - cols * (CUBE + GAP) + GAP) / 2
        base_y = oy + h - CUBE - DEPTH - 24

        with self.canvas:
            for i in range(math.ceil(total_cubes)):
                col_i = i % cols
                row_i = i // cols
                cx = base_x + col_i * (CUBE + GAP)
                cy = base_y - row_i * (CUBE + GAP + DEPTH * 0.5)

                if i < consumed_cubes:
                    if i < max_cubes:
                        face   = C_SUGAR_OK
                        side_t = (face[0]*0.55, face[1]*0.55, face[2]*0.55, 1)
                        top_c  = (face[0]*0.85, face[1]*0.85, face[2]*0.85, 1)
                    else:
                        face   = C_SUGAR_BAD
                        side_t = (face[0]*0.55, face[1]*0.55, face[2]*0.55, 1)
                        top_c  = (face[0]*0.85, face[1]*0.85, face[2]*0.85, 1)
                else:
                    face   = (0.18, 0.19, 0.26, 1)
                    side_t = (0.12, 0.13, 0.18, 1)
                    top_c  = (0.22, 0.23, 0.30, 1)

                # shadow base
                Color(0, 0, 0, 0.30)
                Rectangle(pos=(cx + 4, cy - 4), size=(CUBE, CUBE))
                # front face
                Color(*face)
                Rectangle(pos=(cx, cy), size=(CUBE, CUBE))
                # top face (parallelogram via two triangles approximated as rectangle)
                Color(*top_c)
                Rectangle(pos=(cx + DEPTH * 0.6, cy + CUBE - DEPTH * 0.3),
                          size=(CUBE, DEPTH * 0.7))
                # right side face
                Color(*side_t)
                Rectangle(pos=(cx + CUBE, cy + DEPTH * 0.4),
                          size=(DEPTH * 0.7, CUBE - DEPTH * 0.4))
                # gloss sheen
                Color(1, 1, 1, 0.10)
                Rectangle(pos=(cx + 3, cy + CUBE - 9), size=(CUBE - 6, 6))

            # MAX dashed line
            max_col = int(max_cubes) % cols
            max_row = int(max_cubes) // cols
            line_x  = base_x + max_col * (CUBE + GAP) - GAP * 0.5
            line_y  = base_y - max_row * (CUBE + GAP + DEPTH * 0.5) - GAP * 0.5

            Color(0.95, 0.30, 0.35, 0.85)
            Line(points=[ox + 10, line_y + CUBE + 4, ox + w - 10, line_y + CUBE + 4],
                 width=1.8, dash_length=6, dash_offset=4)

            # "MAX" label via CoreLabel texture
            lbl = CoreLabel(text="MAX", font_size=13, bold=True)
            lbl.refresh()
            tex = lbl.texture
            Color(0.95, 0.30, 0.35, 1)
            Rectangle(texture=tex,
                      pos=(ox + w - tex.width - 8, line_y + CUBE + 6),
                      size=tex.size)


class SugarCubesCard(BoxLayout):
    def __init__(self, consumed_g, max_g, **kwargs):
        super().__init__(
            orientation="vertical", padding=16, spacing=8,
            size_hint_y=None, height=420, **kwargs
        )
        with self.canvas.before:
            Color(0, 0, 0, 0.40)
            self._sh = RoundedRectangle(radius=[22])
            Color(0.95, 0.30, 0.35, 1)
            self._bg = RoundedRectangle(radius=[20])
        self.bind(pos=self._upd, size=self._upd)

        status_lbl, status_col = _status(consumed_g, 0.001, max_g)

        self.add_widget(Label(
            text="Socker", font_size=30, bold=True,
            color=C_TEXT, size_hint_y=None, height=40
        ))
        div = Widget(size_hint_y=None, height=2)
        with div.canvas:
            Color(1, 1, 1, 0.15)
            self._dr = Rectangle(size=(self.width, 2))
        div.bind(pos=lambda w, p: setattr(self._dr, 'pos', p),
                 size=lambda w, s: setattr(self._dr, 'size', s))
        self.add_widget(div)

        self.add_widget(Label(
            text=status_lbl, font_size=16, bold=True,
            color=status_col, size_hint_y=None, height=22
        ))
        self.add_widget(Label(
            text=f"{round(consumed_g, 1)} g  /  max {round(max_g)} g",
            font_size=14, color=(1, 1, 1, 0.70), size_hint_y=None, height=20
        ))
        self.add_widget(_SugarCubesDisplay(consumed_g, max_g))
        self.opacity = 0
        Animation(opacity=1, duration=0.40).start(self)

    def _upd(self, *_):
        self._sh.pos  = (self.x + 5, self.y - 5)
        self._sh.size = self.size
        self._bg.pos  = self.pos
        self._bg.size = self.size


# ─────────────────────────────────────────────────────────────────────────────
#  Circle progress widget
# ─────────────────────────────────────────────────────────────────────────────
class _CircleDisplay(Widget):
    def __init__(self, value_g, lo_g, hi_g, color, unit="g", **kwargs):
        super().__init__(size_hint_y=None, height=220, **kwargs)
        self.value_g = value_g
        self.lo_g    = lo_g
        self.hi_g    = hi_g
        self.color   = color
        self.unit    = unit
        self.bind(size=self._draw, pos=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        w, h   = self.size
        cx     = self.x + w / 2
        cy     = self.y + h / 2
        R      = min(w, h) * 0.38
        thick  = R * 0.22

        pct = min(self.value_g / self.hi_g, 1.5) if self.hi_g > 0 else 0
        arc = pct * 360

        with self.canvas:
            # track ring
            Color(0.18, 0.19, 0.27, 1)
            Line(circle=(cx, cy, R), width=thick)

            # progress arc (clockwise from top = 90 deg)
            if arc > 0:
                if self.value_g <= self.hi_g:
                    Color(*self.color)
                else:
                    Color(*C_SUGAR_BAD)
                start = 90
                end   = 90 - arc
                Line(ellipse=(cx - R, cy - R, R * 2, R * 2, end, start),
                     width=thick)

            # inner filled circle
            inner_r = R - thick * 0.5
            Color(0.10, 0.11, 0.16, 1)
            Ellipse(pos=(cx - inner_r, cy - inner_r),
                    size=(inner_r * 2, inner_r * 2))

            # subtle inner tint
            r, g, b, a = self.color
            Color(r, g, b, 0.06)
            Ellipse(pos=(cx - inner_r, cy - inner_r),
                    size=(inner_r * 2, inner_r * 2))

            # value text
            val_lbl = CoreLabel(
                text=f"{round(self.value_g, 1)}{self.unit}",
                font_size=int(inner_r * 0.55), bold=True
            )
            val_lbl.refresh()
            t = val_lbl.texture
            Color(*C_TEXT)
            Rectangle(texture=t,
                      pos=(cx - t.width / 2, cy - t.height / 2 + inner_r * 0.18),
                      size=t.size)

            # range text
            rng_lbl = CoreLabel(
                text=f"{round(self.lo_g)}-{round(self.hi_g)} g",
                font_size=int(inner_r * 0.28)
            )
            rng_lbl.refresh()
            rt = rng_lbl.texture
            Color(*C_MUTED)
            Rectangle(texture=rt,
                      pos=(cx - rt.width / 2, cy - rt.height / 2 - inner_r * 0.22),
                      size=rt.size)

            # percentage chip
            pct_lbl = CoreLabel(
                text=f"{round(pct * 100)}%",
                font_size=int(inner_r * 0.30), bold=True
            )
            pct_lbl.refresh()
            pt = pct_lbl.texture
            chip_pad = 6
            chip_w = pt.width + chip_pad * 2
            chip_h = pt.height + chip_pad
            Color(*self.color[:3], 0.20)
            RoundedRectangle(
                pos=(cx - chip_w / 2, self.y + 14),
                size=(chip_w, chip_h),
                radius=[chip_h / 2]
            )
            Color(*self.color)
            Rectangle(texture=pt,
                      pos=(cx - pt.width / 2, self.y + 14 + chip_pad // 2),
                      size=pt.size)


class CircleNutrientCard(BoxLayout):
    def __init__(self, title, value_g, lo_g, hi_g, color, fun_text="", **kwargs):
        super().__init__(
            orientation="vertical", padding=16, spacing=6,
            size_hint_y=None, height=420, **kwargs
        )
        with self.canvas.before:
            Color(0, 0, 0, 0.40)
            self._sh = RoundedRectangle(radius=[22])
            Color(*C_CARD)
            self._bg = RoundedRectangle(radius=[20])
        self.bind(pos=self._upd, size=self._upd)

        status_lbl, status_col = _status(value_g, lo_g, hi_g)

        self.add_widget(Label(
            text=title, font_size=30, bold=True,
            color=C_TEXT, size_hint_y=None, height=40
        ))
        div = Widget(size_hint_y=None, height=2)
        with div.canvas:
            Color(1, 1, 1, 0.12)
            self._dr = Rectangle(size=(self.width, 2))
        div.bind(pos=lambda w, p: setattr(self._dr, 'pos', p),
                 size=lambda w, s: setattr(self._dr, 'size', s))
        self.add_widget(div)

        self.add_widget(Label(
            text=status_lbl, font_size=16, bold=True,
            color=status_col, size_hint_y=None, height=22
        ))
        self.add_widget(_CircleDisplay(value_g, lo_g, hi_g, color))
        if fun_text:
            self.add_widget(Label(
                text=fun_text, font_size=13,
                color=(1, 1, 1, 0.60), halign="center",
                size_hint_y=None, height=22
            ))
        self.opacity = 0
        Animation(opacity=1, duration=0.40).start(self)

    def _upd(self, *_):
        self._sh.pos  = (self.x + 5, self.y - 5)
        self._sh.size = self.size
        self._bg.pos  = self.pos
        self._bg.size = self.size


# ─────────────────────────────────────────────────────────────────────────────
#  Running man animation
# ─────────────────────────────────────────────────────────────────────────────
class RunningMan(Image):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.frames      = ["run_1.png", "run_2.png", "run_3.png", "run_4.png"]
        self.frame_index = 0
        self.anim_event  = None
        self.source      = self.frames[0]

    def start(self, speed):
        self.anim_event = Clock.schedule_interval(self.next_frame, speed)

    def next_frame(self, dt):
        self.frame_index = (self.frame_index + 1) % len(self.frames)
        self.source      = self.frames[self.frame_index]

    def stop(self):
        if self.anim_event:
            self.anim_event.cancel()


# ─────────────────────────────────────────────────────────────────────────────
#  Main layout
# ─────────────────────────────────────────────────────────────────────────────
class FoodAppLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=20, spacing=12, **kwargs)
        self.food_list       = []
        self.gender          = None
        self.age             = 0
        self.selection_stage = "gender"
        self.lst             = {}
        self.distance_to_run = 0
        self.timer_seconds   = 0
        self.has_pressed_button = False

        # ── inputs ──────────────────────────────────────────────────────────
        self.gender_input = TextInput(
            hint_text="Kon: man, kvinna, annan, vill ej ange",
            **INPUT_STYLE
        )
        self.gender_input.bind(on_text_validate=self.process_input)

        self.age_input = TextInput(
            hint_text="Alder (siffror)",
            disabled=True,
            **INPUT_STYLE
        )
        self.age_input.bind(on_text_validate=self.process_input)

        self.food_input = TextInput(
            hint_text="Scanna livsmedel, 'reset' eller 'berakna'...",
            disabled=True,
            **INPUT_STYLE
        )
        self.food_input.bind(on_text_validate=self.process_input)
        self.food_input.bind(text=self.on_food_text_change)

        self.add_widget(self.gender_input)
        self.add_widget(self.age_input)
        self.add_widget(self.food_input)

        # ── buttons ─────────────────────────────────────────────────────────
        btn_layout = BoxLayout(size_hint=(1, 0.09), spacing=10)

        self.calc_button = PillButton(
            text="Berakna",
            btn_color=C_ACCENT,
        )
        self.calc_button.bind(on_press=self.show_food)

        self.new_btn = PillButton(
            text="Ny frukost",
            btn_color=C_DIST,
        )
        self.new_btn.bind(on_press=self.new_breakfast)

        self.reset_button = PillButton(
            text="Reset",
            btn_color=C_SUGAR_BAD,
        )
        self.reset_button.bind(on_press=self.reset_foods)

        btn_layout.add_widget(self.calc_button)
        btn_layout.add_widget(self.new_btn)
        btn_layout.add_widget(self.reset_button)
        self.add_widget(btn_layout)

        # ── scroll / cards ───────────────────────────────────────────────────
        self.scroll = ScrollView()
        self.cards_layout = GridLayout(cols=3, spacing=16, size_hint_y=None)
        self.cards_layout.bind(minimum_height=self.cards_layout.setter("height"))
        self.scroll.add_widget(self.cards_layout)
        self.add_widget(self.scroll)

        Clock.schedule_once(self.set_gender_focus, 0.5)
        Clock.schedule_interval(self.update_timer, 1)

    # ── focus helpers ────────────────────────────────────────────────────────
    def set_gender_focus(self, dt):
        self.gender_input.focus = True

    def set_food_focus(self, dt):
        self.food_input.focus = True

    # ── timer ────────────────────────────────────────────────────────────────
    def update_timer(self, dt):
        if self.has_pressed_button:
            self.timer_seconds      = 0
            self.has_pressed_button = False
        else:
            self.timer_seconds += 1
        if self.timer_seconds >= 60:
            print("Auto-reset pga inaktivitet")
            self.reset_foods(None)

    # ── live scan handler ────────────────────────────────────────────────────
    def on_food_text_change(self, instance, value):
        scanned = value.strip().lower()
        if not scanned:
            return
        self.has_pressed_button = True
        if scanned == "reset":
            self.reset_foods(None)
        elif scanned in ("berakna", "finish"):
            self.show_food(None)
        elif scanned in my_foods_dict:
            self.add_food()

    # ── input processing ─────────────────────────────────────────────────────
    def process_input(self, instance):
        text = instance.text.strip().lower()
        self.has_pressed_button = True

        if self.selection_stage == "gender":
            if text in ["man", "kvinna", "annan", "vill ej ange"]:
                self.gender = text
                self.gender_input.disabled = True
                self.age_input.disabled    = False
                self.clear_cards()
                Clock.schedule_once(
                    lambda dt: setattr(self.age_input, "focus", True), 0.1
                )
                self.selection_stage = "age"
            else:
                self.show_error("Ogiltigt val", "Ange: man, kvinna, annan eller vill ej ange")
                self.gender_input.text = ""
                Clock.schedule_once(self.set_gender_focus, 0.1)

        elif self.selection_stage == "age":
            if text.isdigit():
                self.age = int(text)
                self.age_input.disabled  = True
                self.food_input.disabled = False
                self.clear_cards()
                Clock.schedule_once(self.set_food_focus, 0.1)
                self.selection_stage = "food"
            else:
                self.show_error("Fel format", "Ange alder med siffror.")
                self.age_input.text = ""
                Clock.schedule_once(
                    lambda dt: setattr(self.age_input, "focus", True), 0.1
                )

        elif self.selection_stage == "food":
            if text == "reset":
                self.reset_foods(None)
            elif text in ("berakna", "finish"):
                self.show_food(None)
            else:
                self.add_food()

    # ── add food ─────────────────────────────────────────────────────────────
    def add_food(self):
        scanned_data = self.food_input.text.strip().lower()
        self.has_pressed_button = True
        if not scanned_data:
            return
        self.clear_cards()
        if scanned_data in my_foods_dict:
            self.food_list.append(scanned_data)
            self.cards_layout.add_widget(
                NutrientCard(
                    "Tillagd!",
                    f"{scanned_data.capitalize()} tillagd.",
                    (0.10, 0.35, 0.18, 1),
                )
            )
        else:
            self.show_error("Hittades inte", f"'{scanned_data}' saknas.")
        self.food_input.text = ""
        Clock.schedule_once(self.set_food_focus, 0.1)

    def show_error(self, title, msg):
        self.clear_cards()
        self.cards_layout.add_widget(NutrientCard(title, msg, (0.35, 0.08, 0.10, 1)))

    # ── nearest place ─────────────────────────────────────────────────────────
    def get_nearast_point(self):
        self.lst = {}
        fenomenmagsinet = (58.3912, 15.5608)
        phi1    = math.radians(fenomenmagsinet[0])
        lambda1 = math.radians(fenomenmagsinet[1])
        R = 6371.0

        for key, value in destinations.linkoping_locations.items():
            phi2    = math.radians(value[0])
            lambda2 = math.radians(value[1])
            dp      = phi2 - phi1
            dl      = lambda2 - lambda1
            a       = (math.sin(dp / 2) ** 2
                       + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2)
            c       = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            self.lst[key] = R * c
        return self.lst

    def get_place(self):
        self.get_nearast_point()
        best_match  = ""
        smallest_diff = 10_000_000
        for key, dist in self.lst.items():
            diff = abs(self.distance_in_km - dist)
            if diff < smallest_diff:
                smallest_diff = diff
                best_match    = key
        return best_match

    # ── show results ─────────────────────────────────────────────────────────
    def show_food(self, instance):
        self.has_pressed_button = True
        self.food_input.text    = ""
        if not self.food_list:
            self.show_error("Tom lista", "Scanna livsmedel forst.")
            Clock.schedule_once(self.set_food_focus, 0.1)
            return

        res = Frukostdator.get_data_from_scanner(my_foods_dict, self.food_list)
        self.clear_cards()

        daily_kcal = get_daily_calories(self.age, self.gender)
        kcal       = res[0]
        fat_g      = res[1]
        protein_g  = res[2]
        sugar_g    = res[3]

        percent = round((kcal / daily_kcal) * 100) if daily_kcal > 0 else 0

        protein_min_day = (daily_kcal * 0.10) / 4
        protein_max_day = (daily_kcal * 0.20) / 4
        fat_min_day     = (daily_kcal * 0.25) / 9
        fat_max_day     = (daily_kcal * 0.40) / 9
        sugar_max_day   = (daily_kcal * 0.10) / 4

        protein_min_bkfst = round(protein_min_day * 0.20)
        protein_max_bkfst = round(protein_max_day * 0.25)
        fat_min_bkfst     = round(fat_min_day     * 0.20)
        fat_max_bkfst     = round(fat_max_day     * 0.25)
        sugar_max_bkfst   = round(sugar_max_day   * 0.25)
        kcal_min_bkfst    = round(daily_kcal * 0.20)
        kcal_max_bkfst    = round(daily_kcal * 0.25)

        # distance: 1 kcal burns ~1 kcal; running burns ~1 kcal/kg/km
        # => km = kcal / weight
        self.distance_in_km  = kcal / estimate_weight(self.age)
        self.distance_to_run = self.distance_in_km * 1000  # in metres
        dimension = "meter"
        disp_dist = self.distance_to_run

        if disp_dist > 10_000:
            disp_dist = round(disp_dist / 10_000, 2)
            dimension = "mil"
        elif disp_dist > 1_000:
            disp_dist = round(disp_dist / 1_000, 2)
            dimension = "km"
        else:
            disp_dist = round(disp_dist)

        # running-man speed
        if kcal < kcal_min_bkfst:
            speed = 0.25
        elif kcal <= daily_kcal:
            speed = 0.12
        else:
            speed = 0.05

        # ── Energy card ──────────────────────────────────────────────────────
        self.cards_layout.add_widget(NutrientCard(
            "Energi",
            (f"{round(kcal, 1)} kcal\n"
             f"Mal {kcal_min_bkfst}-{kcal_max_bkfst} kcal\n"
             f"{percent}% av dagsintag ({round(daily_kcal)} kcal)"),
            C_KCAL,
        ))

        # ── Running man ───────────────────────────────────────────────────────
        runner = RunningMan(size_hint=(1, None), height=400)
        self.cards_layout.add_widget(runner)
        runner.start(speed)
        Clock.schedule_once(lambda dt: runner.stop(), 5)

        # ── Distance card ─────────────────────────────────────────────────────
        place = self.get_place()
        self.cards_layout.add_widget(NutrientCard(
            "Distans",
            f"Du kan springa\n{disp_dist} {dimension}\nDet ar till: {place}",
            C_DIST,
        ))

        # ── Sugar cubes ───────────────────────────────────────────────────────
        self.cards_layout.add_widget(
            SugarCubesCard(sugar_g, sugar_max_bkfst)
        )

        # ── Fat circle ────────────────────────────────────────────────────────
        self.cards_layout.add_widget(CircleNutrientCard(
            "Fett",
            fat_g,
            fat_min_bkfst,
            fat_max_bkfst,
            C_FAT,
            fun_text=f"Dagsbudget: {round(fat_min_day)}-{round(fat_max_day)} g",
        ))

        # ── Protein circle ────────────────────────────────────────────────────
        self.cards_layout.add_widget(CircleNutrientCard(
            "Protein",
            protein_g,
            protein_min_bkfst,
            protein_max_bkfst,
            C_PROTEIN,
            fun_text=f"Dagsbudget: {round(protein_min_day)}-{round(protein_max_day)} g",
        ))

        Clock.schedule_once(self.set_food_focus, 0.5)

    def clear_cards(self):
        self.cards_layout.clear_widgets()

    # ── new breakfast (keep gender/age, clear foods) ─────────────────────────
    def new_breakfast(self, instance):
        self.food_list          = []
        self.has_pressed_button = True
        self.timer_seconds      = 0
        self.clear_cards()
        if self.selection_stage == "food":
            self.food_input.text     = ""
            self.food_input.disabled = False
            Clock.schedule_once(self.set_food_focus, 0.1)
        else:
            self.reset_foods(None)

    # ── full reset ────────────────────────────────────────────────────────────
    def reset_foods(self, instance):
        self.food_list          = []
        self.selection_stage    = "gender"
        self.timer_seconds      = 0
        self.has_pressed_button = False
        self.clear_cards()

        self.gender_input.disabled = False
        self.gender_input.text     = ""
        self.age_input.disabled    = True
        self.age_input.text        = ""
        self.food_input.disabled   = True
        self.food_input.text       = ""
        Clock.schedule_once(self.set_gender_focus, 0.5)


class FoodApp(App):
    def build(self):
        return FoodAppLayout()


if __name__ == "__main__":
    FoodApp().run()
