# IOAA Observational Flashcards


This is a python flashcard application used for practising sky-map skills for the observation section of the IOAA. 

Each set of flashcards consists of an image of the sky taken from Stellarium. Images are scaled and rotated randomly to avoid repetition.

Flashcard questions involve identifying Celestial Equator, Ecliptic and Constellation - questions that are all likely to be tested in the IOAA.

This project contains three independent flashcards programs:
- **Celestial Lines** — Identify the Celestial Equator, Ecliptic and Galactic Equator on the image shown
- **Celestial Poles** — Identify the North/South Celestial Poles on the image shown
- **Zodiacal Constellations** — Identify the constellation on the image shown

## Project structure

```text
ioaa-observational-flashcards/
├── README.md
└── flashcards/
    ├── celestial_lines/
    │   ├── main.py
    │   ├── questions/
    │   └── answers/
    ├── celestial_poles/
    │   ├── main.py
    │   ├── questions/
    │   └── answers/
    └── zodiacal_constellations/
        ├── main.py
        └── images/
```

## Requirements

- Python 3
- Tkinter
- Pillow

Install Pillow with:

```bash
python -m pip install Pillow
```

Tkinter is included with many Python installations. On systems where it is packaged separately, install the Tkinter package for your Python version using your operating system's package manager.

## Running the flashcards

Each flashcard set is standalone. Run `main.py` from inside the corresponding folder so its relative image paths resolve correctly.

### Celestial Lines

```bash
cd flashcards/celestial_lines
python main.py
```

### Celestial Poles

```bash
cd flashcards/celestial_poles
python main.py
```

### Zodiacal Constellations

```bash
cd flashcards/zodiacal_constellations
python main.py
```
