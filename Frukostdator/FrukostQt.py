#!/usr/bin/env python3
"""
Frukostdatorn – PyQt5 kiosk frontend
All input via barcode scanner. Run: python3 FrukostQt.py
Full-screen on Pi automatically; pass --window for dev.
"""
import math
import os
import sys

from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QTransform,
)
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import destinations
import Frukostdator

# ── Database ─────────────────────────────────────────────────────────────
_df = Frukostdator.get_excel_file()
MY_FOODS = Frukostdator.get_food_and_info(_df)

# ── Palette ───────────────────────────────────────────────────────────────
BG = "#FFF9F0"
AMBER = "#F59E0B"
AMBER_L = "#FEF3C7"
AMBER_B = "#FCD34D"
ORANGE = "#F97316"
ORANGE_L = "#FFF7ED"
ORANGE_B = "#FDBA74"
BLUE = "#3B82F6"
BLUE_L = "#EFF6FF"
BLUE_B = "#93C5FD"
VIOLET = "#8B5CF6"
VIOLET_L = "#F5F3FF"
VIOLET_B = "#C4B5FD"
GREEN = "#10B981"
GREEN_L = "#F0FDF4"
GREEN_B = "#6EE7B7"
ROSE = "#F43F5E"
ROSE_L = "#FFF1F2"
ROSE_B = "#FDA4AF"
RED = "#EF4444"
SUGAR_OK = "#22C55E"
SUGAR_L = "#DCFCE7"
DARK = "#1C1917"
MUTED = "#78716C"


# ── Helpers ───────────────────────────────────────────────────────────────
def estimate_weight(age):
    if age <= 10:
        return (age + 4) * 2
    if age <= 20:
        return age * 3 + 7
    return 75


def daily_kcal(age, gender):
    if age <= 3:
        return 1100
    if age <= 6:
        return 1510
    if age <= 10:
        return 1860
    m = f = 2200
    if age <= 14:
        m, f = 2510, 2200
    elif age <= 17:
        m, f = 3040, 2410
    elif age <= 24:
        m, f = 2800, 2200
    elif age <= 50:
        m, f = 2700, 2200
    elif age <= 70:
        m, f = 2500, 2000
    else:
        m, f = 2400, 2000
    if gender == "man":
        return m
    if gender == "kvinna":
        return f
    return (m + f) / 2


def haversine(la1, lo1, la2, lo2):
    R = 6371.0
    p1, p2 = math.radians(la1), math.radians(la2)
    a = (
        math.sin(math.radians(la2 - la1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


FENOMEN = (58.3912, 15.5608)


def nearest_place(dist_km):
    best, bd = "", 1e9
    for name, (la, lo) in destinations.linkoping_locations.items():
        diff = abs(dist_km - haversine(FENOMEN[0], FENOMEN[1], la, lo))
        if diff < bd:
            bd, best = diff, name
    return best


def fmt_dist(meters):
    if meters > 10000:
        return f"{meters/10000:.2f}", "mil"
    if meters > 1000:
        return f"{meters/1000:.2f}", "km"
    return str(int(meters)), "meter"


def get_status(v, lo, hi):
    if v < lo:
        return "⚠  Lite lite", AMBER
    if v <= hi:
        return "✓  Perfekt!", GREEN
    return "!  Lite för mycket", RED


def calc(foods, food_list, age, gender):
    kcal = fat = prot = sug = 0
    for n in food_list:
        info = foods.get(n.strip().lower(), {})
        kcal += info.get("Energi", 0)
        fat += info.get("Fett", 0)
        prot += info.get("Protein", 0)
        sug += info.get("Socker", 0)
    daily = daily_kcal(age, gender)
    w = estimate_weight(age)
    dk = kcal / w if w else 0
    return dict(
        kcal=kcal,
        fat=fat,
        prot=prot,
        sug=sug,
        daily=daily,
        pct=round(kcal / daily * 100) if daily else 0,
        kcal_min=round(daily * 0.20),
        kcal_max=round(daily * 0.25),
        fat_min=round(daily * 0.25 / 9 * 0.20),
        fat_max=round(daily * 0.40 / 9 * 0.25),
        fat_min_d=round(daily * 0.25 / 9),
        fat_max_d=round(daily * 0.40 / 9),
        pro_min=round(daily * 0.10 / 4 * 0.20),
        pro_max=round(daily * 0.20 / 4 * 0.25),
        pro_min_d=round(daily * 0.10 / 4),
        pro_max_d=round(daily * 0.20 / 4),
        sug_max=round(daily * 0.10 / 4 * 0.25),
        dist_km=dk,
        dist_m=dk * 1000,
        place=nearest_place(dk),
        speed=1.1 if kcal < round(daily * 0.20) else (0.55 if kcal <= daily else 0.27),
    )


# ── UI helpers ────────────────────────────────────────────────────────────
def lbl(text, size=14, bold=False, color=DARK, align=Qt.AlignLeft):
    w = QLabel(text)
    f = QFont()
    f.setPointSize(size)
    f.setBold(bold)
    w.setFont(f)
    w.setStyleSheet(f"color:{color};background:transparent;")
    w.setAlignment(align)
    w.setWordWrap(True)
    return w


def hline(color="#E5E7EB"):
    ln = QFrame()
    ln.setFrameShape(QFrame.HLine)
    ln.setFixedHeight(3)
    ln.setStyleSheet(f"background:{color};border:none;")
    return ln


def make_card(bg, border):
    f = QFrame()
    f.setAttribute(Qt.WA_StyledBackground, True)
    f.setStyleSheet(
        f"QFrame{{background:{bg};border:4px solid {border};border-radius:20px;}}"
    )
    return f


def scanner_field(placeholder, color=AMBER_B):
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    e.setStyleSheet(
        f"""
        QLineEdit{{background:white;border:4px solid {color};border-radius:16px;
                   padding:14px 22px;font-size:20px;font-weight:bold;color:{DARK};}}
        QLineEdit:focus{{border-color:{GREEN};}}
    """
    )
    return e


# ── Chameleon sprite runner ───────────────────────────────────────────────
_CHAM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Chameleon")

class RunnerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 130)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.dt     = 0.09   # frame-advance speed (larger = faster)
        self._frame = 0
        self._accum = 0.0

        # Load all 14 frames, scaled to fit
        self._frames = []
        for i in range(1, 15):
            px = QPixmap(os.path.join(_CHAM_DIR, f"{i:02d}.png"))
            self._frames.append(
                px.scaled(110, 95, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._tick)
        self._tmr.start(33)

    def set_speed(self, spd):
        # higher calorie speed value → smaller spd → larger dt → faster frames
        self.dt = 0.09 * (0.55 / max(spd, 0.1))

    def _tick(self):
        self._accum += self.dt
        while self._accum >= 0.09:        # advance one frame per 0.09 units accumulated
            self._accum -= 0.09
            self._frame = (self._frame + 1) % len(self._frames)
        self.update()

    def paintEvent(self, _):
        if not self._frames:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()

        px      = self._frames[self._frame]
        px_w    = px.width()
        px_h    = px.height()
        img_x   = (w - px_w) // 2 + 10   # shift right slightly for speed lines
        img_y   = (h - px_h) // 2

        # speed lines to the left — more lines at higher speed
        n_lines = 3 if self.dt > 0.14 else (2 if self.dt > 0.08 else 1)
        p.setPen(QPen(QColor(AMBER_B), 3, Qt.SolidLine, Qt.RoundCap))
        for i in range(n_lines):
            ly = img_y + px_h * 0.35 + i * (px_h * 0.22)
            ln = 24 - i * 5
            p.drawLine(QPointF(img_x - 8 - ln, ly), QPointF(img_x - 8, ly))

        # shadow
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 25))
        p.drawEllipse(QRectF(img_x + px_w * 0.1, h - 14, px_w * 0.8, 8))

        # current frame
        p.drawPixmap(img_x, img_y, px)


# ── Sugar cubes (QPainter) ────────────────────────────────────────────────
class SugarWidget(QWidget):
    def __init__(self, consumed_g, max_g, parent=None):
        super().__init__(parent)
        self.consumed_g = consumed_g
        self.max_g = max_g
        self.setMinimumHeight(180)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        G        = 4.0
        cC       = self.consumed_g / G          # float cubes consumed
        mC       = self.max_g / G               # float cubes at max
        n_max    = max(1, math.ceil(mC))        # slots that fit within max
        n_filled = max(0, math.floor(cC))       # whole cubes actually eaten

        # Scale widget to n_max so MAX line is always in frame.
        # Only draw CONSUMED cubes — no empty outlines.
        LBL_H  = 18
        TOP_M  = 28
        BOT_M  = LBL_H + 6
        D_FRAC = 0.44
        usable = h - TOP_M - BOT_M
        CUBE   = max(10, min(32, usable / n_max - 1))
        D      = CUBE * D_FRAC

        stack_w = CUBE + D * 0.58
        cx      = (w - stack_w) / 2 - 10
        base_y  = h - BOT_M

        def draw_cube(top_y, c_front, c_top, c_side, c_border, c_dot):
            # right side face
            p.setBrush(c_side); p.setPen(QPen(c_border, 0.7))
            p.drawPolygon(QPolygonF([
                QPointF(cx + CUBE,          top_y),
                QPointF(cx + CUBE + D*0.58, top_y - D*0.42),
                QPointF(cx + CUBE + D*0.58, top_y + CUBE - D*0.42),
                QPointF(cx + CUBE,          top_y + CUBE),
            ]))
            # top face
            p.setBrush(c_top)
            p.drawPolygon(QPolygonF([
                QPointF(cx,              top_y),
                QPointF(cx + CUBE,       top_y),
                QPointF(cx + CUBE+D*0.58,top_y - D*0.42),
                QPointF(cx + D*0.58,     top_y - D*0.42),
            ]))
            # front face
            p.setBrush(c_front); p.setPen(QPen(c_border, 0.7))
            p.drawRect(QRectF(cx, top_y, CUBE, CUBE))
            # crystal dots
            p.setPen(Qt.NoPen); p.setBrush(c_dot)
            dr = max(1.0, CUBE * 0.07)
            for fdx, fdy in [(0.22,0.25),(0.72,0.25),(0.22,0.72),(0.72,0.72),(0.47,0.48)]:
                p.drawEllipse(QRectF(cx+fdx*CUBE-dr, top_y+fdy*CUBE-dr, dr*2, dr*2))
            # highlight
            p.setPen(QPen(QColor(255,255,255,210), 1.2))
            p.drawLine(QPointF(cx, top_y), QPointF(cx + CUBE, top_y))

        # Draw only consumed cubes bottom→top — no empty outlines
        for i in range(n_filled):
            top_y   = base_y - (i + 1) * CUBE
            allowed = i < mC
            if allowed:
                draw_cube(top_y,
                    QColor("#FAFAFA"), QColor("#DBEAFE"),
                    QColor("#93C5FD"), QColor("#BFDBFE"),
                    QColor(148, 163, 184, 100))
            else:
                draw_cube(top_y,
                    QColor("#FEE2E2"), QColor("#FECACA"),
                    QColor("#F87171"), QColor("#FCA5A5"),
                    QColor(220, 80, 80, 120))

        # ── MAX horizontal line at exact fractional height ────────────────
        max_y  = base_y - mC * CUBE
        line_x1 = cx - 6
        line_x2 = cx + CUBE + D * 0.58 + 6
        p.setPen(QPen(QColor(RED), 2.8))
        p.drawLine(QPointF(line_x1, max_y), QPointF(line_x2, max_y))

        # Arrow tips on both ends
        p.setPen(Qt.NoPen); p.setBrush(QColor(RED))
        for ax in (line_x1, line_x2):
            sign = -1 if ax == line_x1 else 1
            p.drawPolygon(QPolygonF([
                QPointF(ax,          max_y - 4),
                QPointF(ax,          max_y + 4),
                QPointF(ax + sign*7, max_y),
            ]))

        # MAX label to the right
        fmax = QFont(); fmax.setBold(True); fmax.setPointSize(9)
        p.setFont(fmax)
        p.setPen(QColor(RED))
        p.drawText(QRectF(line_x2 + 5, max_y - 9, 38, 18),
                   Qt.AlignVCenter | Qt.AlignLeft, "MAX")

        # Unit label at the very bottom
        fu = QFont(); fu.setPointSize(8)
        p.setFont(fu)
        p.setPen(QColor(MUTED))
        p.drawText(QRectF(0, h - LBL_H, w, LBL_H),
                   Qt.AlignCenter, f"1 kub = {int(G)} g socker")


# ── Circle chart (QPainter) ───────────────────────────────────────────────
class CircleWidget(QWidget):
    def __init__(self, value, lo, hi, color, parent=None):
        super().__init__(parent)
        self.value = value
        self.lo = lo
        self.hi = hi
        self.color = QColor(color)
        self.setFixedSize(165, 165)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx = cy = self.width() // 2
        R = cx - 12
        thick = 14
        pct = (self.value / self.hi) if self.hi > 0 else 0
        arc_col = QColor(RED) if self.value > self.hi else self.color

        p.setPen(QPen(QColor("#F3F4F6"), thick, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(QRectF(cx - R, cy - R, R * 2, R * 2), 90 * 16, -360 * 16)

        if pct > 0:
            p.setPen(QPen(arc_col, thick, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(
                QRectF(cx - R, cy - R, R * 2, R * 2),
                90 * 16,
                -int(min(pct, 1) * 360 * 16),
            )

        inn = R - thick // 2
        p.setPen(Qt.NoPen)
        p.setBrush(Qt.white)
        p.drawEllipse(QRectF(cx - inn, cy - inn, inn * 2, inn * 2))
        p.setBrush(QColor(arc_col.red(), arc_col.green(), arc_col.blue(), 15))
        p.drawEllipse(QRectF(cx - inn, cy - inn, inn * 2, inn * 2))

        # --- value (big number) in upper zone ---
        fv = QFont(); fv.setBold(True); fv.setPointSize(14)
        p.setFont(fv)
        fm_v = QFontMetrics(fv)
        val_str = f"{round(self.value, 1)}g"
        # shrink if it would overflow the inner diameter
        while fm_v.horizontalAdvance(val_str) > inn * 2 - 8 and fv.pointSize() > 8:
            fv.setPointSize(fv.pointSize() - 1)
            p.setFont(fv)
            fm_v = QFontMetrics(fv)
        val_h = fm_v.height()
        p.setPen(QColor(DARK))
        p.drawText(
            QRectF(cx - inn, cy - inn + 6, inn * 2, val_h),
            Qt.AlignHCenter | Qt.AlignVCenter,
            val_str,
        )

        # --- range text in middle ---
        fs = QFont(); fs.setPointSize(9)
        p.setFont(fs)
        fm_s = QFontMetrics(fs)
        range_h = fm_s.height()
        range_y = cy - inn + 6 + val_h + 4
        p.setPen(QColor(MUTED))
        p.drawText(
            QRectF(cx - inn, range_y, inn * 2, range_h),
            Qt.AlignHCenter | Qt.AlignVCenter,
            f"{round(self.lo)}–{round(self.hi)} g",
        )

        # --- % badge pinned to bottom of inner circle ---
        fb = QFont(); fb.setBold(True); fb.setPointSize(10)
        p.setFont(fb)
        badge = f"{round(pct * 100)}%"
        bw = QFontMetrics(fb).horizontalAdvance(badge) + 16
        bh = 20
        bx = cx - bw // 2
        by = cy + inn - bh - 5          # 5 px margin from inner circle edge
        p.setBrush(Qt.white)
        p.setPen(QPen(arc_col, 1.8))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), bh // 2, bh // 2)
        p.setPen(arc_col)
        p.drawText(QRectF(bx, by, bw, bh), Qt.AlignCenter, badge)




# ═══════════════════════════════════════════════════════════════════════════
# PAGES
# ═══════════════════════════════════════════════════════════════════════════


class GenderPage(QWidget):
    chosen = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._age = 0
        root = QVBoxLayout(self)
        root.setContentsMargins(80, 50, 80, 50)
        root.setSpacing(30)

        root.addWidget(lbl("Hej! Vem är du?", 34, True, DARK, Qt.AlignCenter))
        root.addWidget(lbl("Scanna din könkod", 16, False, MUTED, Qt.AlignCenter))

        cards_row = QHBoxLayout()
        cards_row.setSpacing(20)
        colors = [
            (BLUE_L,      BLUE_B),
            ("#FCE7F3",   "#F9A8D4"),
            (VIOLET_L,    VIOLET_B),
        ]
        self._card_emojis = []
        self._card_labels = []
        for bg, border in colors:
            c = make_card(bg, border)
            v = QVBoxLayout(c)
            v.setContentsMargins(20, 22, 20, 22)
            v.setSpacing(8)
            e = lbl("", 54, False, DARK, Qt.AlignCenter)
            t = lbl("", 28, True,  DARK, Qt.AlignCenter)
            v.addWidget(e)
            v.addWidget(t)
            c.setMinimumHeight(170)
            cards_row.addWidget(c)
            self._card_emojis.append(e)
            self._card_labels.append(t)
        root.addLayout(cards_row)

        self._inp = scanner_field("Scanna könkod...")
        self._inp.returnPressed.connect(self._submit)
        root.addWidget(self._inp)

        self._err = lbl("", 13, False, RED, Qt.AlignCenter)
        root.addWidget(self._err)
        root.addStretch()

    def setup(self, age):
        self._age = age
        if age < 18:
            opts  = [("🧒", "Pojke"), ("👧", "Flicka"), ("", "Annat")]
            hint  = "Scanna könkod: pojke / flicka / annat"
        else:
            opts  = [("👨", "Man"), ("👩", "Kvinna"), ("", "Annat")]
            hint  = "Scanna könkod: man / kvinna / annat"
        for i, (emoji, label) in enumerate(opts):
            self._card_emojis[i].setText(emoji)
            self._card_emojis[i].setVisible(bool(emoji))
            self._card_labels[i].setText(label)
        self._inp.setPlaceholderText(hint)

    def showEvent(self, _):
        self._inp.clear()
        QTimer.singleShot(80, self._inp.setFocus)

    def _submit(self):
        raw = self._inp.text().strip().lower()
        self._inp.clear()
        MAP = {
            "pojke": "man", "flicka": "kvinna",
            "man": "man",   "kvinna": "kvinna",
            "annat": "annan", "annan": "annan", "vill ej ange": "annan",
        }
        if raw in MAP:
            self._err.setText("")
            self.chosen.emit(MAP[raw])
        else:
            self._err.setText(f'Okänd kod: "{raw}" — försök igen')


class AgePage(QWidget):
    chosen = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(80, 50, 80, 50)
        root.setSpacing(28)

        root.addWidget(lbl("Hur gammal är du? 🎂", 34, True, DARK, Qt.AlignCenter))
        root.addWidget(lbl("Scanna din ålder", 16, False, MUTED, Qt.AlignCenter))

        self._disp = lbl("—", 88, True, AMBER, Qt.AlignCenter)
        root.addWidget(self._disp)
        root.addWidget(lbl("år", 18, False, MUTED, Qt.AlignCenter))

        self._inp = scanner_field("Scanna ålder (t.ex. 10)...")
        self._inp.textChanged.connect(
            lambda t: self._disp.setText(t if t.isdigit() else "—")
        )
        self._inp.returnPressed.connect(self._submit)
        root.addWidget(self._inp)

        self._err = lbl("", 13, False, RED, Qt.AlignCenter)
        root.addWidget(self._err)
        root.addStretch()

    def showEvent(self, _):
        self._inp.clear()
        self._disp.setText("—")
        QTimer.singleShot(80, self._inp.setFocus)

    def _submit(self):
        txt = self._inp.text().strip()
        self._inp.clear()
        if txt.isdigit() and 1 <= int(txt) <= 120:
            self._err.setText("")
            self.chosen.emit(int(txt))
        else:
            self._err.setText("Ange ålder med siffror!")


class FoodPage(QWidget):
    calc_requested = pyqtSignal()
    reset_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.food_list = []
        root = QVBoxLayout(self)
        root.setContentsMargins(60, 30, 60, 30)
        root.setSpacing(14)

        root.addWidget(lbl("Scanna din frukost! 🍽️", 30, True, DARK, Qt.AlignCenter))
        root.addWidget(
            lbl(
                "Håll streckkoden mot scannern  ·  scanna 'berakna' när du är klar",
                14,
                False,
                MUTED,
                Qt.AlignCenter,
            )
        )

        self._inp = scanner_field("📷  Scanna livsmedel...")
        self._inp.textChanged.connect(self._live)
        self._inp.returnPressed.connect(self._submit)
        root.addWidget(self._inp)

        self._fb = lbl("", 14, True, GREEN, Qt.AlignCenter)
        root.addWidget(self._fb)

        self._list_lbl = QLabel("")
        self._list_lbl.setWordWrap(True)
        self._list_lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._list_lbl.setStyleSheet(
            f"color:{DARK};background:transparent;font-size:15px;"
        )
        root.addWidget(self._list_lbl)
        root.addStretch()

    def reset(self):
        self.food_list = []
        self._inp.clear()
        self._fb.setText("")
        self._list_lbl.setText("")

    def showEvent(self, _):
        QTimer.singleShot(80, self._inp.setFocus)

    def _live(self, txt):
        key = txt.strip().lower()
        if not key:
            return
        if key == "reset":
            self.reset_requested.emit()
            self._inp.clear()
            return
        if key in ("berakna", "finish"):
            self.calc_requested.emit()
            self._inp.clear()
            return
        if key in MY_FOODS:
            self._add(key)

    def _submit(self):
        key = self._inp.text().strip().lower()
        self._inp.clear()
        if not key:
            return
        if key == "reset":
            self.reset_requested.emit()
            return
        if key in ("berakna", "finish"):
            self.calc_requested.emit()
            return
        if key in MY_FOODS:
            self._add(key)
        else:
            self._fb.setStyleSheet(f"color:{RED};background:transparent;")
            self._fb.setText(f'Hittades inte: "{key}"')

    def _add(self, key):
        self.food_list.append(key)
        self._inp.clear()
        self._fb.setStyleSheet(f"color:{GREEN};background:transparent;")
        self._fb.setText(f"✅  Tillagd: {key}!")
        lines = "\n".join(f"  {i+1}.  {name}" for i, name in enumerate(self.food_list))
        self._list_lbl.setText(lines)
        QTimer.singleShot(60, self._inp.setFocus)


class ResultsPage(QWidget):
    reset_requested = pyqtSignal()
    new_bkfst = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 16, 24, 16)
        outer.setSpacing(12)

        self._title = lbl("Din frukost! 🎉", 26, True, DARK, Qt.AlignCenter)
        outer.addWidget(self._title)

        self._grid_w = QWidget()
        self._grid = QGridLayout(self._grid_w)
        self._grid.setSpacing(12)
        outer.addWidget(self._grid_w, 1)

        self._inp = scanner_field("Scanna 'ny frukost' eller 'reset'...", VIOLET_B)
        self._inp.textChanged.connect(self._live)
        self._inp.returnPressed.connect(self._submit)
        outer.addWidget(self._inp)
        outer.addWidget(
            lbl(
                "Scanna 'ny frukost' för att mäta igen  ·  'reset' för att börja om",
                12,
                False,
                MUTED,
                Qt.AlignCenter,
            )
        )

    def showEvent(self, _):
        QTimer.singleShot(80, self._inp.setFocus)

    def _live(self, txt):
        key = txt.strip().lower()
        if key == "reset":
            self.reset_requested.emit()
            self._inp.clear()
        elif key in ("ny frukost", "nyfrukost"):
            self.new_bkfst.emit()
            self._inp.clear()

    def _submit(self):
        key = self._inp.text().strip().lower()
        self._inp.clear()
        if key == "reset":
            self.reset_requested.emit()
        elif key in ("ny frukost", "nyfrukost"):
            self.new_bkfst.emit()

    def load(self, res, n):
        self._title.setText(f"Din frukost! 🎉   ({n} livsmedel)")
        while self._grid.count():
            it = self._grid.takeAt(0)
            if it and it.widget():
                it.widget().deleteLater()

        def card_vbox(bg, border):
            c = make_card(bg, border)
            v = QVBoxLayout(c)
            v.setContentsMargins(14, 12, 14, 12)
            v.setSpacing(5)
            return c, v

        # Energy
        c, v = card_vbox(AMBER_L, AMBER_B)
        v.addWidget(lbl("⚡ Energi", 17, True, "#92400E"))
        v.addWidget(hline(AMBER_B))
        st, sc = get_status(res["kcal"], res["kcal_min"], res["kcal_max"])
        v.addWidget(lbl(st, 12, True, sc))
        v.addWidget(lbl(f"{round(res['kcal'])} kcal", 32, True, AMBER, Qt.AlignCenter))
        v.addWidget(
            lbl(f"Mål: {res['kcal_min']}–{res['kcal_max']} kcal", 12, True, "#92400E")
        )
        v.addWidget(
            lbl(
                f"{res['pct']}% av dagsbehovet ({round(res['daily'])} kcal)",
                12,
                True,
                MUTED,
            )
        )
        self._grid.addWidget(c, 0, 0)

        # Runner
        c, v = card_vbox(BLUE_L, BLUE_B)
        v.addWidget(lbl("🏃 Springgubbe", 17, True, "#1E40AF"))
        v.addWidget(hline(BLUE_B))
        spd = res["speed"]
        v.addWidget(
            lbl(
                (
                    "Lugnt tempo 🐢"
                    if spd >= 1
                    else ("Bra fart! 🏃" if spd >= 0.5 else "SUPERSNABB!! 🚀")
                ),
                12,
                True,
                BLUE,
            )
        )
        rw = RunnerWidget()
        rw.set_speed(spd)
        v.addWidget(rw, 0, Qt.AlignCenter)
        self._grid.addWidget(c, 0, 1)

        # Distance
        dv, du = fmt_dist(res["dist_m"])
        c, v = card_vbox(VIOLET_L, VIOLET_B)
        v.addWidget(lbl("📍 Distans", 17, True, "#5B21B6"))
        v.addWidget(hline(VIOLET_B))
        v.addWidget(lbl("Du kan springa...", 12, True, MUTED))
        v.addWidget(lbl(f"{dv} {du}", 32, True, VIOLET, Qt.AlignCenter))
        v.addWidget(lbl("Ungefär till:", 12, True, MUTED))
        v.addWidget(lbl(res["place"], 14, True, "#4C1D95"))
        self._grid.addWidget(c, 0, 2)

        # Sugar
        ok = res["sug"] <= res["sug_max"]
        c, v = card_vbox(SUGAR_L if ok else ROSE_L, GREEN_B if ok else ROSE_B)
        v.addWidget(lbl("🍬 Socker", 17, True, "#065F46" if ok else "#9F1239"))
        v.addWidget(hline(GREEN_B if ok else ROSE_B))
        st, sc = get_status(res["sug"], 0.001, res["sug_max"])
        v.addWidget(lbl(st, 12, True, sc))
        v.addWidget(
            lbl(f"{round(res['sug'],1)} g  /  max {res['sug_max']} g", 12, True, MUTED)
        )
        v.addWidget(SugarWidget(res["sug"], res["sug_max"]))
        self._grid.addWidget(c, 1, 0)

        # Fat
        c, v = card_vbox(ORANGE_L, ORANGE_B)
        v.addWidget(lbl("🧈 Fett", 17, True, "#9A3412"))
        v.addWidget(hline(ORANGE_B))
        st, sc = get_status(res["fat"], res["fat_min"], res["fat_max"])
        v.addWidget(lbl(st, 12, True, sc))
        v.addWidget(CircleWidget(res["fat"], res["fat_min"], res["fat_max"], ORANGE), 0, Qt.AlignCenter)
        v.addWidget(
            lbl(
                f"Dagsbudget: {res['fat_min_d']}–{res['fat_max_d']} g",
                12,
                True,
                MUTED,
                Qt.AlignCenter,
            )
        )
        self._grid.addWidget(c, 1, 1)

        # Protein
        c, v = card_vbox(BLUE_L, BLUE_B)
        v.addWidget(lbl("💪 Protein", 17, True, "#1E3A8A"))
        v.addWidget(hline(BLUE_B))
        st, sc = get_status(res["prot"], res["pro_min"], res["pro_max"])
        v.addWidget(lbl(st, 12, True, sc))
        v.addWidget(CircleWidget(res["prot"], res["pro_min"], res["pro_max"], BLUE), 0, Qt.AlignCenter)
        v.addWidget(
            lbl(
                f"Dagsbudget: {res['pro_min_d']}–{res['pro_max_d']} g",
                12,
                True,
                MUTED,
                Qt.AlignCenter,
            )
        )
        self._grid.addWidget(c, 1, 2)

        QTimer.singleShot(80, self._inp.setFocus)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Frukostdatorn")
        self.setStyleSheet(f"QWidget{{background:{BG};}}")
        self._gender = None
        self._age = None
        self._tsec = 60
        self._tactive = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setFixedHeight(62)
        hdr.setStyleSheet("background:white;border-bottom:4px solid #FCD34D;")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.addWidget(lbl("🍳 Frukostdatorn", 20, True, AMBER))
        hl.addStretch()
        self._step_labels = []
        for s in ("🔢 Ålder", "👤 Vem", "🍎 Frukost", "✨ Resultat"):
            lb = QLabel(s)
            lb.setStyleSheet(
                "background:#F3F4F6;color:#9CA3AF;border-radius:11px;"
                "padding:4px 12px;font-weight:bold;font-size:12px;"
            )
            hl.addWidget(lb)
            self._step_labels.append(lb)
        hl.addStretch()
        self._tlbl = lbl("", 11, False, MUTED)
        hl.addWidget(self._tlbl)
        root.addWidget(hdr)

        # Timer strip
        self._tbar_bg = QWidget()
        self._tbar_bg.setFixedHeight(4)
        self._tbar_bg.setStyleSheet("background:#F3F4F6;")
        self._tbar = QWidget(self._tbar_bg)
        self._tbar.setStyleSheet("background:#FCD34D;")
        root.addWidget(self._tbar_bg)

        # Pages
        self._stack = QStackedWidget()
        self._p_age = AgePage()
        self._p_gender = GenderPage()
        self._p_food = FoodPage()
        self._p_results = ResultsPage()
        for p in (self._p_age, self._p_gender, self._p_food, self._p_results):
            self._stack.addWidget(p)
        root.addWidget(self._stack)

        # Signals
        self._p_age.chosen.connect(self._on_age)
        self._p_gender.chosen.connect(self._on_gender)
        self._p_food.calc_requested.connect(self._on_calc)
        self._p_food.reset_requested.connect(self._do_reset)
        self._p_results.reset_requested.connect(self._do_reset)
        self._p_results.new_bkfst.connect(self._new_bkfst)

        self._atimer = QTimer(self)
        self._atimer.timeout.connect(self._tick)
        self._atimer.start(1000)
        self._go(0)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update_tbar()

    def _go(self, idx):
        self._stack.setCurrentIndex(idx)
        ACTIVE = f"background:{AMBER_B};color:#78350F;border-radius:11px;padding:4px 12px;font-weight:bold;font-size:12px;"
        DONE = f"background:{GREEN_L};color:#065F46;border-radius:11px;padding:4px 12px;font-weight:bold;font-size:12px;"
        PENDING = "background:#F3F4F6;color:#9CA3AF;border-radius:11px;padding:4px 12px;font-weight:bold;font-size:12px;"
        for i, lb in enumerate(self._step_labels):
            lb.setStyleSheet(ACTIVE if i == idx else DONE if i < idx else PENDING)

    def _on_age(self, a):
        self._age = a
        self._tsec = 60
        self._p_gender.setup(a)
        self._go(1)

    def _on_gender(self, g):
        self._gender = g
        self._tactive = True
        self._tsec = 60
        self._p_food.reset()
        self._go(2)

    def _on_calc(self):
        if not self._p_food.food_list:
            return
        res = calc(MY_FOODS, self._p_food.food_list, self._age, self._gender)
        self._p_results.load(res, len(self._p_food.food_list))
        self._tsec = 60
        self._go(3)

    def _new_bkfst(self):
        self._p_food.reset()
        self._tsec = 60
        self._go(2)

    def _do_reset(self):
        self._gender = None
        self._age = None
        self._p_food.reset()
        self._tactive = False
        self._tsec = 60
        self._tlbl.setText("")
        self._update_tbar()
        self._go(0)

    def _tick(self):
        if not self._tactive:
            return
        self._tsec -= 1
        self._tlbl.setText(f"Auto-reset om {self._tsec}s")
        self._update_tbar()
        if self._tsec <= 0:
            self._do_reset()

    def _update_tbar(self):
        pct = (self._tsec / 60) if self._tactive else 1.0
        self._tbar.setGeometry(0, 0, int(self._tbar_bg.width() * pct), 4)


# ── Entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    f = QFont()
    for fam in ("Cantarell", "Ubuntu", "DejaVu Sans", "Arial"):
        f.setFamily(fam)
        if QFontMetrics(f).averageCharWidth() > 0:
            break
    f.setPointSize(13)
    app.setFont(f)

    win = MainWindow()
    if "--window" in sys.argv:
        win.resize(1280, 800)
        win.show()
    else:
        win.showFullScreen()

    sys.exit(app.exec_())
