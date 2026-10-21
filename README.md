# IOAA Blind Sky Trainer

This is a python Tkinter application used for practising sky-map skills for the observation section of the IOAA. The activities uses a randomly generated sky-map with data from the Hipparcos catalogue and Stellarium constellation diagrams and the positions are plotted via zenithal-equidistant polar projection.

Activity questions involve identifying Celestial Equator, Ecliptic and Constellations among other commonly tested questions at the IOAA.

After revealing the answer to an activity, the current sky can be analysed where reference coordinates, constellation lines and labels can be toggled on.

Below are further specifications about the program:

## Included exercises

1. **Celestial Equator and Cardinal Directions** — identify the celestial equator, cardinal directions, one celestial pole, and estimate the observer's latitude.
2. **Ecliptic** — identify the ecliptic and zodiacal constellation
3. **Locate a Constellation** — locate a randomly chosen constellation above the horizon
4. **Locate a Zodiacal Constellation** — locate one of the 13 constellations zodiacal constellations, including Ophiuchus.
5. **Name the Constellation** — identify a randomly circled constellation above the horizon
6. **Name the Star** — identify a circled bright star by its IAU name and Bayer designation.

A timer begins when a new sky map displays and stops when **Reveal answer** is selected, just used for the user as a reference and simulate exam conditions.

## Home page

The launcher contains three tabs:

- **Exercises** — the default main page containing all training exercises.
- **Tools** — automatically discovered, independently runnable astronomy utilities.
- **Random sky settings** — constraints and view settings used by newly opened exercises.

The **Instructions & About…** button is located in the global header so it remains available regardless of the selected tab. All Boolean layer and view controls are displayed as compact borderless sliding switches, and scrollable settings pages use eased mouse-wheel and trackpad movement.

## Project structure

```text
ioaa_sky_trainer/
├── main.py
├── sky_map_generator.py
├── requirements.txt
├── run_windows.bat
├── run_macos_linux.sh
├── activities/                       # Legacy folder name retained for compatibility
│   ├── activity_celestial_equator.py
│   ├── activity_ecliptic.py
│   ├── activity_constellation.py
│   ├── activity_zodiac_constellation.py
│   ├── activity_name_constellation.py
│   ├── activity_name_star.py
│   └── activity_template.py.example
├── tools/
│   ├── tool_sky_map_generator.py
│   └── tool_template.py.example
└── ioaa_trainer/
    ├── activity_api.py                # Legacy API names retained for compatibility
    ├── activity_ui.py
    ├── analysis_ui.py
    ├── astronomy.py
    ├── generation_settings.py
    ├── generator_ui.py
    ├── help_ui.py
    ├── models.py
    ├── random_sky.py
    ├── reference_data.py
    ├── rendering.py
    ├── targeting.py
    ├── theme.py
    ├── time_utils.py
    ├── widgets.py
    └── tool_api.py
```

The launcher automatically discovers:

- Files named `activities/activity_*.py` that export `ACTIVITY_CLASS`.
- Files named `tools/tool_*.py` that export `TOOL_CLASS`.

The older internal names are retained so existing exercise modules and saved projects continue to work unchanged.

## Requirements

- Python 3.11 or newer is recommended.
- Tkinter support must be included with Python.
- Internet access is required on the first run.

The first run downloads the Hipparcos catalogue and a pinned Stellarium constellation-line file. Catalogue data and launcher settings are stored under:

```text
~/.ioaa_sky_trainer
```

## Windows setup

Extract the ZIP, open the project folder, and double-click:

```text
run_windows.bat
```

Manual PowerShell setup:

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

## macOS setup

```bash
cd ~/Downloads/ioaa_sky_trainer
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

Use a Python installation that includes Tkinter. The Python installer from python.org normally includes it.

## Ubuntu or Debian setup

```bash
sudo apt update
sudo apt install python3 python3-tk python3-venv
cd ~/Downloads/ioaa_sky_trainer
chmod +x run_macos_linux.sh
./run_macos_linux.sh
```

## Using the exercise timer

1. The timer remains at zero while the astronomical data is being calculated.
2. It starts when the blind map and prompt are ready.
3. It updates to one tenth of a second.
4. It stops permanently for that question when **Reveal answer** is pressed.
5. A new question resets it to zero.

## Configuring generated exercise skies

Open `main.py` and select **Random sky settings**.

### Solar-system objects

Enable **Include visible Sun, Moon, and planets** to add unlabelled solar-system markers. It is disabled by default, preserving the original star-only exercise maps.

### Coordinates

Choose either:

- **Random coordinates** — latitude is sampled uniformly over Earth's surface and longitude uniformly from −180° to +180°.
- **Fixed coordinates** — enter latitude and longitude in degrees.

North and east are positive; south and west are negative.

### Time

Choose one of four forms:

- **Random UTC date and time** — sampled between 1 January 2020 and 31 December 2035.
- **Fixed UTC date and time** — enter `YYYY-MM-DD` and `HH:MM:SS`.
- **Fixed local sidereal time (LST)** — enter an LST as `HH:MM:SS` or decimal hours plus a UTC reference date. The selected longitude is used to resolve the UTC instant.
- **Fixed Modified Julian Date (MJD)** — enter a numeric UTC MJD.

### View

- **Default colours** — use a white chart with black star markers.
- **Invert map colours** — switches to white stars and labels on a black chart.
- **Night mode** — changes the application interface and all charts to a black-and-red palette designed to avoid white and blue light during observations. The saved choice is used by the launcher, exercises, analysis windows, help, and tools.
- **Sky coverage from zenith** — the control runs from 0° (the zenith point) through 90° (the default hemisphere ending at the horizon) to 180° (the full celestial sphere).
- **Faintest visible magnitude** — lower values show only brighter stars; higher values include fainter stars, up to magnitude 8.0.
- **Star marker scale** — changes marker sizes without changing the selected stars.
- **Randomise map rotation** — enabled by default; switch it off to keep north up.

Select **Save settings**. Newly launched exercise windows use the saved values. An exercise already open continues using the settings with which it started.

## Using an exercise

1. Wait for the blind map and timer to appear.
2. Solve the prompt using the star pattern.
3. Select **Reveal answer** to stop the timer and display the answer.
4. Select **New random question** or **Analyse current sky…**.

The blind map hides ordinary coordinates, grids, constellation labels, location, and time. Exercises 5 and 6 retain their target circles. The chart is north-up unless random map rotation is enabled in Random sky settings. Exercise 1 reveals its requested cardinal-direction and pole labels only after the answer is revealed.

## Analysis window

All optional layers start switched off. Available controls include:

- Horizon directions
- Altitude/azimuth grid
- RA/Dec grid
- Ecliptic
- Celestial equator
- Galactic equator
- Constellation diagrams
- Constellation names
- Bright-star names
- Solar-system objects
- Solar-system object names
- Zenith label
- Exercise answer highlight
- Observation details title
- Faintest visible stellar magnitude

The observation panel displays latitude, longitude, UTC, apparent local sidereal time (LST), map rotation, and question seed. The saved chart colours, sky coverage, and default star marker scale remain consistent with the exercise chart.

## Tools

The **Tools** tab uses the same modular card layout as the Exercises tab. Each tool is an independent file and may also be run directly.

### Sky Map Generator

Open **Sky Map Generator** from the Tools tab, or run:

```bash
python sky_map_generator.py
```

The generator provides two ways to place the sky:

- **Observer location + time** — enter latitude/longitude and supply time as UTC, LST plus reference date, or MJD.
- **Direct zenith** — drag a marker on an equirectangular celestial-sphere projection to place the right ascension and declination at the centre of the chart. For precise placement, enter RA as decimal hours or `HH:MM:SS` and Dec as decimal degrees in the manual controls below the projection. The highlighted spherical-cap boundary shows the area included by the current field-of-view setting. The declination becomes the synthetic observer latitude and the RA becomes LST for the selected reference date.

The generator recalculates automatically after observation inputs settle; there is no separate Generate button. In direct-zenith mode the chart keeps recalculating while the zenith marker is dragged. The **View** tab controls colour inversion, distance from zenith (0°–180°), faintest visible magnitude, star-marker scale, and optional map rotation. Rotation is disabled by default, giving a north-up map. At 90° the chart is one visible hemisphere; at 180° it is a full-sky zenithal-equidistant projection with the nadir at the outer edge. Because the full sphere is calculated internally, coverage, layer, colour, magnitude, marker-size, and rotation changes redraw immediately. The generator also retains study-view, navigation, and PNG-export controls.

### Adding a new tool

1. Copy `tools/tool_template.py.example`.
2. Rename it to `tools/tool_something.py`.
3. Set the tool's `tool_id`, `title`, and `description`.
4. Implement the directly runnable `run_tool()` function.
5. Export the class as `TOOL_CLASS`.

The launcher discovers the tool automatically and displays it on the Tools tab without changes to `main.py`.

## Instructions page

Select **Instructions & About…** in the launcher header. It explains the exercise workflow, keyboard shortcuts, chart geometry, saved settings, tool system, map generator, first-run downloads, and extension process.

## Adding a new exercise

1. Copy `activities/activity_template.py.example`.
2. Rename it to `activities/activity_something.py`.
3. Implement `create_question()` and `draw_answer()`.
4. Override `draw_question()` only when a marker must be shown before reveal.
5. Export the class as `ACTIVITY_CLASS`.

The launcher discovers it automatically. Shared timing, random-sky constraints, view settings, answer flow, and analysis support are applied without additional exercise code.

If a generated sky is unsuitable, raise `QuestionUnavailable` and the framework will try another sky.

## Command-line checks

After installing dependencies:

```bash
python main.py --check
python activities/activity_constellation.py --check
python tools/tool_sky_map_generator.py
python -m compileall -q .
```

## Accuracy and scope

- The maps are intended for visual training rather than precision astrometry.
- Atmospheric refraction is disabled; the geometric horizon is used.
- Stellar proper motion is not applied.
- Solar-system positions use Astropy's built-in ephemeris.
- Local sidereal time is apparent LST for the entered longitude.
- Constellation lines use the selected Stellarium line diagrams.
- The catalogue and constellation layers are clipped to the selected zenith-distance coverage.
- Exercises that ask for a visible constellation continue to select targets using above-horizon line segments.
- Astropy uses bundled Earth-orientation data without a separate IERS download.

## Troubleshooting

### `No module named tkinter`

Tkinter is provided by the operating system or Python installer, not by `pip`.

Ubuntu/Debian:

```bash
sudo apt install python3-tk
```

### Missing Astropy, Skyfield, Matplotlib, Pandas, or NumPy

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### First question fails to load

Confirm internet access. If a catalogue download was interrupted, delete the catalogue cache files under `~/.ioaa_sky_trainer` and retry. The same folder also stores the launcher settings; retain it to preserve them.

---

## Packaged launcher note

This packaged version includes a small convenience change for first-time users:

- Run **`main.py`** directly from PyCharm, VS Code, or another Python IDE.
- On first launch, `main.py` creates a local `.venv`, installs the packages from `requirements.txt`, and then starts the original application from `app.py`.
- The first run therefore requires an internet connection for dependency installation and any astronomy data downloads used by the program.
- The original application launcher code has been preserved in `app.py`.

The existing Windows and macOS/Linux launcher scripts are also included.
