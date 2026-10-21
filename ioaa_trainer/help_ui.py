"""Instructions and general information window for the IOAA sky trainer."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .theme import apply_night_theme, night_mode_enabled, refresh_widget_theme
from .widgets import SmoothScrolledText


HELP_TEXT = """IOAA Blind Sky Trainer

This is a Python Tkinter application used for practising sky-map skills for the observation section of the IOAA. The activities use a randomly generated sky map with data from the Hipparcos catalogue and Stellarium constellation diagrams, and the positions are plotted via a zenithal-equidistant polar projection.

Activity questions involve identifying the Celestial Equator, Ecliptic, and constellations, among other commonly tested questions at the IOAA.

After revealing the answer to an activity, the current sky can be analysed, where reference coordinates, constellation lines, and labels can be toggled on.

Below are further specifications about the program:

Excersices:

1. Celestial Equator and Cardinal Directions — identify the celestial equator, cardinal directions, one celestial pole, and estimate the observer's latitude.
2. Ecliptic — identify the ecliptic and zodiacal constellation.
3. Locate a Constellation — locate a randomly chosen constellation above the horizon.
4. Locate a Zodiacal Constellation — locate one of the 13 zodiacal constellations, including Ophiuchus.
5. Name the Constellation — identify a randomly circled constellation above the horizon.
6. Name the Star — identify a circled bright star by its IAU name and Bayer designation.
7. Star from Alt/Az — identify one of the 20 brightest stars from a supplied Alt/Az coordinate; cardinal directions are shown.
8. Estimate the LST — use a drawn local meridian and familiar RA references to estimate local sidereal time.

A timer begins when a new sky map displays and stops when Reveal answer is selected. It is used as a reference for the user and to simulate exam conditions.

Navigating the app:

The launcher contains three tabs:

- Exercises — the default main page containing all training exercises.
- Tools — independently runnable astronomy tools. Tool 1 is the Sky Map Generator; Tool 2 is the Coordinate Converter for RA/Dec, Alt/Az, LST, and hour angle. The Coordinate Converter includes a live, draggable celestial sphere beneath each workflow, showing the P–Z–★ astronomical triangle, equator, horizon, meridian, N/E/S/W directions, and coordinate arcs. The default/reset orientation is observer-centred Alt–Az (zenith up and east right), and drag rotation stays screen-relative after tilting.
- Random sky settings — settings for the random sky maps generated in the sky map. All customisation to sky settings will be saved locally.

"""


class HelpWindow(tk.Toplevel):
    """A scrollable, modeless instructions page."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        apply_night_theme(self, night_mode_enabled(parent))
        self.title("IOAA Sky Trainer — Instructions and About")
        self.geometry("760x720")
        self.minsize(560, 460)
        self.transient(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        frame = ttk.Frame(self, padding=14)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        text = SmoothScrolledText(
            frame,
            wrap="word",
            padx=14,
            pady=12,
            font=("TkDefaultFont", 10),
        )
        text.grid(row=0, column=0, sticky="nsew")
        text.insert("1.0", HELP_TEXT)
        text.configure(state="disabled")

        ttk.Button(frame, text="Close", command=self.destroy).grid(
            row=1,
            column=0,
            sticky="e",
            pady=(10, 0),
        )
        refresh_widget_theme(self)
