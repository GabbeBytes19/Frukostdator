#!/usr/bin/env python3
"""
Miljodatorn – PyQt5 kioskfrontend
All inmatning via streckkodsskanner (eller mus/tangentbord för dev).
Kör:  python3 MiljoQt.py
Helskärm på Pi automatiskt; skicka --window för dev.
"""

import sys

from PyQt5.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
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

import Miljodator

# ── Ladda livsmedelsdata ──────────────────────────────────────────────────
MY_FOODS = Miljodator.get_food_impacts()
_BARCODE_MAP = Miljodator.build_barcode_map(MY_FOODS)

# ── Färgpalett ────────────────────────────────────────────────────────────
BG       = "#F2F6F3"
DARK     = "#1A2B1E"
MUTED    = "#4A6655"

PRIMARY  = "#548665"
PRIMARY_L= "#E4EDE7"
PRIMARY_B= "#6D9077"

ACCENT   = "#3D6B50"
ACCENT_L = "#D6E5DA"
ACCENT_B = "#97AA9B"

LOGO_TEAL = "#005850"

MAUVE    = "#5C3D7A"
MAUVE_L  = "#EDE8F4"
MAUVE_B  = "#9B7DC0"

EARTH    = "#7A4F1A"
EARTH_L  = "#FBF0E0"
EARTH_B  = "#C49040"

WATER_D  = "#1A4F7A"
WATER_L  = "#DDF0FB"
WATER_B  = "#7BB8D8"

RED      = "#C0392B"
RED_L    = "#FDECEA"
RED_B    = "#E8857C"

SEGMENT_COLORS = [
    "#4CAF50", "#2196F3", "#FF9800", "#9C27B0", "#00BCD4",
    "#F44336", "#8BC34A", "#FF5722", "#3F51B5", "#009688",
    "#FFC107", "#E91E63", "#607D8B", "#795548", "#CDDC39",
    "#03A9F4", "#FF4081", "#69F0AE",
]

# ── WWF one planet plate threshold ───────────────────────────────────────
WWF_CO2_LIMIT = 0.5   # kg CO2e per måltid

# ── Verkliga jämförelser per enhet ────────────────────────────────────────
def co2_comparison(kg: float) -> str:
    km = kg / 0.21
    if km < 1:
        m = round(km * 1000)
        return f"≈ {m} m bilkörning"
    return f"≈ {km:.1f} km bilkörning"

def land_comparison(m2: float) -> str:
    A4 = 0.0623
    sheets_raw = m2 / A4
    sheets = round(sheets_raw * 2) / 2
    if sheets == int(sheets):
        sheets_str = str(int(sheets))
    else:
        sheets_str = f"{sheets:.1f}".replace(".", ",")
    return f"≈ {sheets_str} A4 papper"

def water_comparison(liters: float) -> str:
    mins = liters / 9.0
    if mins < 1:
        return f"≈ {round(liters)} liter vatten"
    return f"≈ {mins:.1f} minuter duschning"


# ── Hjälpfunktioner ───────────────────────────────────────────────────────
def lbl(text, size=14, bold=False, color=DARK, align=Qt.AlignLeft):
    w = QLabel(text)
    f = QFont()
    f.setPointSize(size)
    f.setBold(bold)
    w.setFont(f)
    w.setStyleSheet(f"color:{color};background:transparent;border:none;")
    w.setAlignment(align)
    w.setWordWrap(True)
    return w


def hline(color=None):
    if color is None:
        color = PRIMARY_B
    ln = QFrame()
    ln.setFrameShape(QFrame.HLine)
    ln.setFixedHeight(2)
    ln.setStyleSheet(f"background:{color};border:none;max-height:2px;")
    return ln


class ClickableCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, bg, border, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._bg     = bg
        self._border = border
        self._apply_style()
        self.setCursor(Qt.PointingHandCursor)

    def _apply_style(self):
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


def scanner_field(placeholder, color=None):
    if color is None:
        color = PRIMARY_B
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    e.setStyleSheet(
        f"QLineEdit{{background:white;border:4px solid {color};border-radius:16px;"
        f"padding:14px 22px;font-size:20px;font-weight:bold;color:{DARK};}}"
        f"QLineEdit:focus{{border-color:{PRIMARY};}}"
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


# ══════════════════════════════════════════════════════════════════════════
# PLANET WIDGET  (ny funktion – WWF one planet plate)
# ══════════════════════════════════════════════════════════════════════════

class PlanetWidget(QWidget):
    """
    Visar en animerad planet och ett budskap baserat på om måltiden
    ligger under eller över WWF:s gräns för "One Planet Plate" (0,5 kg CO2e).

    Under gränsen → grön glad planet med leende
    Över gränsen  → röd/orange ledsen planet med rök-/flammografik
    Pulsanimation gör planeten levande.
    """

    ANIM_MS = 40   # timer-intervall i ms

    def __init__(self, co2_kg: float, parent=None):
        super().__init__(parent)
        self.co2_kg = co2_kg
        self._good  = co2_kg <= WWF_CO2_LIMIT
        self._t     = 0.0          # animationsparameter 0..2π

        self.setFixedHeight(160)
        self.setMinimumWidth(400)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._anim = QTimer(self)
        self._anim.timeout.connect(self._tick)
        self._anim.start(self.ANIM_MS)

    def _tick(self):
        import math
        self._t = (self._t + 0.06) % (2 * math.pi)
        self.update()

    def paintEvent(self, _):
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # ── Planeten ──────────────────────────────────────────────────────
        pulse = math.sin(self._t) * 3          # ±3 px puls
        R     = int(h * 0.38) + int(pulse)
        cx    = w // 2
        cy    = h // 2 + 5

        if self._good:
            planet_col  = QColor("#27AE60")
            shadow_col  = QColor("#1E8449")
            shine_col   = QColor("#A9DFBF")
            bg_glow     = QColor(39, 174, 96, 30)
        else:
            planet_col  = QColor("#E74C3C")
            shadow_col  = QColor("#C0392B")
            shine_col   = QColor("#F1948A")
            bg_glow     = QColor(231, 76, 60, 30)

        # Glöd-ring runt planeten
        for r_off in range(18, 0, -2):
            alpha = int(40 * (1 - r_off / 18))
            glow = QColor(planet_col)
            glow.setAlpha(alpha)
            p.setPen(Qt.NoPen)
            p.setBrush(glow)
            p.drawEllipse(QRectF(cx - R - r_off, cy - R - r_off,
                                 (R + r_off) * 2, (R + r_off) * 2))

        # Planetshadow
        p.setPen(Qt.NoPen)
        p.setBrush(shadow_col)
        p.drawEllipse(QRectF(cx - R + 4, cy - R + 6, R * 2, R * 2))

        # Planetkropp
        p.setBrush(planet_col)
        p.drawEllipse(QRectF(cx - R, cy - R, R * 2, R * 2))

        # Glansreflex uppe till vänster
        p.setBrush(shine_col)
        sr = int(R * 0.35)
        p.drawEllipse(QRectF(cx - R + int(R * 0.15), cy - R + int(R * 0.10), sr, int(sr * 0.65)))

        # ── Ansikte ───────────────────────────────────────────────────────
        eye_r = max(3, R // 8)
        eye_y = cy - R // 5
        eye_off = R // 3

        p.setBrush(QColor("white"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(cx - eye_off - eye_r, eye_y - eye_r, eye_r * 2, eye_r * 2))
        p.drawEllipse(QRectF(cx + eye_off - eye_r, eye_y - eye_r, eye_r * 2, eye_r * 2))

        pupil_r = max(2, eye_r // 2)
        p.setBrush(QColor("#1A1A1A"))
        if self._good:
            p.drawEllipse(QRectF(cx - eye_off - pupil_r, eye_y - pupil_r, pupil_r * 2, pupil_r * 2))
            p.drawEllipse(QRectF(cx + eye_off - pupil_r, eye_y - pupil_r, pupil_r * 2, pupil_r * 2))
        else:
            # Arga ögonbryn + pupiller nedåt
            brow_pen = QPen(QColor("#1A1A1A"), max(2, eye_r // 3))
            brow_pen.setCapStyle(Qt.RoundCap)
            p.setPen(brow_pen)
            # vänster ögonbryn lutande ner mot mitten
            p.drawLine(int(cx - eye_off - eye_r), int(eye_y - eye_r - 3),
                       int(cx - eye_off + eye_r), int(eye_y - eye_r + 3))
            # höger ögonbryn
            p.drawLine(int(cx + eye_off - eye_r), int(eye_y - eye_r + 3),
                       int(cx + eye_off + eye_r), int(eye_y - eye_r - 3))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#1A1A1A"))
            p.drawEllipse(QRectF(cx - eye_off - pupil_r, eye_y, pupil_r * 2, pupil_r * 2))
            p.drawEllipse(QRectF(cx + eye_off - pupil_r, eye_y, pupil_r * 2, pupil_r * 2))

        # Mun
        mouth_y = cy + R // 4
        mouth_w = R // 2
        mouth_pen = QPen(QColor("white"), max(2, R // 10))
        mouth_pen.setCapStyle(Qt.RoundCap)
        p.setPen(mouth_pen)
        p.setBrush(Qt.NoBrush)
        if self._good:
            # Leende bågmun
            from PyQt5.QtCore import QRect
            p.drawArc(QRect(cx - mouth_w, mouth_y - mouth_w // 2,
                            mouth_w * 2, mouth_w),
                      200 * 16, 140 * 16)
        else:
            # Sur nedåtbågmun
            from PyQt5.QtCore import QRect
            p.drawArc(QRect(cx - mouth_w, mouth_y,
                            mouth_w * 2, mouth_w),
                      20 * 16, 140 * 16)

        # ── Extra grafik beroende på läge ─────────────────────────────────
        if self._good:
            # Stjärnor runt planeten
            star_data = [(-R*1.6, -R*0.6), (R*1.5, -R*0.8), (-R*1.3, R*0.5), (R*1.4, R*0.3)]
            star_pulse = math.sin(self._t * 1.5)
            for sx_off, sy_off in star_data:
                sx = cx + int(sx_off)
                sy = cy + int(sy_off)
                sr2 = max(3, int(5 + star_pulse * 1.5))
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#F9E79F"))
                self._draw_star(p, sx, sy, sr2)

        # ── Textbanner till höger av planeten ─────────────────────────────
        text_x = cx + R + 26
        text_w = w - text_x - 10

        if self._good:
            badge_bg  = QColor("#D5F5E3")
            badge_brd = QColor(PRIMARY)
            head_col  = QColor(PRIMARY)
            head_text = "🌍  One Planet Plate!"
            sub_text  = (f"Din måltid släpper ut {self.co2_kg:.2f} kg CO₂e -\n"
                         f"under WWF:s gräns på {WWF_CO2_LIMIT} kg.\nBra jobbat!")
        else:
            badge_bg  = QColor("#FADBD8")
            badge_brd = QColor(RED)
            head_col  = QColor(RED)
            head_text = "🌡️  Över One Planet Plate"
            sub_text  = (f"Din måltid släpper ut {self.co2_kg:.2f} kg CO₂e -\n"
                         f"WWF:s mål är under {WWF_CO2_LIMIT} kg.\n"
                         f"Prova att byta ut något!")

        # Badge-bakgrund
        bpad = 12
        badge_rect = QRectF(text_x - bpad, cy - 58, text_w + bpad, 116)
        p.setBrush(badge_bg)
        p.setPen(QPen(badge_brd, 2))
        p.drawRoundedRect(badge_rect, 14, 14)

        # Rubrik
        fh = QFont()
        fh.setBold(True)
        fh.setPointSize(15)
        p.setFont(fh)
        p.setPen(head_col)
        p.drawText(QRectF(text_x, cy - 50, text_w, 28), Qt.AlignVCenter | Qt.AlignLeft, head_text)

        # Brödtext
        fs = QFont()
        fs.setPointSize(11)
        p.setFont(fs)
        p.setPen(QColor(DARK))
        p.drawText(QRectF(text_x, cy - 18, text_w, 76),
                   Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, sub_text)

    @staticmethod
    def _draw_star(painter, cx, cy, r):
        import math
        from PyQt5.QtCore import QPointF
        from PyQt5.QtGui import QPolygonF
        pts = []
        for i in range(10):
            angle = math.pi / 5 * i - math.pi / 2
            rad   = r if i % 2 == 0 else r * 0.45
            pts.append(QPointF(cx + math.cos(angle) * rad, cy + math.sin(angle) * rad))
        painter.drawPolygon(QPolygonF(pts))

    def closeEvent(self, e):
        self._anim.stop()
        super().closeEvent(e)


# ── Lägesväxlare (kortknapp med QR-kod) ──────────────────────────────────
class ModeToggle(QWidget):
    mode_changed = pyqtSignal(str)

    _LABELS = {
        "meal":   ("📊 Jämför livsmedel per kg",    "byt lage"),
        "per_kg": ("🍽️ Visa din måltid", "byt lage"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = "meal"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._card = make_card(MAUVE_L, MAUVE_B)
        cv = QVBoxLayout(self._card)
        cv.setContentsMargins(14, 10, 14, 10)
        cv.setSpacing(6)

        self._title_lbl = lbl("", 14, True, MAUVE, Qt.AlignCenter)
        cv.addWidget(self._title_lbl)

        self._qr_lbl = QLabel()
        self._qr_lbl.setAlignment(Qt.AlignCenter)
        self._qr_lbl.setStyleSheet("border:none;background:transparent;")
        cv.addWidget(self._qr_lbl)

        self._card.clicked.connect(self._toggle)
        layout.addWidget(self._card)
        self._refresh()

    def _toggle(self):
        self._current = "per_kg" if self._current == "meal" else "meal"
        self._refresh()
        self.mode_changed.emit(self._current)

    def activate_via_scanner(self):
        self._toggle()

    def current(self) -> str:
        return self._current

    def _refresh(self):
        label, code = self._LABELS[self._current]
        self._title_lbl.setText(label)
        self._qr_lbl.setPixmap(make_qr_pixmap(code, 120))


# ── Staplad donut-widget ──────────────────────────────────────────────────
class StackedDonutWidget(QWidget):
    LEGEND_ROW = 20
    LEGEND_DOT = 8

    def __init__(self, breakdown: list, metric: str, total: float,
                 unit: str, color_map: dict, label_map: dict = None,
                 parent=None):
        super().__init__(parent)
        self.breakdown = breakdown
        self.metric    = metric
        self.total     = total
        self.unit      = unit
        self.color_map = color_map
        self.label_map = label_map or {}

        n = len(breakdown)
        legend_rows    = (n + 1) // 2
        self._donut_h  = 200
        self._legend_h = legend_rows * self.LEGEND_ROW + 6
        self.setFixedHeight(self._donut_h + self._legend_h)
        self.setMinimumWidth(300)

    def paintEvent(self, _):
        if not self.breakdown or self.total <= 0:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()

        size  = min(w, self._donut_h) - 25
        cx    = w // 2
        cy    = self._donut_h // 2
        R     = max(40, size // 2)
        thick = max(10, min(R // 4, 30))

        p.setPen(QPen(QColor("#E5E7EB"), thick, Qt.SolidLine, Qt.FlatCap))
        p.drawArc(QRectF(cx - R, cy - R, R * 2, R * 2), 0, 360 * 16)

        start_angle = 90 * 16
        for i, item in enumerate(self.breakdown):
            v    = item[self.metric]
            frac = v / self.total
            span = -int(frac * 360 * 16)
            color = QColor(self.color_map.get(
                item["name"], SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
            ))
            p.setPen(QPen(color, thick, Qt.SolidLine, Qt.FlatCap))
            p.drawArc(QRectF(cx - R, cy - R, R * 2, R * 2), start_angle, span)
            start_angle += span

        inn = R - thick // 2 - 2
        p.setPen(Qt.NoPen)
        p.setBrush(Qt.white)
        p.drawEllipse(QRectF(cx - inn, cy - inn, inn * 2, inn * 2))

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
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawEllipse(QRectF(lx + 2, ly + (self.LEGEND_ROW - dot) / 2, dot, dot))

            raw   = item["name"]
            if raw in self.label_map:
                short = self.label_map[raw].capitalize()
            else:
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
            text    = fm2.elidedText(text, Qt.ElideRight, col_w - dot - 10)
            p.setPen(QColor(DARK))
            p.drawText(
                QRectF(lx + dot + 6, ly, col_w - dot - 8, self.LEGEND_ROW),
                Qt.AlignVCenter | Qt.AlignLeft,
                text,
            )


# ── Horisontellt stapeldiagram (per kg-läge) ──────────────────────────────
class HBarChartWidget(QWidget):
    """
    Visar ett horisontellt stapeldiagram där varje livsmedel får en rad.
    Staplarna är proportionella mot det högsta värdet i serien.
    Samma färger och namnförkortningar som StackedDonutWidget används.
    """

    ROW_H   = 28   # höjd per stapelrad
    ROW_GAP = 6    # mellanrum mellan rader
    LBL_W   = 110  # bredd för livsmedelsnamnet till vänster
    VAL_W   = 68   # bredd för värdetexten till höger
    BAR_R   = 5    # hörnradie på staplarna

    def __init__(self, breakdown: list, metric: str,
                 unit: str, color_map: dict, parent=None):
        super().__init__(parent)
        self.breakdown = breakdown
        self.metric    = metric
        self.unit      = unit
        self.color_map = color_map

        n = len(breakdown)
        total_h = n * (self.ROW_H + self.ROW_GAP) + 4
        self.setFixedHeight(total_h)
        self.setMinimumWidth(260)

    @staticmethod
    def _short_name(raw: str) -> str:
        return (raw
            .replace("fibrer ca 7%", "").replace("fibrer ca 5% typ formfranska", "")
            .replace("fett 1,5% berikad", "").replace("fett 2%", "")
            .replace("fett 80%", "").replace("fett 28%", "")
            .replace("fullkorn", "").replace("m. skal", "")
            .replace("drickf.", "").replace("u. fyllning", "")
            .replace("  ", " ").strip().capitalize()
        )

    def paintEvent(self, _):
        if not self.breakdown:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()

        max_val = max((item[self.metric] for item in self.breakdown), default=1.0)
        if max_val <= 0:
            max_val = 1.0

        bar_area_w = w - self.LBL_W - self.VAL_W - 8

        fn = QFont()
        fn.setPointSize(8)
        p.setFont(fn)
        fm = QFontMetrics(fn)

        for i, item in enumerate(self.breakdown):
            val   = item[self.metric]
            color = QColor(self.color_map.get(
                item["name"], SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
            ))
            y = i * (self.ROW_H + self.ROW_GAP) + 2

            # ── Livsmedelsnamn (vänster) ──────────────────────────────────
            name = self._short_name(item["name"])
            name = fm.elidedText(name, Qt.ElideRight, self.LBL_W - 4)
            p.setPen(QColor(DARK))
            p.drawText(
                QRectF(0, y, self.LBL_W - 4, self.ROW_H),
                Qt.AlignVCenter | Qt.AlignLeft,
                name,
            )

            # ── Bakgrundsspår ─────────────────────────────────────────────
            track_x = self.LBL_W
            track_rect = QRectF(track_x, y + 4, bar_area_w, self.ROW_H - 8)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#E5E7EB"))
            p.drawRoundedRect(track_rect, self.BAR_R, self.BAR_R)

            # ── Färgad stapel ─────────────────────────────────────────────
            frac    = val / max_val
            bar_w   = max(self.BAR_R * 2, int(bar_area_w * frac))
            bar_rect = QRectF(track_x, y + 4, bar_w, self.ROW_H - 8)
            p.setBrush(color)
            p.drawRoundedRect(bar_rect, self.BAR_R, self.BAR_R)

            # ── Värdetext (höger) ─────────────────────────────────────────
            if val < 10:
                val_str = f"{val:.2f} {self.unit}"
            elif val < 100:
                val_str = f"{val:.1f} {self.unit}"
            else:
                val_str = f"{round(val)} {self.unit}"

            val_x = track_x + bar_area_w + 6
            p.setPen(QColor(MUTED))
            p.drawText(
                QRectF(val_x, y, self.VAL_W, self.ROW_H),
                Qt.AlignVCenter | Qt.AlignLeft,
                val_str,
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

        self.food_display_map = {
            "mellanmjölk fett 1,5% berikad":                ("glas mjölk",        "glas mjölk"),
            "fruktyoghurt fett 2%":                         ("skål yoghurt",       "skålar yoghurt"),
            "apelsinjuice drickf.":                         ("glas apelsinjuice",  "glas apelsinjuice"),
            "ägg kokt":                                     ("kokt ägg",           "kokta ägg"),
            "påläggskorv salami rökt":                      ("skiva salami",       "skivor salami"),
            "ost hårdost fett 28%":                         ("skiva ost",          "skivor ost"),
            "smör fett 80%":                                ("klick smör",         "klickar smör"),
            "jordgubbssylt":                                ("msk jordgubbssylt",  "msk jordgubbssylt"),
            "nötkräm chokladkräm":                          ("msk chokladkräm",    "msk chokladkräm"),
            "bröd fullkorn råg fibrer ca 7%":               ("skiva mörkt bröd",   "skivor mörkt bröd"),
            "bröd vitt fibrer ca 5% typ formfranska":       ("skiva ljust bröd",   "skivor ljust bröd"),
            "havregryn fullkorn":                           ("dl havregryn",       "dl havregryn"),
            "frukostflingor müsli fullkorn m. frukt":       ("portion müsli",      "portioner müsli"),
            "frukostflingor ris puffat m. socker berikad":  ("portion flingor",    "portioner flingor"),
            "mjölkchoklad":                                 ("chokladkaka",        "chokladkakor"),
            "munk u. fyllning":                             ("munk",               "munkar"),
            "äpple m. skal":                                ("äpple",              "äpplen"),
            "banan":                                        ("banan",              "bananer"),
        }

        root = QVBoxLayout(self)
        root.setContentsMargins(60, 30, 60, 30)
        root.setSpacing(14)

        root.addWidget(lbl("Scanna din mat! 🌿", 30, True, PRIMARY, Qt.AlignCenter))
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
            ("✅ Beräkna",  "berakna", "#065F46", PRIMARY_L, PRIMARY_B),
            ("↺ Börja om", "reset",   "#5B1F6B", MAUVE_L,   MAUVE_B),
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

        self._fb = lbl("", 14, True, PRIMARY, Qt.AlignCenter)
        root.addWidget(self._fb)

        self._list_lbl = QLabel("")
        self._list_lbl.setWordWrap(True)
        self._list_lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._list_lbl.setStyleSheet(
            f"color:{DARK};background:transparent;border:none;font-size:15px;"
        )
        root.addWidget(self._list_lbl)
        root.addStretch()

        self._scan_buf = ''
        self._buf_timer = QTimer(self)
        self._buf_timer.setSingleShot(True)
        self._buf_timer.timeout.connect(self._clear_scan_buf)

    def _clear_scan_buf(self):
        self._scan_buf = ''

    def reset(self):
        self.food_list   = []
        self.food_counts = {}
        self._scan_buf = ''
        self._buf_timer.stop()
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
        if key in ("beräkna", "berakna", "berkna", "finish"):
            self.calc_requested.emit()
            self._inp.clear()
            return
        key = Miljodator.resolve_scan(key, _BARCODE_MAP)
        if key in MY_FOODS:
            self._add(key)

    def _submit(self):
        fragment = self._inp.text().strip().lower()
        self._inp.clear()
        if not fragment:
            return
        if fragment == "reset":
            self._scan_buf = ''
            self._buf_timer.stop()
            self.reset_requested.emit()
            return
        if fragment in ("beräkna", "berakna", "berkna", "finish"):
            self._scan_buf = ''
            self._buf_timer.stop()
            self.calc_requested.emit()
            return
        combined = (self._scan_buf + fragment).strip()
        key = Miljodator.resolve_scan(combined, _BARCODE_MAP)
        if key in MY_FOODS:
            self._scan_buf = ''
            self._buf_timer.stop()
            self._add(key)
        else:
            self._scan_buf = combined
            self._buf_timer.start(500)

    def _add(self, key):
        self.food_list.append(key)
        self.food_counts[key] = self.food_counts.get(key, 0) + 1
        self._inp.clear()
        self._fb.setStyleSheet(f"color:{PRIMARY};background:transparent;border:none;")
        singular, _ = self.food_display_map.get(key, (key, key))
        self._fb.setText(f"✅  Tillagd: {singular}!")
        lines = []
        for food, count in self.food_counts.items():
            singular, plural = self.food_display_map.get(food, (food, food))
            name = singular if count == 1 else plural
            lines.append(f"  {count} × {name}")
        self._list_lbl.setText("\n".join(lines))
        QTimer.singleShot(60, self._inp.setFocus)


# ── ResultsPage ───────────────────────────────────────────────────────────
class ResultsPage(QWidget):
    new_scan = pyqtSignal()

    CARDS = [
        ("CO2",   "🌱 Växthusgaser (CO₂e)", "kg CO₂e", PRIMARY_L, PRIMARY_B, PRIMARY,   co2_comparison),
        ("Land",  "🌾 Markanvändning",       "m²/år",   EARTH_L,   EARTH_B,   EARTH,     land_comparison),
        ("Water", "💧 Färskvatten",          "liter",   WATER_L,   WATER_B,   WATER_D,   water_comparison),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_mode   = "meal"
        self._last_food_list = []
        self._planet_widget  = None   # hålls i minnet för att stoppa animatorn

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 16, 24, 16)
        outer.setSpacing(10)

        # Rubrik
        self._title = lbl(
            "Så mycket klimatpåverkan har din måltid",
            24, True, PRIMARY, Qt.AlignCenter,
        )
        outer.addWidget(self._title)

        self._subtitle = lbl(
            "Baserat på portionsstorlek och antal",
            14, False, MUTED, Qt.AlignCenter,
        )
        outer.addWidget(self._subtitle)

        # ── Planet-banner-plats (byts ut vid render) ──────────────────────
        # stretch=1 → planet absorbs spare vertical space; grid stays at its
        # natural height, so the bottom buttons are never pushed off-screen.
        self._planet_container = QWidget()
        self._planet_container.setStyleSheet("background:transparent;border:none;")
        self._planet_layout = QVBoxLayout(self._planet_container)
        self._planet_layout.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._planet_container, 1)   # ← stretch=1

        # Kortnät (3 kolumner) – stretch=0 so it only takes what it needs
        self._grid_w = QWidget()
        self._grid_w.setStyleSheet("background:transparent;border:none;")
        self._grid   = QGridLayout(self._grid_w)
        self._grid.setSpacing(14)
        outer.addWidget(self._grid_w, 0)             # ← stretch=0

        # Skanningsfält
        self._inp = scanner_field("Scanna koden på skärmen...", PRIMARY_B)
        self._inp.textChanged.connect(self._live)
        self._inp.returnPressed.connect(self._submit)
        outer.addWidget(self._inp)

        # Nedre rad
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        ny_card = make_card(PRIMARY_L, PRIMARY_B)
        v = QVBoxLayout(ny_card)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(6)
        v.addWidget(lbl("🍳 Ny scanning", 14, True, PRIMARY, Qt.AlignCenter))
        ql = QLabel()
        ql.setAlignment(Qt.AlignCenter)
        ql.setStyleSheet("border:none;background:transparent;")
        ql.setPixmap(make_qr_pixmap("ny scanning", 120))
        v.addWidget(ql)
        ny_card.clicked.connect(lambda: self._inp.setText("ny scanning"))
        bottom_row.addWidget(ny_card, 1)

        self._toggle = ModeToggle()
        self._toggle.mode_changed.connect(self._on_mode_changed)
        bottom_row.addWidget(self._toggle, 1)

        outer.addLayout(bottom_row)

    def showEvent(self, _):
        QTimer.singleShot(80, self._inp.setFocus)

    def _live(self, txt):
        key = txt.strip().lower()
        if key == "ny scanning":
            self.new_scan.emit()
            self._inp.clear()
        elif key == "byt lage":
            self._toggle.activate_via_scanner()
            self._inp.clear()

    def _submit(self):
        key = self._inp.text().strip().lower()
        self._inp.clear()
        if key == "ny scanning":
            self.new_scan.emit()
        elif key == "byt lage":
            self._toggle.activate_via_scanner()

    def _on_mode_changed(self, mode: str):
        self._current_mode = mode
        if self._last_food_list:
            self._render(self._last_food_list)

    def load(self, food_list: list, n: int):
        self._last_food_list = food_list
        self._render(food_list)

    def _render(self, food_list: list):
        mode = self._current_mode

        if mode == "meal":
            res = Miljodator.calc_meal(MY_FOODS, food_list)
            self._title.setText(f"Så mycket klimatpåverkan har din måltid ({len(food_list)} matvaror)")
            self._subtitle.setText("Baserat på portionsstorlek och antal")
            unit_suffix = ""
        else:
            res = Miljodator.calc_per_kg(MY_FOODS, food_list)
            unique_count = len(res["breakdown"])
            self._title.setText(f"Jämför livsmedel ({unique_count} unika varor)")
            self._subtitle.setText("Varornas utsläpp per kg")
            unit_suffix = " / kg"

        breakdown = res["breakdown"]

        color_map = {
            item["name"]: SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
            for i, item in enumerate(breakdown)
        }

        # ── Uppdatera planet-bannern (bara i måltidsläge) ─────────────────
        # Ta bort gammalt widget
        while self._planet_layout.count():
            it = self._planet_layout.takeAt(0)
            if it and it.widget():
                w = it.widget()
                if hasattr(w, '_anim'):
                    w._anim.stop()
                w.deleteLater()
        self._planet_widget = None

        if mode == "meal":
            pw = PlanetWidget(res["co2"])
            self._planet_layout.addWidget(pw)
            self._planet_widget = pw
            self._planet_container.setVisible(True)
            self._planet_container.setMinimumHeight(100)
            self._planet_container.setMaximumHeight(16777215)  # reset to unlimited
        else:
            self._planet_container.setVisible(False)
            self._planet_container.setFixedHeight(0)

        # Rensa gamla kort
        while self._grid.count():
            it = self._grid.takeAt(0)
            if it and it.widget():
                it.widget().deleteLater()

        totals = {"CO2": res["co2"], "Land": res["land"], "Water": res["water"]}

        if mode == "meal":
            meal_label_map = {}
            for item in breakdown:
                name  = item["name"]
                count = item["count"]
                sing, plur = self._p_food_display_map.get(name, (name, name))
                display = sing if count == 1 else plur
                meal_label_map[name] = f"{count} {display}"
        else:
            meal_label_map = None

        for col, (metric, title, unit, bg, border, title_color, cmp_fn) in enumerate(self.CARDS):
            total = totals[metric]
            display_unit = unit + unit_suffix

            c = make_card(bg, border)
            v = QVBoxLayout(c)
            v.setContentsMargins(16, 14, 16, 14)
            v.setSpacing(6)

            v.addWidget(lbl(title, 17, True, title_color))
            v.addWidget(hline(border))

            if mode == "meal":
                cmp_text = cmp_fn(total)
                v.addWidget(lbl(cmp_text, 12, False, MUTED, Qt.AlignCenter))

            if mode == "meal":
                v.addWidget(
                    StackedDonutWidget(breakdown, metric, total, display_unit,
                                       color_map, meal_label_map),
                    0, Qt.AlignCenter,
                )
            else:
                v.addWidget(
                    HBarChartWidget(breakdown, metric, display_unit, color_map),
                    0, Qt.AlignCenter,
                )

            self._grid.addWidget(c, 0, col)

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

        hdr = QWidget()
        hdr.setFixedHeight(62)
        hdr.setStyleSheet(f"background:white;border-bottom:4px solid {PRIMARY_B};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 0, 24, 0)
        hl.setSpacing(10)

        logo = QLabel()
        logo.setStyleSheet("background:transparent;border:none;")
        logo_px = QPixmap("logga_magasinet.png")
        if not logo_px.isNull():
            logo.setPixmap(
                logo_px.scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        hl.addWidget(logo, 0, Qt.AlignVCenter)

        title_lbl = lbl("Miljödatorn", 20, True, LOGO_TEAL)
        title_lbl.setStyleSheet(
            f"color:{LOGO_TEAL};"
            "background:transparent;"
            "border:none;"
            "margin-top:16px;"
        )
        hl.addWidget(title_lbl)
        hl.addStretch()

        self._step_labels = []
        for s in ("🍎 Mat", "🌿 Resultat"):
            lb = QLabel(s)
            lb.setStyleSheet(
                f"background:#F3F4F6;color:#9CA3AF;border-radius:11px;"
                f"padding:4px 12px;font-weight:bold;font-size:12px;border:none;"
            )
            hl.addWidget(lb)
            self._step_labels.append(lb)
        hl.addStretch()

        right_box = QWidget()
        right_box.setStyleSheet("background:transparent;border:none;")
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._source_lbl = lbl("Källa: SAFAD (SLU) & WWF", 11, False, MUTED, Qt.AlignRight)
        self._tlbl       = lbl("", 11, False, MUTED, Qt.AlignRight)
        self._tlbl.setFixedWidth(160)
        self._source_lbl.setFixedWidth(160)

        right_layout.addWidget(self._tlbl)
        right_layout.addWidget(self._source_lbl)
        hl.addWidget(right_box)
        root.addWidget(hdr)

        self._tbar_bg = QWidget()
        self._tbar_bg.setFixedHeight(4)
        self._tbar_bg.setStyleSheet("background:#F3F4F6;border:none;")
        self._tbar = QWidget(self._tbar_bg)
        self._tbar.setStyleSheet(f"background:{ACCENT};border:none;")
        root.addWidget(self._tbar_bg)

        self._stack     = QStackedWidget()
        self._p_food    = FoodPage()
        self._p_results = ResultsPage()
        self._p_results._p_food_display_map = self._p_food.food_display_map
        for p in (self._p_food, self._p_results):
            self._stack.addWidget(p)
        root.addWidget(self._stack)

        self._p_food.calc_requested.connect(self._on_calc)
        self._p_food.reset_requested.connect(self._do_reset)
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
        ACTIVE  = (f"background:{PRIMARY_B};color:{PRIMARY};border-radius:11px;"
                   "padding:4px 12px;font-weight:bold;font-size:12px;border:none;")
        DONE    = (f"background:{PRIMARY_L};color:#065F46;border-radius:11px;"
                   "padding:4px 12px;font-weight:bold;font-size:12px;border:none;")
        PENDING = ("background:#F3F4F6;color:#9CA3AF;border-radius:11px;"
                   "padding:4px 12px;font-weight:bold;font-size:12px;border:none;")
        for i, lb in enumerate(self._step_labels):
            lb.setStyleSheet(ACTIVE if i == idx else DONE if i < idx else PENDING)

    def _on_calc(self):
        if not self._p_food.food_list:
            return
        self._p_results.load(self._p_food.food_list, len(self._p_food.food_list))
        self._tactive = True
        self._tsec    = 200
        self._go(1)

    def _new_scan(self):
        self._p_food.reset()
        self._p_results._current_mode = "meal"
        self._p_results._toggle._current = "meal"
        self._p_results._toggle._refresh()
        self._tsec = 200
        self._go(0)

    def _do_reset(self):
        self._p_food.reset()
        self._p_results._current_mode = "meal"
        self._p_results._toggle._current = "meal"
        self._p_results._toggle._refresh()
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