#!/usr/bin/env python3
"""
Miljodatorn – PyQt5 kioskfrontend
All inmatning via streckkodsskanner (eller mus/tangentbord för dev).
Kör:  python3 MiljoQt.py
Helskärm på Pi automatiskt; skicka --window för dev.
"""

import math
import sys

from PyQt5.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
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
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QSizePolicy

import Miljodator

# ── Ladda livsmedelsdata ──────────────────────────────────────────────────
MY_FOODS = Miljodator.get_food_impacts()

# ── Färgpalett (grönt) ────────────────────────────────────────────────────
BG      = "#F2F8F4"
DARK    = "#1C2B1E"
MUTED   = "#5A7360"

GREEN_D = "#166534"
GREEN   = "#22C55E"
GREEN_L = "#DCFCE7"
GREEN_B = "#86EFAC"

TEAL_D  = "#0F766E"
TEAL    = "#14B8A6"
TEAL_L  = "#CCFBF1"
TEAL_B  = "#5EEAD4"

LIME_D  = "#3F6212"
LIME    = "#84CC16"
LIME_L  = "#F7FEE7"
LIME_B  = "#BEF264"

AMBER   = "#D97706"
AMBER_L = "#FEF3C7"
AMBER_B = "#FCD34D"

RED     = "#DC2626"
RED_L   = "#FEE2E2"
RED_B   = "#FCA5A5"

EARTH   = "#78350F"
EARTH_L = "#FEF9C3"

WATER_D = "#1D4ED8"
WATER_L = "#DBEAFE"
WATER_B = "#93C5FD"

# Distinkta färger för segmenten (ett per unikt livsmedel)
SEGMENT_COLORS = [
    "#22C55E", "#14B8A6", "#84CC16", "#F59E0B", "#3B82F6",
    "#8B5CF6", "#EC4899", "#EF4444", "#06B6D4", "#F97316",
    "#10B981", "#6366F1", "#D946EF", "#0EA5E9", "#A3E635",
    "#FB923C", "#E879F9", "#34D399",
]


# ── Hjälpfunktioner ───────────────────────────────────────────────────────
def lbl(text, size=14, bold=False, color=DARK, align=Qt.AlignLeft):
    w = QLabel(text)
    f = QFont()
    f.setPointSize(size)
    f.setBold(bold)
    w.setFont(f)
    # border:none förhindrar att kortets kantlinje ärvs av barnwidgets
    w.setStyleSheet(f"color:{color};background:transparent;border:none;")
    w.setAlignment(align)
    w.setWordWrap(True)
    return w


def hline(color="#D1FAE5"):
    ln = QFrame()
    ln.setFrameShape(QFrame.HLine)
    ln.setFixedHeight(2)
    ln.setStyleSheet(f"background:{color};border:none;max-height:2px;")
    return ln


class ClickableCard(QFrame):
    """Kortwidget med synlig kantlinje BARA på sig själv."""
    clicked = pyqtSignal()

    def __init__(self, bg, border, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._bg     = bg
        self._border = border
        self._apply_style()
        self.setCursor(Qt.PointingHandCursor)

    def _apply_style(self):
        # QFrame[card='1'] matchar bara detta kort, inte barnwidgets
        self.setStyleSheet(
            f"QFrame[card='1']{{background:{self._bg};"
            f"border:2px solid {self._border};border-radius:14px;}}"
        )
        self.setProperty("card", "1")

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        self.clicked.emit()


def make_card(bg, border):
    return ClickableCard(bg, border)


def scanner_field(placeholder, color=GREEN_B):
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    e.setStyleSheet(
        f"QLineEdit{{background:white;border:4px solid {color};border-radius:16px;"
        f"padding:14px 22px;font-size:20px;font-weight:bold;color:{DARK};}}"
        f"QLineEdit:focus{{border-color:{GREEN};}}"
    )
    return e


_qr_cache: dict = {}


def make_qr_pixmap(data: str, size: int = 150) -> QPixmap:
    key = (data, size)
    if key in _qr_cache:
        return _qr_cache[key]
    try:
        from io import BytesIO
        import qrcode
        img = qrcode.make(data)
        img = img.resize((size, size))
        buf = BytesIO()
        img.save(buf, format="PNG")
        px = QPixmap()
        px.loadFromData(buf.getvalue())
    except Exception:
        px = QPixmap(size, size)
        px.fill(QColor("#E5E7EB"))
    _qr_cache[key] = px
    return px


# ── Staplad donut-widget ──────────────────────────────────────────────────
class StackedDonutWidget(QWidget):
    """
    En donut-/ringdiagram där varje unikt livsmedel får ett färgat bågssegment
    som adderar till 100 %. Totalvärdet och enheten visas i mitten.
    En färgkodad förklaring med livsmedelskortnamn + värde visas nedanför.

    breakdown  : lista av {name, count, CO2, Land, Water}
    metric     : "CO2" | "Land" | "Water"
    total      : det redan beräknade totala värdet (float)
    unit       : visningssträng, t.ex. "kg CO2e"
    color_map  : {livsmedelsnamn: hex_färgstr}
    """

    LEGEND_ROW = 20   # px per förklaringsrad
    LEGEND_DOT = 8    # storlek på färgpunkten

    def __init__(self, breakdown: list, metric: str, total: float,
                 unit: str, color_map: dict, parent=None):
        super().__init__(parent)
        self.breakdown = breakdown
        self.metric    = metric
        self.total     = total
        self.unit      = unit
        self.color_map = color_map
        self.setMinimumWidth(260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("background: transparent;")
        def sizeHint(self):
            return QSize(260, self._donut_h + self._legend_h)
        # WA_TranslucentBackground tas bort – orsakar osynlig rendering på barnwidgets

        n = len(breakdown)
        legend_rows = (n + 1) // 2
        self._donut_h  = 200
        self._legend_h = legend_rows * self.LEGEND_ROW + 6
        # setFixedHeight förhindrar att layouten kollapsar widgeten till 0
        self.setFixedHeight(self._donut_h + self._legend_h)

    def paintEvent(self, _):
        if not self.breakdown or self.total <= 0:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()

        # ── Donut-geometri ──────────────────────────────────────────────
        size  = min(w, self._donut_h) - 25
        cx    = w // 2
        cy    = self._donut_h // 2
        R     = max(40, size // 2)         # minst 40 px radie
        thick = max(10, min(R // 4, 30))   # ringtjocklek: 10–30 px, aldrig > R/4

        # Bakgrundscirkel (spår)
        p.setPen(QPen(QColor("#E5E7EB"), thick, Qt.SolidLine, Qt.FlatCap))
        p.drawArc(QRectF(cx - R, cy - R, R * 2, R * 2), 0, 360 * 16)

        # Rita varje segment med start kl 12 (90°), medurs
        start_angle = 90 * 16   # Qt: 90° = klockan 12, positivt = moturs → använd negativa span
        for i, item in enumerate(self.breakdown):
            v    = item[self.metric]
            frac = v / self.total
            span = -int(frac * 360 * 16)   # negativ = medurs

            color = QColor(self.color_map.get(
                item["name"], SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
            ))
            p.setPen(QPen(color, thick, Qt.SolidLine, Qt.FlatCap))
            p.drawArc(QRectF(cx - R, cy - R, R * 2, R * 2), start_angle, span)
            start_angle += span

        # Vit inre cirkel (hålet)
        inn = R - thick // 2 - 2
        p.setPen(Qt.NoPen)
        p.setBrush(Qt.white)
        p.drawEllipse(QRectF(cx - inn, cy - inn, inn * 2, inn * 2))

        # ── Centraltext: totalvärde + enhet ─────────────────────────────
        if self.total < 10:
            val_str = f"{self.total:.2f}"
        elif self.total < 100:
            val_str = f"{self.total:.1f}"
        else:
            val_str = f"{round(self.total)}"

        fv = QFont()
        fv.setBold(True)
        fv.setPointSize(16)
        p.setFont(fv)
        fm = QFontMetrics(fv)
        # Krympa tills det får plats i hålet
        while fm.horizontalAdvance(val_str) > inn * 2 - 10 and fv.pointSize() > 9:
            fv.setPointSize(fv.pointSize() - 1)
            p.setFont(fv)
            fm = QFontMetrics(fv)

        val_h = fm.height()
        p.setPen(QColor(DARK))
        p.drawText(
            QRectF(cx - inn, cy - inn, inn * 2, inn * 2 - val_h // 2),
            Qt.AlignHCenter | Qt.AlignVCenter,
            val_str,
        )

        # Enhet under värdet
        fu = QFont()
        fu.setPointSize(9)
        p.setFont(fu)
        fmu = QFontMetrics(fu)
        unit_h = fmu.height()
        p.setPen(QColor(MUTED))
        p.drawText(
            QRectF(cx - inn, cy + val_h // 2 - 2, inn * 2, unit_h + 4),
            Qt.AlignHCenter | Qt.AlignVCenter,
            self.unit,
        )

        # ── Förklaring nedanför donut ────────────────────────────────────
        fn = QFont()
        fn.setPointSize(8)
        p.setFont(fn)
        fm2 = QFontMetrics(fn)

        legend_y = self._donut_h + 4
        col_w    = w // 2
        dot      = self.LEGEND_DOT

        for i, item in enumerate(self.breakdown):
            col   = i % 2
            row   = i // 2
            lx    = col * col_w
            ly    = legend_y + row * self.LEGEND_ROW
            color = QColor(self.color_map.get(
                item["name"], SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
            ))

            # Färgpunkt
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawEllipse(QRectF(
                lx + 2,
                ly + (self.LEGEND_ROW - dot) / 2,
                dot, dot
            ))

            # Kortnamn + värde
            raw   = item["name"]
            short = (raw
                .replace("fibrer ca 7%", "").replace("fibrer ca 5% typ formfranska", "")
                .replace("fett 1,5% berikad", "").replace("fett 2%", "")
                .replace("fett 80%", "").replace("fett 28%", "")
                .replace("fullkorn", "").replace("m. skal", "")
                .replace("drickf.", "").replace("u. fyllning", "")
                .replace("  ", " ").strip().capitalize()
            )
            v = item[self.metric]
            if v < 10:
                val_str2 = f"{v:.2f} {self.unit}"
            elif v < 100:
                val_str2 = f"{v:.1f} {self.unit}"
            else:
                val_str2 = f"{round(v)} {self.unit}"

            pct_str = f"{round(v / self.total * 100)}%"
            text    = f"{short} {pct_str} ({val_str2})"
            max_px  = col_w - dot - 10
            text    = fm2.elidedText(text, Qt.ElideRight, max_px)

            p.setPen(QColor(DARK))
            p.drawText(
                QRectF(lx + dot + 6, ly, col_w - dot - 8, self.LEGEND_ROW),
                Qt.AlignVCenter | Qt.AlignLeft,
                text,
            )


# ══════════════════════════════════════════════════════════════════════════
# SIDOR
# ══════════════════════════════════════════════════════════════════════════

class FoodPage(QWidget):
    calc_requested  = pyqtSignal()
    reset_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.food_list   = []
        self.food_counts = {}

        # Visningsnamn (singular, plural)
        self.food_display_map = {
            "mellanmjölk fett 1,5% berikad":                ("mjölk",          "mjölk"),
            "fruktyoghurt fett 2%":                         ("yoghurt",        "yoghurt"),
            "apelsinjuice drickf.":                         ("apelsinjuice",   "apelsinjuice"),
            "ägg kokt":                                     ("ägg",            "ägg"),
            "påläggskorv salami rökt":                      ("salami",         "salami"),
            "ost hårdost fett 28%":                         ("ost",            "ost"),
            "smör fett 80%":                                ("smör",           "smör"),
            "jordgubbssylt":                                ("jordgubbssylt",  "jordgubbssylt"),
            "nötkräm chokladkräm":                          ("chokladkräm",    "chokladkräm"),
            "bröd fullkorn råg fibrer ca 7%":               ("mörkt bröd",     "mörkt bröd"),
            "bröd vitt fibrer ca 5% typ formfranska":       ("ljust bröd",     "ljust bröd"),
            "havregryn fullkorn":                           ("havregryn",      "havregryn"),
            "frukostflingor müsli fullkorn m. frukt":       ("müsli",          "müsli"),
            "frukostflingor ris puffat m. socker berikad":  ("flingor",        "flingor"),
            "mjölkchoklad":                                 ("mjölkchoklad",   "mjölkchoklad"),
            "munk u. fyllning":                             ("munk",           "munkar"),
            "äpple m. skal":                                ("äpple",          "äpplen"),
            "banan":                                        ("banan",          "bananer"),
        }

        root = QVBoxLayout(self)
        root.setContentsMargins(60, 30, 60, 30)
        root.setSpacing(14)

        root.addWidget(lbl("Scanna din mat! 🌿", 30, True, GREEN_D, Qt.AlignCenter))
        root.addWidget(lbl(
            "Scanna matvarorna i hyllan  ·  scanna Beräkna när du är klar",
            14, False, MUTED, Qt.AlignCenter,
        ))

        self._inp = scanner_field("📷  Scanna livsmedel...")
        self._inp.textChanged.connect(self._live)
        self._inp.returnPressed.connect(self._submit)
        root.addWidget(self._inp)

        action_row = QHBoxLayout()
        action_row.setSpacing(16)
        for label, code, txt_col, bg, border in [
            ("✅ Beräkna",  "beräkna", "#065F46", GREEN_L, GREEN_B),
            ("↺ Börja om", "reset",   "#9F1239", RED_L,   RED_B),
        ]:
            c = make_card(bg, border)
            v = QVBoxLayout(c)
            v.setContentsMargins(14, 10, 14, 10)
            v.setSpacing(6)
            v.addWidget(lbl(label, 14, True, txt_col, Qt.AlignCenter))
            ql = QLabel()
            ql.setAlignment(Qt.AlignCenter)
            ql.setStyleSheet("border:none;background:transparent;")
            ql.setPixmap(make_qr_pixmap(code, 120))
            v.addWidget(ql)
            c.clicked.connect(lambda checked=False, k=code: self._inp.setText(k))
            action_row.addWidget(c)
        root.addLayout(action_row)

        self._fb = lbl("", 14, True, GREEN, Qt.AlignCenter)
        root.addWidget(self._fb)

        self._list_lbl = QLabel("")
        self._list_lbl.setWordWrap(True)
        self._list_lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._list_lbl.setStyleSheet(
            f"color:{DARK};background:transparent;border:none;font-size:15px;"
        )
        root.addWidget(self._list_lbl)
        root.addStretch()

    def reset(self):
        self.food_list   = []
        self.food_counts = {}
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
        if key in ("beräkna", "berakna", "finish"):
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
        if key in ("beräkna", "berakna", "finish"):
            self.calc_requested.emit()
            return
        if key in MY_FOODS:
            self._add(key)
        else:
            self._fb.setStyleSheet(f"color:{RED};background:transparent;border:none;")
            self._fb.setText(f'Hittades inte: "{key}"')

    def _add(self, key):
        self.food_list.append(key)
        self.food_counts[key] = self.food_counts.get(key, 0) + 1
        self._inp.clear()
        self._fb.setStyleSheet(f"color:{GREEN_D};background:transparent;border:none;")
        singular, _ = self.food_display_map.get(key, (key, key))
        self._fb.setText(f"✅  Tillagd: {singular}!")

        lines = []
        for food, count in self.food_counts.items():
            singular, plural = self.food_display_map.get(food, (food, food))
            name = singular if count == 1 else plural
            lines.append(f"  {count} × {name}")
        self._list_lbl.setText("\n".join(lines))
        QTimer.singleShot(60, self._inp.setFocus)


class ResultsPage(QWidget):
    reset_requested = pyqtSignal()
    new_scan        = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 16, 24, 16)
        outer.setSpacing(10)

        self._title = lbl("Miljöpåverkan per kg 🌍", 24, True, GREEN_D, Qt.AlignCenter)
        outer.addWidget(self._title)

        self._grid_w = QWidget()
        self._grid_w.setStyleSheet("background:transparent;border:none;")
        self._grid   = QGridLayout(self._grid_w)
        self._grid.setSpacing(14)
        outer.addWidget(self._grid_w, 1)

        self._inp = scanner_field("Scanna koden på skärmen...", TEAL_B)
        self._inp.textChanged.connect(self._live)
        self._inp.returnPressed.connect(self._submit)
        outer.addWidget(self._inp)

        action_row = QHBoxLayout()
        action_row.setSpacing(16)
        for label, code, txt_col, bg, border in [
            ("🍳 Ny scanning",  "ny scanning", "#065F46", GREEN_L, GREEN_B),
            ("↺ Börja om",     "reset",        "#9F1239", RED_L,   RED_B),
        ]:
            c = make_card(bg, border)
            v = QVBoxLayout(c)
            v.setContentsMargins(14, 10, 14, 10)
            v.setSpacing(6)
            v.addWidget(lbl(label, 14, True, txt_col, Qt.AlignCenter))
            ql = QLabel()
            ql.setAlignment(Qt.AlignCenter)
            ql.setStyleSheet("border:none;background:transparent;")
            ql.setPixmap(make_qr_pixmap(code, 120))
            v.addWidget(ql)
            c.clicked.connect(lambda checked=False, k=code: self._inp.setText(k))
            action_row.addWidget(c)
        outer.addLayout(action_row)

    def showEvent(self, _):
        QTimer.singleShot(80, self._inp.setFocus)

    def _live(self, txt):
        key = txt.strip().lower()
        if key == "reset":
            self.reset_requested.emit()
            self._inp.clear()
        elif key == "ny scanning":
            self.new_scan.emit()
            self._inp.clear()

    def _submit(self):
        key = self._inp.text().strip().lower()
        self._inp.clear()
        if key == "reset":
            self.reset_requested.emit()
        elif key == "ny scanning":
            self.new_scan.emit()

    def load(self, res: dict, n: int):
        self._title.setText(f"Miljöpåverkan per kg 🌍   ({n} livsmedel)")

        while self._grid.count():
            it = self._grid.takeAt(0)
            if it and it.widget():
                it.widget().deleteLater()

        breakdown = res["breakdown"]

        # Tilldela en stabil färg per unikt livsmedel
        color_map = {
            item["name"]: SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
            for i, item in enumerate(breakdown)
        }

        def card_vbox(bg, border):
            c = make_card(bg, border)
            v = QVBoxLayout(c)
            v.setContentsMargins(16, 14, 16, 14)
            v.setSpacing(6)
            return c, v

        # ── CO2-kort ──────────────────────────────────────────────────────
        c, v = card_vbox(GREEN_L, GREEN_B)
        v.addWidget(lbl("🌱 CO₂-ekvivalenter", 17, True, GREEN_D))
        v.addWidget(hline(GREEN_B))
        v.addWidget(lbl(f"Totalt: {res['co2']:.4f} kg CO₂e / kg",
                        12, True, MUTED, Qt.AlignCenter))
        v.addWidget(
            StackedDonutWidget(breakdown, "CO2", res["co2"], "kg CO₂e", color_map),
            0, Qt.AlignCenter,
        )
        self._grid.addWidget(c, 0, 0)

        # ── Markkort ──────────────────────────────────────────────────────
        c, v = card_vbox(EARTH_L, AMBER_B)
        v.addWidget(lbl("🌾 Markanvändning", 17, True, EARTH))
        v.addWidget(hline(AMBER_B))
        v.addWidget(lbl(f"Totalt: {res['land']:.4f} m²/år / kg",
                        12, True, MUTED, Qt.AlignCenter))
        v.addWidget(
            StackedDonutWidget(breakdown, "Land", res["land"], "m²/år", color_map),
            0, Qt.AlignCenter,
        )
        self._grid.addWidget(c, 0, 1)

        # ── Vattenkort ────────────────────────────────────────────────────
        c, v = card_vbox(WATER_L, WATER_B)
        v.addWidget(lbl("💧 Vattenanvändning", 17, True, WATER_D))
        v.addWidget(hline(WATER_B))
        v.addWidget(lbl(f"Totalt: {res['water']:.3f} liter / kg",
                        12, True, MUTED, Qt.AlignCenter))
        v.addWidget(
            StackedDonutWidget(breakdown, "Water", res["water"], "liter", color_map),
            0, Qt.AlignCenter,
        )
        self._grid.addWidget(c, 0, 2)

        QTimer.singleShot(80, self._inp.setFocus)


# ══════════════════════════════════════════════════════════════════════════
# HUVUDFÖNSTER
# ══════════════════════════════════════════════════════════════════════════

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Miljodatorn")
        self.setStyleSheet(f"QWidget{{background:{BG};}}")
        self._tsec    = 200
        self._tactive = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidhuvud ──────────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setFixedHeight(62)
        hdr.setStyleSheet("background:white;border-bottom:4px solid #86EFAC;")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(24, 0, 24, 0)

        logo = QLabel()
        logo_px = QPixmap("logga_magasinet.png")
        if not logo_px.isNull():
            logo.setPixmap(
                logo_px.scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        logo.setStyleSheet("background:transparent;border:none;")
        hl.addWidget(logo)

        hl.addWidget(lbl(" Miljödatorn 🌍", 20, True, GREEN_D))
        hl.addStretch()

        self._step_labels = []
        for s in ("🍎 Mat", "🌿 Resultat"):
            lb = QLabel(s)
            lb.setStyleSheet(
                "background:#F3F4F6;color:#9CA3AF;border-radius:11px;"
                "padding:4px 12px;font-weight:bold;font-size:12px;border:none;"
            )
            hl.addWidget(lb)
            self._step_labels.append(lb)
        hl.addStretch()

        right_box = QWidget()
        right_box.setStyleSheet("background:transparent;border:none;")
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._source_lbl = lbl("Källa: SAFAD (SLU)", 11, False, MUTED, Qt.AlignRight)
        self._tlbl       = lbl("", 11, False, MUTED, Qt.AlignRight)
        self._tlbl.setFixedWidth(160)
        self._source_lbl.setFixedWidth(160)

        right_layout.addWidget(self._tlbl)
        right_layout.addWidget(self._source_lbl)
        hl.addWidget(right_box)
        root.addWidget(hdr)

        # ── Tidsstapel ────────────────────────────────────────────────────
        self._tbar_bg = QWidget()
        self._tbar_bg.setFixedHeight(4)
        self._tbar_bg.setStyleSheet("background:#F3F4F6;border:none;")
        self._tbar = QWidget(self._tbar_bg)
        self._tbar.setStyleSheet("background:#86EFAC;border:none;")
        root.addWidget(self._tbar_bg)

        # ── Sidor ─────────────────────────────────────────────────────────
        self._stack     = QStackedWidget()
        self._p_food    = FoodPage()
        self._p_results = ResultsPage()
        for p in (self._p_food, self._p_results):
            self._stack.addWidget(p)
        root.addWidget(self._stack)

        # ── Signaler ──────────────────────────────────────────────────────
        self._p_food.calc_requested.connect(self._on_calc)
        self._p_food.reset_requested.connect(self._do_reset)
        self._p_results.reset_requested.connect(self._do_reset)
        self._p_results.new_scan.connect(self._new_scan)

        self._atimer = QTimer(self)
        self._atimer.timeout.connect(self._tick)
        self._atimer.start(1000)
        self._go(0)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update_tbar()

    def _go(self, idx: int):
        self._source_lbl.setVisible(idx == 1)
        self._stack.setCurrentIndex(idx)
        ACTIVE  = (f"background:{GREEN_B};color:{GREEN_D};border-radius:11px;"
                   "padding:4px 12px;font-weight:bold;font-size:12px;border:none;")
        DONE    = (f"background:{GREEN_L};color:#065F46;border-radius:11px;"
                   "padding:4px 12px;font-weight:bold;font-size:12px;border:none;")
        PENDING = ("background:#F3F4F6;color:#9CA3AF;border-radius:11px;"
                   "padding:4px 12px;font-weight:bold;font-size:12px;border:none;")
        for i, lb in enumerate(self._step_labels):
            lb.setStyleSheet(ACTIVE if i == idx else DONE if i < idx else PENDING)

    def _on_calc(self):
        if not self._p_food.food_list:
            return
        res = Miljodator.calc(MY_FOODS, self._p_food.food_list)
        self._p_results.load(res, len(self._p_food.food_list))
        self._tactive = True
        self._tsec    = 200
        self._go(1)

    def _new_scan(self):
        self._p_food.reset()
        self._tsec = 200
        self._go(0)

    def _do_reset(self):
        self._p_food.reset()
        self._tactive = False
        self._tsec    = 200
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
        pct = (self._tsec / 200) if self._tactive else 1.0
        self._tbar.setGeometry(0, 0, int(self._tbar_bg.width() * pct), 4)


# ── Startpunkt ────────────────────────────────────────────────────────────
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