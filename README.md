# Frukostdator & Miljödator

Interactive kiosk applications for [FenomenMagasinet](https://fenomenmagasinet.se), designed to teach visitors about nutrition and environmental impact of food. Both apps run on Raspberry Pi in full-screen kiosk mode and accept input via a barcode scanner.

---

## Frukostdator

**"Breakfast Calculator"** — Users scan breakfast foods to see their nutritional values, then receive gamified feedback tailored to their age and gender.

### Flow

```
Age selection → Gender selection → Food scanning → Results
```

### Features

- Scans 18 common breakfast items and aggregates: **energy (kcal), fat, protein, sugar, fibre**
- Personalized daily targets based on age (3–70+) and gender
- Gamified result screen:
  - **Running distance** — how far you could run on that energy (nearest landmark in the Linköping region)
  - **Sugar cube tower** — isometric 3D visualization of sugar content
  - **Fat & protein circles** — arc progress bars against recommended breakfast targets
  - **Animated chameleon** — runs faster with more calories (14-frame sprite sheet)
- Auto-reset after 60 seconds of inactivity

### Running

```bash
# Full-screen kiosk (Raspberry Pi)
python3 FrukostQt.py

# Windowed mode for development
python3 FrukostQt.py --window

# Alternative Kivy frontend
python3 Frukostfront.py

# One-time: embed food DB into the standalone web version
python3 export_foods_json.py
```

### Files

| File | Role |
|---|---|
| `FrukostQt.py` | Primary PyQt5 frontend (~1073 lines) |
| `Frukostdator.py` | Core data logic — reads Excel, extracts nutrients |
| `Frukostfront.py` | Alternative Kivy frontend |
| `frukostdator.html` | Standalone browser version (embedded JSON) |
| `destinations.py` | 50+ Linköping-region landmarks for running distance display |
| `LivsmedelsDB_202602231534.xlsx` | Swedish national food nutrition database (~2000 items) |

---

## Miljödator

**"Environment Calculator"** — Users scan the same breakfast items to see their climate and resource footprint, with two viewing modes for comparing meals or individual products.

### Flow

```
Food scanning → Results (switchable between "Din måltid" and "Per kg")
```

### Features

- Tracks three environmental metrics per food item:
  - **CO₂e** — kg greenhouse gas equivalents
  - **Land use** — m² per year
  - **Freshwater** — litres
- Two calculation modes toggled via barcode or on-screen button:
  - **Din måltid** — total impact of the scanned meal using real portion weights
  - **Per kg** — normalised per-kilogram comparison, duplicates ignored
- Results displayed as **donut charts** with colour-coded legends per food item
- Human-scale comparisons (e.g. "≈ 2.4 km driving", "≈ 3 A4 sheets of paper", "≈ 1.2 min showering")
- Data sourced from **SAFAD (SLU)** via `food_data.xlsx`
- Auto-reset after 200 seconds with a live countdown progress bar

### Running

```bash
# Full-screen kiosk (Raspberry Pi)
python3 MiljoQt.py

# Windowed mode for development
python3 MiljoQt.py --window
```

### Files

| File | Role |
|---|---|
| `MiljoQt.py` | PyQt5 frontend with donut charts and mode toggle |
| `Miljodator.py` | Data & logic layer — maps scanner names to dataset names, calculates totals |
| `food_data.xlsx` | Environmental impact data (SAFAD/SLU) |
| `Food-Carbon-Footprint.json` | Raw carbon footprint data (reference) |
| `logga_magasinet.png` | FenomenMagasinet logo for the header |

---

## Dependencies

```
pandas   # Excel reading (Frukostdator)
PyQt5    # GUI for both apps
kivy     # Alternative frontend (Frukostfront.py only)
qrcode   # QR code generation (Miljödator, optional)
```

No `requirements.txt` exists — install manually:

```bash
pip install pandas PyQt5 kivy qrcode
```

---

## Architecture

Both apps follow the same pattern:

```
Scanner (keyboard input)
    ↓
PyQt5 QStackedWidget (pages)
    ↓
Backend module (Frukostdator.py / Miljodator.py)
    ↓
Custom QPainter widgets (no third-party chart libraries)
```

All visuals are hand-drawn with `QPainter`. There is no build step, test suite, or linter.
