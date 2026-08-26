# IOAA Blind Sky Trainer

This is a python Tkinter application used for practising sky-map skills for the observation section of the IOAA. The activities uses a randomly generated sky-map with data from the Hipparcos catalogue and Stellarium constellation diagrams and the positions are plotted via zenithal-equidistant polar projection.

Activity questions involve identifying Celestial Equator, Ecliptic and Constellation - questions that are all likely to be tested in the IOAA.

After revealing the answer to an activity, the current sky can be analysed where reference coordinates, constellation lines and labels can be toggled on.

Below are further specifications about the program:

## Included activities

1. **Celestial Equator** — identify the celestial equator.
2. **Ecliptic** — identify the ecliptic.
3. **Locate a Constellation** — locate a randomly selected constellation that has at least three visible diagram segments above the horizon.

## Project structure

```text
ioaa_sky_trainer/
├── main.py                         
├── requirements.txt
├── run_windows.bat
├── run_macos_linux.sh
├── activities/
│   ├── activity_celestial_equator.py
│   ├── activity_ecliptic.py
│   ├── activity_constellation.py
│   └── activity_template.py.example
└── ioaa_trainer/
    ├── activity_api.py             # Small interface implemented by activities
    ├── activity_ui.py              # Reusable blind-question UI
    ├── analysis_ui.py              # Reusable full analysis window
    ├── astronomy.py                # Catalogue loading and coordinate transforms
    ├── models.py                   # Shared immutable data objects
    ├── random_sky.py               # Random location/time generation
    └── rendering.py                # Blind and analysis chart rendering
```

The launcher automatically discovers files named `activities/activity_*.py` that export an `ACTIVITY_CLASS`.

## Requirements

- Python 3.11 or newer is recommended.
- Tkinter support must be installed with Python.
- Internet access is required on the first run.

The first run downloads the Hipparcos catalogue and a pinned Stellarium constellation-line file. They are cached in:

```text
~/.ioaa_sky_trainer
```

Later runs use the cache.

# Windows: step-by-step

## Option A: automatic launcher

1. Extract the ZIP file.
2. Open the extracted `ioaa_sky_trainer` folder.
3. Double-click `run_windows.bat`.
4. On first use, the script creates `.venv` and installs the dependencies.
5. Select an activity from the launcher.

If Windows asks which Python to use, install Python 3.11 or newer from python.org and enable **Add Python to PATH** during installation.

## Option B: PowerShell commands

Open PowerShell in the project directory and run:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

You can avoid activation entirely:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

# macOS: step-by-step

1. Extract the ZIP file.
2. Open Terminal.
3. Change to the project folder, for example:

```bash
cd ~/Downloads/ioaa_sky_trainer
```

4. Run the launcher script:

```bash
./run_macos_linux.sh
```

If macOS reports that the file is not executable:

```bash
chmod +x run_macos_linux.sh
./run_macos_linux.sh
```

Manual setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Use a Python installation that includes Tk. If `import tkinter` fails, install a matching Tk package or use the Python installer from python.org.

# Ubuntu or Debian: step-by-step

Install the operating-system Tk and virtual-environment packages:

```bash
sudo apt update
sudo apt install python3 python3-tk python3-venv
```

Then run:

```bash
cd ~/Downloads/ioaa_sky_trainer
./run_macos_linux.sh
```

Manual setup is the same as macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

```bash
python activities/activity_celestial_equator.py
python activities/activity_ecliptic.py
python activities/activity_constellation.py
```

On Windows without activating the virtual environment:

```powershell
.venv\Scripts\python.exe activities\activity_constellation.py
```

# Activity Specifications

1. The program generates a random Earth location and a random UTC time between 2020 and 2035.
2. The question map displays only stars and the horizon circle. It contains no direction labels, coordinate labels, grids, constellation lines, constellation names, or reference lines.
3. Read the prompt and identify the requested feature mentally or on paper.
4. Select **Reveal answer**.
5. Choose either:
   - **New random question**, or
   - **Analyse current sky…**
6. In the analysis window, toggle any of these layers:
   - Horizon directions
   - Altitude/azimuth grid
   - RA/Dec coordinate grid
   - Ecliptic
   - Celestial equator
   - Galactic equator
   - All constellation diagrams
   - Constellation names
   - Bright-star names
   - Activity-answer highlight
   - Observation details title
7. Adjust **Faintest visible magnitude** to show only brighter stars or include fainter stars down to the catalogue limit used for the question.
8. The analysis window also reveals the latitude, longitude, UTC time, map rotation, and question seed, and can export a PNG.

All analysis overlays are initially switched off, so the analysis window opens with the same clean star field as the question. Text labels remain upright even when the map has a random rotation.

# Command-line checks

After installing dependencies, verify discovery and imports without opening windows:

```bash
python main.py --check
python activities/activity_constellation.py --check
```

# Randomisation details

- Longitude is uniformly sampled from −180° to +180°.
- Latitude is sampled uniformly over Earth’s surface using a uniform value of `sin(latitude)`, avoiding an artificial excess of polar questions.
- Time is sampled uniformly between 1 January 2020 and 31 December 2035 in UTC.
- Map rotation is sampled uniformly from 0° to 360° and remains fixed for the question, answer, and analysis view.
- The observation details are hidden during the blind question and revealed only in the analysis window.
- Each question stores a seed that can be recorded for diagnostics or future reproducibility work.

# Accuracy and scope

- The chart is intended for visual training, not precision astrometric measurement.
- Atmospheric refraction is disabled; the geometric horizon is used.
- Stellar proper motion is not applied.
- Constellation lines are the selected Stellarium sky-culture diagrams.
- A constellation edge is drawn only when both endpoint stars are above the horizon.
- Astropy uses its bundled Earth-orientation data without a separate IERS download.

# Troubleshooting

## `No module named tkinter`

Tkinter is supplied by the operating system or Python installer rather than `pip`.

Ubuntu/Debian:

```bash
sudo apt install python3-tk
```

## `ModuleNotFoundError` for Astropy, Skyfield, Matplotlib, Pandas, or NumPy

Activate the virtual environment and reinstall:

```bash
python -m pip install -r requirements.txt
```

## First question fails to load

Confirm internet access. If a download was interrupted, remove the cache and retry:

```text
~/.ioaa_sky_trainer
```

## The activity launcher opens no activities

Confirm that activity files:

- are inside `activities/`,
- are named `activity_*.py`, and
- export `ACTIVITY_CLASS`.
