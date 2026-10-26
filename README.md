# Sky Map Trainer

A desktop app for practising blind sky maps for the IOAA observational exams. 

The program uses sky-maps generated with data from the Hipparcos catalogue and Stellarium constellation diagrams and the positions are plotted via zenithal-equidistant polar projection.

The current interface uses PyQt6; the earlier Tkinter releases are available in the repository's [release history](https://github.com/Goggyy/IOAA-Sky-Map/releases).

## What is included

- Eight exercises covering the celestial pole, ecliptic, constellations, named stars and Bayer designations, local sidereal time, and missing stars.
- Constellation sets: all, zodiac, northern, southern, winter, and summer. Star exercises offer Top 60 and Extended sets where applicable.
- A sky map generator with a world map location picker, UTC or local time, and a coordinate converter.
- Sky analysis layers and saved display and generation settings.
- Help & About page with user guide.

## Run from source

Download the source and open a terminal in the folder containing `main.py` and `requirements.txt` (the `Sky Map Trainer 3.0` folder in this working copy). Python 3.11 or newer is recommended.

On macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

On Windows, from Command Prompt or PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

The app needs internet access for its first Hipparcos and Stellarium data downloads. It stores them and user settings in `~/.ioaa_sky_trainer` (the current user's home directory on Windows). This is a source release, not an installer. Import and offscreen workflow checks passed on macOS 26.5.2 with Python 3.13.0; a fresh installation, a visible desktop session, and Windows/Linux use have not been verified for this release.

The app's **Help** page is editable in [`ioaa_trainer/HELP.md`](ioaa_trainer/HELP.md). More detailed student instructions and demonstrations are planned for 2027.

## Licence and data

Copyright (c) 2026 Goggyy. This PyQt6 application is released under the [GNU General Public License version 3](LICENSE) (GPLv3). Earlier releases and any untouched legacy material retained in the repository remain available under their original MIT terms; that notice is preserved in [LICENSE-MIT-legacy](LICENSE-MIT-legacy). GPLv3 is compatible with the free edition of [PyQt6](https://www.riverbankcomputing.com/software/pyqt/intro).

The app downloads Stellarium constellation lines under **CC BY-SA 2.0** and ESA Hipparcos star data under **CC BY-NC 3.0 IGO**; the bundled Natural Earth map is public domain. See [third-party notices](THIRD_PARTY_NOTICES.md) for credits, licence conditions, and source links. These data terms are separate from the app code's GPLv3 licence. No executable or downloaded catalogue files are supplied.
