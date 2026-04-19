#!/usr/bin/env python3
"""
Frukostdatorn – PyQt5 kiosk frontend
All input via barcode scanner. Run: python3 FrukostQt.py
Full-screen on Pi automatically; pass --window for dev.
"""
import sys, math
from PyQt5.QtWidgets import (
    QApplication, QWidget, QStackedWidget, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QFrame,
    QLayout, QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF, QRect, QPoint, QSize, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QPen,
    QPainterPath, QPolygonF,
)

import Frukostdator
import destinations

# ── Database ─────────────────────────────────────────────────────────────
_df      = Frukostdator.get_excel_file()
MY_FOODS = Frukostdator.get_food_and_info(_df)

# ── Palette ───────────────────────────────────────────────────────────────
BG        = "#FFF9F0"
AMBER     = "#F59E0B";  AMBER_L  = "#FEF3C7";  AMBER_B = "#FCD34D"
ORANGE    = "#F97316";  ORANGE_L = "#FFF7ED";  ORANGE_B= "#FDBA74"
BLUE      = "#3B82F6";  BLUE_L   = "#EFF6FF";  BLUE_B  = "#93C5FD"
VIOLET    = "#8B5CF6";  VIOLET_L = "#F5F3FF";  VIOLET_B= "#C4B5FD"
GREEN     = "#10B981";  GREEN_L  = "#F0FDF4";  GREEN_B = "#6EE7B7"
ROSE      = "#F43F5E";  ROSE_L   = "#FFF1F2";  ROSE_B  = "#FDA4AF"
RED       = "#EF4444"
SUGAR_OK  = "#22C55E";  SUGAR_L  = "#DCFCE7"
DARK      = "#1C1917";  MUTED    = "#78716C"

# ── Helpers ───────────────────────────────────────────────────────────────
def estimate_weight(age):
    if age <= 10: return (age + 4) * 2
    if age <= 20: return age * 3 + 7
    return 75

def daily_kcal(age, gender):
    if age <= 3:  return 1100
    if age <= 6:  return 1510
    if age <= 10: return 1860
    m = f = 2200
    if   age <= 14: m, f = 2510, 2200
    elif age <= 17: m, f = 3040, 2410
    elif age <= 24: m, f = 2800, 2200
    elif age <= 50: m, f = 2700, 2200
    elif age <= 70: m, f = 2500, 2000
    else:           m, f = 2400, 2000
    if gender == "man":    return m
    if gender == "kvinna": return f
    return (m + f) / 2

def haversine(la1, lo1, la2, lo2):
    R = 6371.0
    p1, p2 = math.radians(la1), math.radians(la2)
    a = (math.sin(math.radians(la2 - la1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2)
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
    if meters > 10000: return f"{meters/10000:.2f}", "mil"
    if meters > 1000:  return f"{meters/1000:.2f}",  "km"
    return str(int(meters)), "meter"

def get_status(v, lo, hi):
    if v < lo:   return "⚠  Lite lite",     AMBER
    if v <= hi:  return "✓  Perfekt!",       GREEN
    return              "!  Lite för mycket", RED

def calc(foods, food_list, age, gender):
    kcal = fat = prot = sug = 0
    for n in food_list:
        info = foods.get(n.strip().lower(), {})
        kcal += info.get("Energi",  0)
        fat  += info.get("Fett",    0)
        prot += info.get("Protein", 0)
        sug  += info.get("Socker",  0)
    daily = daily_kcal(age, gender)
    w     = estimate_weight(age)
    dk    = kcal / w if w else 0
    return dict(
        kcal=kcal, fat=fat, prot=prot, sug=sug, daily=daily,
        pct=round(kcal / daily * 100) if daily else 0,
        kcal_min=round(daily * .20), kcal_max=round(daily * .25),
        fat_min=round(daily*.25/9*.20),  fat_max=round(daily*.40/9*.25),
        fat_min_d=round(daily*.25/9),    fat_max_d=round(daily*.40/9),
        pro_min=round(daily*.10/4*.20),  pro_max=round(daily*.20/4*.25),
        pro_min_d=round(daily*.10/4),    pro_max_d=round(daily*.20/4),
        sug_max=round(daily*.10/4*.25),
        dist_km=dk, dist_m=dk*1000, place=nearest_place(dk),
        speed=1.1 if kcal < round(daily*.20) else (.55 if kcal <= daily else .27),
    )

# ── UI helpers ────────────────────────────────────────────────────────────
def lbl(text, size=14, bold=False, color=DARK, align=Qt.AlignLeft):
    w = QLabel(text)
    f = QFont(); f.setPointSize(size); f.setBold(bold)
    w.setFont(f)
    w.setStyleSheet(f"color:{color};background:transparent;")
    w.setAlignment(align)
    w.setWordWrap(True)
    return w

def hline(color="#E5E7EB"):
    ln = QFrame(); ln.setFrameShape(QFrame.HLine)
    ln.setFixedHeight(3)
    ln.setStyleSheet(f"background:{color};border:none;")
    return ln

def make_card(bg, border):
    f = QFrame()
    f.setAttribute(Qt.WA_StyledBackground, True)
    f.setStyleSheet(f"QFrame{{background:{bg};border:4px solid {border};border-radius:20px;}}")
    return f

def scanner_field(placeholder, color=AMBER_B):
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    e.setStyleSheet(f"""
        QLineEdit{{background:white;border:4px solid {color};border-radius:16px;
                   padding:14px 22px;font-size:20px;font-weight:bold;color:{DARK};}}
        QLineEdit:focus{{border-color:{GREEN};}}
    """)
    return e

# ── Running man (QPainter, smooth animation) ──────────────────────────────
class RunnerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(130, 190)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.t  = 0.0
        self.dt = 0.09
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._tick)
        self._tmr.start(33)

    def set_speed(self, spd):
        self.dt = 0.09 * (0.55 / max(spd, 0.1))

    def _tick(self):
        self.t = (self.t + self.dt) % (2 * math.pi)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx = self.width() // 2
        bounce   = abs(math.sin(self.t)) * 7
        base_y   = self.height() - 16
        tb       = base_y - 60 - bounce
        tt       = tb - 34
        head_cy  = tt - 22

        la = math.sin(self.t)       * math.radians(36)
        ra = math.sin(self.t + math.pi) * math.radians(36)
        ll = math.sin(self.t + 0.5) * math.radians(32)
        rl = math.sin(self.t + 0.5 + math.pi) * math.radians(32)
        AL, LL = 30, 36

        # shadow
        p.setPen(Qt.NoPen); p.setBrush(QColor(0, 0, 0, 28))
        p.drawEllipse(QRectF(cx - 18, base_y + 2, 36, 10))

        # speed lines
        p.setPen(QPen(QColor(AMBER_B), 3, Qt.SolidLine, Qt.RoundCap))
        for dy in (-14, -2, 9):
            p.drawLine(cx - 42, int(head_cy + dy), cx - 54, int(head_cy + dy))

        # legs
        p.setPen(QPen(QColor(ORANGE), 10, Qt.SolidLine, Qt.RoundCap))
        lx = cx - 5 + math.sin(ll) * LL;  ly = tb + math.cos(ll) * LL
        rx = cx + 5 + math.sin(rl) * LL;  ry = tb + math.cos(rl) * LL
        p.drawLine(cx - 5, int(tb), int(lx), int(ly))
        p.drawLine(cx + 5, int(tb), int(rx), int(ry))

        # shoes
        p.setPen(Qt.NoPen); p.setBrush(QColor(DARK))
        p.drawEllipse(QRectF(lx - 9, ly - 4, 18, 9))
        p.drawEllipse(QRectF(rx - 9, ry - 4, 18, 9))

        # body
        p.setBrush(QColor(BLUE))
        p.drawRoundedRect(QRectF(cx - 13, tt, 26, 36), 11, 11)
        p.setBrush(QColor(255, 255, 255, 55))
        p.drawRoundedRect(QRectF(cx - 13, tt + 11, 26, 7), 4, 4)

        # arms
        p.setPen(QPen(QColor("#FBBF24"), 10, Qt.SolidLine, Qt.RoundCap))
        lax = cx - 11 + math.sin(la) * AL;  lay = tt + 9 + math.cos(la) * AL
        rax = cx + 11 + math.sin(ra) * AL;  ray = tt + 9 + math.cos(ra) * AL
        p.drawLine(cx - 11, int(tt + 9), int(lax), int(lay))
        p.drawLine(cx + 11, int(tt + 9), int(rax), int(ray))
        p.setPen(Qt.NoPen); p.setBrush(QColor("#FBBF24"))
        p.drawEllipse(QRectF(lax - 6, lay - 6, 12, 12))
        p.drawEllipse(QRectF(rax - 6, ray - 6, 12, 12))

        # head
        p.setBrush(QColor("#FBBF24"))
        p.drawEllipse(QRectF(cx - 19, head_cy - 19, 38, 38))
        p.setBrush(QColor(239, 100, 100, 55))
        p.drawEllipse(QRectF(cx - 19, head_cy - 2, 10, 10))
        p.drawEllipse(QRectF(cx +  9, head_cy - 2, 10, 10))
        p.setBrush(QColor(DARK))
        p.drawEllipse(QRectF(cx - 11, head_cy - 8, 7, 7))
        p.drawEllipse(QRectF(cx +  4, head_cy - 8, 7, 7))
        p.setBrush(Qt.white)
        p.drawEllipse(QRectF(cx -  9, head_cy - 10, 3, 3))
        p.drawEllipse(QRectF(cx +  6, head_cy - 10, 3, 3))
        smile = QPainterPath()
        smile.moveTo(cx - 8, head_cy + 2)
        smile.cubicTo(cx - 3, head_cy + 8, cx + 3, head_cy + 8, cx + 8, head_cy + 2)
        p.setPen(QPen(QColor(DARK), 2.5, Qt.SolidLine, Qt.RoundCap))
        p.drawPath(smile)

# ── Sugar cubes (QPainter) ────────────────────────────────────────────────
class SugarWidget(QWidget):
    def __init__(self, consumed_g, max_g, parent=None):
        super().__init__(parent)
        self.consumed_g = consumed_g
        self.max_g      = max_g
        self.setMinimumHeight(150)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h    = self.width(), self.height()
        G       = 3.0
        total   = max(4, math.ceil(max(self.consumed_g, self.max_g) / G) + 3)
        cC      = self.consumed_g / G
        mC      = self.max_g / G
        COLS    = min(int(total), 10)
        CUBE    = min(26, (w - 30) / COLS - 4)
        GAP     = 4
        D       = CUBE * 0.30
        bx      = (w - (COLS * (CUBE + GAP) - GAP)) / 2
        by      = D + 10

        for i in range(math.ceil(total)):
            col = i % COLS;  row = i // COLS
            cx  = bx + col * (CUBE + GAP)
            cy  = by + row * (CUBE + GAP + D * 0.25)
            if i < cC:
                f, t, s = (QColor(SUGAR_OK), QColor("#86EFAC"), QColor("#15803D")) if i < mC else \
                          (QColor(RED),      QColor("#FCA5A5"), QColor("#B91C1C"))
            else:
                f, t, s = QColor("#E5E7EB"), QColor("#F3F4F6"), QColor("#D1D5DB")

            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 28))
            p.drawRect(QRectF(cx + 3, cy + 3, CUBE, CUBE))
            p.setBrush(f)
            p.drawRoundedRect(QRectF(cx, cy, CUBE, CUBE), 2, 2)
            p.setBrush(t)
            p.drawPolygon(QPolygonF([
                QPointF(cx, cy), QPointF(cx + CUBE, cy),
                QPointF(cx + CUBE + D*.7, cy - D*.5), QPointF(cx + D*.7, cy - D*.5),
            ]))
            p.setBrush(s)
            p.drawPolygon(QPolygonF([
                QPointF(cx + CUBE, cy), QPointF(cx + CUBE + D*.7, cy - D*.5),
                QPointF(cx + CUBE + D*.7, cy + CUBE - D*.5), QPointF(cx + CUBE, cy + CUBE),
            ]))
            p.setBrush(QColor(255, 255, 255, 55))
            p.drawRoundedRect(QRectF(cx + 2, cy + 3, CUBE - 4, 4), 1, 1)

        # MAX dashed line
        mRow = int(mC) // COLS
        ly   = by + mRow * (CUBE + GAP + D * 0.25) - D * 0.4 - 3
        pen  = QPen(QColor(RED), 2.2)
        pen.setDashPattern([6, 3])
        p.setPen(pen)
        p.drawLine(QPointF(8, ly), QPointF(w - 8, ly))
        f2 = QFont(); f2.setBold(True); f2.setPointSize(9)
        p.setFont(f2); p.setPen(QColor(RED))
        p.drawText(QRectF(w - 38, ly - 15, 34, 13), Qt.AlignRight, "MAX")

# ── Circle chart (QPainter) ───────────────────────────────────────────────
class CircleWidget(QWidget):
    def __init__(self, value, lo, hi, color, parent=None):
        super().__init__(parent)
        self.value = value; self.lo = lo; self.hi = hi
        self.color = QColor(color)
        self.setFixedSize(155, 155)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx = cy = self.width() // 2
        R       = cx - 12
        thick   = 14
        pct     = min(self.value / self.hi, 1.5) if self.hi > 0 else 0
        arc_col = QColor(RED) if self.value > self.hi else self.color

        p.setPen(QPen(QColor("#F3F4F6"), thick, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(QRectF(cx - R, cy - R, R*2, R*2), 90*16, -360*16)

        if pct > 0:
            p.setPen(QPen(arc_col, thick, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(QRectF(cx - R, cy - R, R*2, R*2), 90*16, -int(min(pct, 1)*360*16))

        inn = R - thick // 2
        p.setPen(Qt.NoPen); p.setBrush(Qt.white)
        p.drawEllipse(QRectF(cx - inn, cy - inn, inn*2, inn*2))
        p.setBrush(QColor(arc_col.red(), arc_col.green(), arc_col.blue(), 15))
        p.drawEllipse(QRectF(cx - inn, cy - inn, inn*2, inn*2))

        fv = QFont(); fv.setBold(True); fv.setPointSize(15)
        p.setFont(fv); p.setPen(QColor(DARK))
        p.drawText(QRectF(cx - inn, cy - inn - 4, inn*2, inn),
                   Qt.AlignHCenter | Qt.AlignBottom, f"{round(self.value, 1)}g")

        fs = QFont(); fs.setPointSize(9)
        p.setFont(fs); p.setPen(QColor(MUTED))
        p.drawText(QRectF(cx - inn, cy + 2, inn*2, inn),
                   Qt.AlignHCenter | Qt.AlignTop, f"{round(self.lo)}–{round(self.hi)} g")

        fb = QFont(); fb.setBold(True); fb.setPointSize(10)
        p.setFont(fb)
        badge = f"{round(pct * 100)}%"
        bw = QFontMetrics(fb).horizontalAdvance(badge) + 16
        bh = 20; bx = cx - bw // 2; by = cy + inn - 10
        p.setBrush(QColor(arc_col.red(), arc_col.green(), arc_col.blue(), 40))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(bx, by, bw, bh), bh//2, bh//2)
        p.setPen(arc_col)
        p.drawText(QRectF(bx, by, bw, bh), Qt.AlignCenter, badge)

# ── Flow layout (for food chips) ──────────────────────────────────────────
class FlowLayout(QLayout):
    def __init__(self, parent=None, hs=8, vs=8):
        super().__init__(parent)
        self._items = []; self._hs = hs; self._vs = vs

    def addItem(self, item):       self._items.append(item)
    def count(self):               return len(self._items)
    def itemAt(self, i):           return self._items[i] if 0 <= i < len(self._items) else None
    def takeAt(self, i):           return self._items.pop(i) if 0 <= i < len(self._items) else None
    def expandingDirections(self): return Qt.Orientations(0)
    def hasHeightForWidth(self):   return True
    def heightForWidth(self, w):   return self._do_layout(QRect(0, 0, w, 0), True)
    def setGeometry(self, rect):   super().setGeometry(rect); self._do_layout(rect, False)
    def sizeHint(self):            return self.minimumSize()
    def minimumSize(self):
        s = QSize()
        for it in self._items: s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return s + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do_layout(self, rect, test):
        m  = self.contentsMargins()
        x0 = rect.x() + m.left(); y = rect.y() + m.top()
        x  = x0; rh = 0
        for it in self._items:
            sw = it.sizeHint().width() + self._hs
            sh = it.sizeHint().height() + self._vs
            if x + sw > rect.right() + self._hs and rh > 0:
                x = x0; y += rh; rh = 0
            if not test:
                it.setGeometry(QRect(QPoint(x, y), it.sizeHint()))
            x += sw; rh = max(rh, sh)
        return y + rh - rect.y()

# ═══════════════════════════════════════════════════════════════════════════
# PAGES
# ═══════════════════════════════════════════════════════════════════════════

class GenderPage(QWidget):
    chosen = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(80, 50, 80, 50); root.setSpacing(30)

        root.addWidget(lbl("Hej! 👋  Vem är du?", 34, True, DARK, Qt.AlignCenter))
        root.addWidget(lbl("Scanna din könkod", 16, False, MUTED, Qt.AlignCenter))

        cards = QHBoxLayout(); cards.setSpacing(20)
        for emoji, label, bg, border in [
            ("🧒", "Pojke",  BLUE_L,  BLUE_B),
            ("👧", "Flicka", "#FCE7F3", "#F9A8D4"),
            ("🌈", "Annat",  VIOLET_L, VIOLET_B),
        ]:
            c = make_card(bg, border)
            v = QVBoxLayout(c); v.setContentsMargins(20, 22, 20, 22); v.setSpacing(8)
            v.addWidget(lbl(emoji, 54, False, DARK, Qt.AlignCenter))
            v.addWidget(lbl(label, 22, True,  DARK, Qt.AlignCenter))
            c.setMinimumHeight(170)
            cards.addWidget(c)
        root.addLayout(cards)

        self._inp = scanner_field("Scanna könkod: man / kvinna / annan / vill ej ange")
        self._inp.returnPressed.connect(self._submit)
        root.addWidget(self._inp)

        self._err = lbl("", 13, False, RED, Qt.AlignCenter)
        root.addWidget(self._err)
        root.addStretch()

    def showEvent(self, _):
        self._inp.clear()
        QTimer.singleShot(80, self._inp.setFocus)

    def _submit(self):
        raw = self._inp.text().strip().lower()
        self._inp.clear()
        MAP = {"pojke": "man", "flicka": "kvinna", "annat": "annan",
               "vill ej ange": "annan", "man": "man", "kvinna": "kvinna", "annan": "annan"}
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
        root.setContentsMargins(80, 50, 80, 50); root.setSpacing(28)

        root.addWidget(lbl("Hur gammal är du? 🎂", 34, True, DARK, Qt.AlignCenter))
        root.addWidget(lbl("Scanna din ålder", 16, False, MUTED, Qt.AlignCenter))

        self._disp = lbl("—", 88, True, AMBER, Qt.AlignCenter)
        root.addWidget(self._disp)
        root.addWidget(lbl("år", 18, False, MUTED, Qt.AlignCenter))

        self._inp = scanner_field("Scanna ålder (t.ex. 10)...")
        self._inp.textChanged.connect(lambda t: self._disp.setText(t if t.isdigit() else "—"))
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
    calc_requested  = pyqtSignal()
    reset_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.food_list = []
        root = QVBoxLayout(self)
        root.setContentsMargins(60, 30, 60, 30); root.setSpacing(14)

        root.addWidget(lbl("Scanna din frukost! 🍽️", 30, True, DARK, Qt.AlignCenter))
        root.addWidget(lbl("Håll streckkoden mot scannern  ·  scanna 'berakna' när du är klar",
                           14, False, MUTED, Qt.AlignCenter))

        self._inp = scanner_field("📷  Scanna livsmedel...")
        self._inp.textChanged.connect(self._live)
        self._inp.returnPressed.connect(self._submit)
        root.addWidget(self._inp)

        self._fb = lbl("", 14, True, GREEN, Qt.AlignCenter)
        root.addWidget(self._fb)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        scroll.setMaximumHeight(220)
        self._chip_box = QWidget()
        self._chip_box.setStyleSheet("background:transparent;")
        self._flow = FlowLayout(self._chip_box)
        scroll.setWidget(self._chip_box)
        root.addWidget(scroll)
        root.addStretch()

    def reset(self):
        self.food_list = []
        self._inp.clear()
        self._fb.setText("")
        while self._flow.count():
            it = self._flow.takeAt(0)
            if it and it.widget():
                it.widget().deleteLater()
        self._chip_box.update()

    def showEvent(self, _):
        QTimer.singleShot(80, self._inp.setFocus)

    def _live(self, txt):
        key = txt.strip().lower()
        if not key: return
        if key == "reset":              self.reset_requested.emit(); self._inp.clear(); return
        if key in ("berakna","finish"): self.calc_requested.emit();  self._inp.clear(); return
        if key in MY_FOODS:             self._add(key)

    def _submit(self):
        key = self._inp.text().strip().lower()
        self._inp.clear()
        if not key: return
        if key == "reset":              self.reset_requested.emit(); return
        if key in ("berakna","finish"): self.calc_requested.emit();  return
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
        chip = QLabel(f"🌿 {key}")
        chip.setStyleSheet(f"""QLabel{{background:{GREEN_L};border:2px solid {GREEN_B};
            border-radius:13px;padding:5px 13px;color:#065F46;font-weight:bold;font-size:13px;}}""")
        self._flow.addWidget(chip)
        self._chip_box.update()
        QTimer.singleShot(60, self._inp.setFocus)


class ResultsPage(QWidget):
    reset_requested = pyqtSignal()
    new_bkfst       = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 16, 24, 16); outer.setSpacing(12)

        self._title = lbl("Din frukost! 🎉", 26, True, DARK, Qt.AlignCenter)
        outer.addWidget(self._title)

        self._grid_w = QWidget()
        self._grid   = QGridLayout(self._grid_w)
        self._grid.setSpacing(12)
        outer.addWidget(self._grid_w, 1)

        self._inp = scanner_field("Scanna 'ny frukost' eller 'reset'...", VIOLET_B)
        self._inp.textChanged.connect(self._live)
        self._inp.returnPressed.connect(self._submit)
        outer.addWidget(self._inp)
        outer.addWidget(lbl("Scanna 'ny frukost' för att mäta igen  ·  'reset' för att börja om",
                            12, False, MUTED, Qt.AlignCenter))

    def showEvent(self, _):
        QTimer.singleShot(80, self._inp.setFocus)

    def _live(self, txt):
        key = txt.strip().lower()
        if key == "reset":                     self.reset_requested.emit(); self._inp.clear()
        elif key in ("ny frukost","nyfrukost"): self.new_bkfst.emit();       self._inp.clear()

    def _submit(self):
        key = self._inp.text().strip().lower()
        self._inp.clear()
        if key == "reset":                     self.reset_requested.emit()
        elif key in ("ny frukost","nyfrukost"): self.new_bkfst.emit()

    def load(self, res, n):
        self._title.setText(f"Din frukost! 🎉   ({n} livsmedel)")
        while self._grid.count():
            it = self._grid.takeAt(0)
            if it and it.widget(): it.widget().deleteLater()

        def card_vbox(bg, border):
            c = make_card(bg, border)
            v = QVBoxLayout(c); v.setContentsMargins(14, 12, 14, 12); v.setSpacing(5)
            return c, v

        # Energy
        c, v = card_vbox(AMBER_L, AMBER_B)
        v.addWidget(lbl("⚡ Energi", 17, True, "#92400E"))
        v.addWidget(hline(AMBER_B))
        st, sc = get_status(res["kcal"], res["kcal_min"], res["kcal_max"])
        v.addWidget(lbl(st, 12, True, sc))
        v.addWidget(lbl(f"{round(res['kcal'])} kcal", 32, True, AMBER, Qt.AlignCenter))
        v.addWidget(lbl(f"Mål: {res['kcal_min']}–{res['kcal_max']} kcal", 11, False, "#92400E"))
        v.addWidget(lbl(f"{res['pct']}% av dagsbehovet ({round(res['daily'])} kcal)", 10, False, MUTED))
        self._grid.addWidget(c, 0, 0)

        # Runner
        c, v = card_vbox(BLUE_L, BLUE_B)
        v.addWidget(lbl("🏃 Springgubbe", 17, True, "#1E40AF"))
        v.addWidget(hline(BLUE_B))
        spd = res["speed"]
        v.addWidget(lbl("Lugnt tempo 🐢" if spd >= 1 else ("Bra fart! 🏃" if spd >= .5 else "SUPERSNABB!! 🚀"),
                        12, True, BLUE))
        rw = RunnerWidget(); rw.set_speed(spd)
        wrap = QWidget(); wrap.setStyleSheet("background:transparent;")
        wl = QHBoxLayout(wrap); wl.addStretch(); wl.addWidget(rw); wl.addStretch()
        v.addWidget(wrap)
        self._grid.addWidget(c, 0, 1)

        # Distance
        dv, du = fmt_dist(res["dist_m"])
        c, v = card_vbox(VIOLET_L, VIOLET_B)
        v.addWidget(lbl("📍 Distans", 17, True, "#5B21B6"))
        v.addWidget(hline(VIOLET_B))
        v.addWidget(lbl("Du kan springa...", 11, False, MUTED))
        v.addWidget(lbl(f"{dv} {du}", 32, True, VIOLET, Qt.AlignCenter))
        v.addWidget(lbl("Ungefär till:", 11, False, MUTED))
        v.addWidget(lbl(res["place"], 14, True, "#4C1D95"))
        self._grid.addWidget(c, 0, 2)

        # Sugar
        ok = res["sug"] <= res["sug_max"]
        c, v = card_vbox(SUGAR_L if ok else ROSE_L, GREEN_B if ok else ROSE_B)
        v.addWidget(lbl("🍬 Socker", 17, True, "#065F46" if ok else "#9F1239"))
        v.addWidget(hline(GREEN_B if ok else ROSE_B))
        st, sc = get_status(res["sug"], 0.001, res["sug_max"])
        v.addWidget(lbl(st, 12, True, sc))
        v.addWidget(lbl(f"{round(res['sug'],1)} g  /  max {res['sug_max']} g", 11, False, MUTED))
        v.addWidget(SugarWidget(res["sug"], res["sug_max"]))
        self._grid.addWidget(c, 1, 0)

        # Fat
        c, v = card_vbox(ORANGE_L, ORANGE_B)
        v.addWidget(lbl("🧈 Fett", 17, True, "#9A3412"))
        v.addWidget(hline(ORANGE_B))
        st, sc = get_status(res["fat"], res["fat_min"], res["fat_max"])
        v.addWidget(lbl(st, 12, True, sc))
        fw = QWidget(); fw.setStyleSheet("background:transparent;")
        fl = QHBoxLayout(fw); fl.addStretch()
        fl.addWidget(CircleWidget(res["fat"], res["fat_min"], res["fat_max"], ORANGE))
        fl.addStretch(); v.addWidget(fw)
        v.addWidget(lbl(f"Dagsbudget: {res['fat_min_d']}–{res['fat_max_d']} g", 10, False, MUTED, Qt.AlignCenter))
        self._grid.addWidget(c, 1, 1)

        # Protein
        c, v = card_vbox(BLUE_L, BLUE_B)
        v.addWidget(lbl("💪 Protein", 17, True, "#1E3A8A"))
        v.addWidget(hline(BLUE_B))
        st, sc = get_status(res["prot"], res["pro_min"], res["pro_max"])
        v.addWidget(lbl(st, 12, True, sc))
        pw = QWidget(); pw.setStyleSheet("background:transparent;")
        pl = QHBoxLayout(pw); pl.addStretch()
        pl.addWidget(CircleWidget(res["prot"], res["pro_min"], res["pro_max"], BLUE))
        pl.addStretch(); v.addWidget(pw)
        v.addWidget(lbl(f"Dagsbudget: {res['pro_min_d']}–{res['pro_max_d']} g", 10, False, MUTED, Qt.AlignCenter))
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
        self._age    = None
        self._tsec   = 60
        self._tactive = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setFixedHeight(62)
        hdr.setStyleSheet("background:white;border-bottom:4px solid #FCD34D;")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(24, 0, 24, 0)
        hl.addWidget(lbl("🍳 Frukostdatorn", 20, True, AMBER))
        hl.addStretch()
        self._step_labels = []
        for s in ("👤 Vem", "🔢 Ålder", "🍎 Frukost", "✨ Resultat"):
            lb = QLabel(s)
            lb.setStyleSheet("background:#F3F4F6;color:#9CA3AF;border-radius:11px;"
                             "padding:4px 12px;font-weight:bold;font-size:12px;")
            hl.addWidget(lb)
            self._step_labels.append(lb)
        hl.addStretch()
        self._tlbl = lbl("", 11, False, MUTED)
        hl.addWidget(self._tlbl)
        root.addWidget(hdr)

        # Timer strip
        self._tbar_bg = QWidget(); self._tbar_bg.setFixedHeight(4)
        self._tbar_bg.setStyleSheet("background:#F3F4F6;")
        self._tbar = QWidget(self._tbar_bg)
        self._tbar.setStyleSheet("background:#FCD34D;")
        root.addWidget(self._tbar_bg)

        # Pages
        self._stack = QStackedWidget()
        self._p_gender  = GenderPage()
        self._p_age     = AgePage()
        self._p_food    = FoodPage()
        self._p_results = ResultsPage()
        for p in (self._p_gender, self._p_age, self._p_food, self._p_results):
            self._stack.addWidget(p)
        root.addWidget(self._stack)

        # Signals
        self._p_gender.chosen.connect(self._on_gender)
        self._p_age.chosen.connect(self._on_age)
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
        ACTIVE  = f"background:{AMBER_B};color:#78350F;border-radius:11px;padding:4px 12px;font-weight:bold;font-size:12px;"
        DONE    = f"background:{GREEN_L};color:#065F46;border-radius:11px;padding:4px 12px;font-weight:bold;font-size:12px;"
        PENDING = "background:#F3F4F6;color:#9CA3AF;border-radius:11px;padding:4px 12px;font-weight:bold;font-size:12px;"
        for i, lb in enumerate(self._step_labels):
            lb.setStyleSheet(ACTIVE if i == idx else DONE if i < idx else PENDING)

    def _on_gender(self, g):
        self._gender  = g
        self._tactive = True
        self._tsec    = 60
        self._go(1)

    def _on_age(self, a):
        self._age  = a
        self._tsec = 60
        self._p_food.reset()
        self._go(2)

    def _on_calc(self):
        if not self._p_food.food_list: return
        res = calc(MY_FOODS, self._p_food.food_list, self._age, self._gender)
        self._p_results.load(res, len(self._p_food.food_list))
        self._tsec = 60
        self._go(3)

    def _new_bkfst(self):
        self._p_food.reset()
        self._tsec = 60
        self._go(2)

    def _do_reset(self):
        self._gender = None; self._age = None
        self._p_food.reset()
        self._tactive = False; self._tsec = 60
        self._tlbl.setText("")
        self._update_tbar()
        self._go(0)

    def _tick(self):
        if not self._tactive: return
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
