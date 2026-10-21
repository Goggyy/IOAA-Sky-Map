"""Guided equatorial / horizontal coordinate converter UI.

The converter separates *given values* from *calculated values*.  The user
chooses a conversion direction and, where necessary, which sidereal quantity
is known.  This avoids the ambiguous behaviour of an all-editable worksheet.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .coordinate_converter import (
    equatorial_from_horizontal,
    format_degrees,
    format_hours,
    horizontal_from_equatorial,
    hour_angle_from_lst_ra,
    lst_from_ra_hour_angle,
    parse_degrees,
    parse_hours,
    ra_from_lst_hour_angle,
)
from .generation_settings import load_generation_settings
from .theme import apply_night_theme
from .celestial_sphere_widget import CelestialSphereTriangle
from .widgets import VerticalScrolledFrame


class CoordinateConverterApplication(tk.Tk):
    """A guided converter between equatorial and horizontal coordinates."""

    AUTOFILL_DELAY_MS = 220

    def __init__(self) -> None:
        super().__init__()
        self.title("IOAA Coordinate Converter")
        self.geometry("790x670")
        self.minsize(620, 500)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        settings = load_generation_settings()
        self._programmatic_update = False
        self._solve_job: str | None = None
        self._sphere_visualizers: list[CelestialSphereTriangle] = []

        # Shared quantities make switching direction useful: the result of one
        # conversion is immediately ready for the reverse conversion.
        self.latitude_var = tk.StringVar()
        self.ra_var = tk.StringVar()
        self.dec_var = tk.StringVar()
        self.lst_var = tk.StringVar()
        self.ha_var = tk.StringVar()
        self.alt_var = tk.StringVar()
        self.az_var = tk.StringVar()

        self.forward_time_mode = tk.StringVar(value="lst")
        self.reverse_time_anchor = tk.StringVar(value="lst")
        self.forward_status = tk.StringVar(
            value="Enter latitude, RA, Dec and LST. Results appear automatically."
        )
        self.reverse_status = tk.StringVar(
            value="Enter latitude, altitude and azimuth. Add LST to also determine RA."
        )

        apply_night_theme(self, settings.night_mode)
        self._build_ui()
        self._install_live_updates()
        self.after_idle(self._solve_active_tab)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=14)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="Coordinate Converter",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text=(
                "Choose a direction, enter only the quantities you know, and read "
                "the calculated coordinates separately."
            ),
            wraplength=720,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(3, 0))

        self.notebook = ttk.Notebook(outer)
        self.notebook.grid(row=1, column=0, sticky="nsew")
        self.notebook.bind("<<NotebookTabChanged>>", lambda _event: self._solve_active_tab())

        self.forward_tab = ttk.Frame(self.notebook)
        self.reverse_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.forward_tab, text="RA / Dec  →  Alt / Az")
        self.notebook.add(self.reverse_tab, text="Alt / Az  →  RA / Dec")
        self._build_forward_tab()
        self._build_reverse_tab()

        footer = ttk.Frame(outer)
        footer.grid(row=2, column=0, sticky="ew", pady=(9, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(
            footer,
            text=(
                "Input: decimal or sexagesimal (12.5 = 12:30:00).  "
                "Azimuth N=0°, E=90°.  H = LST − RA; H > 0 west of the meridian."
            ),
            wraplength=730,
            justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 7))
        ttk.Frame(footer).grid(row=1, column=0, sticky="ew")
        ttk.Button(footer, text="Copy values", command=self._copy_values).grid(
            row=1, column=1, padx=(10, 0)
        )
        ttk.Button(footer, text="Clear all", command=self._clear_all).grid(
            row=1, column=2, padx=(8, 0)
        )

    def _build_forward_tab(self) -> None:
        self.forward_tab.columnconfigure(0, weight=1)
        self.forward_tab.rowconfigure(0, weight=1)
        scroller = VerticalScrolledFrame(self.forward_tab, padding=10)
        scroller.grid(row=0, column=0, sticky="nsew")
        body = scroller.content
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        ttk.Label(
            body,
            text="Given equatorial position",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        inputs = ttk.LabelFrame(body, text="Given", padding=12)
        inputs.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        inputs.columnconfigure(1, weight=1)
        self._input_row(inputs, 0, "Observer latitude φ", self.latitude_var, "degrees")
        self._input_row(inputs, 1, "Right ascension α", self.ra_var, "hours")
        self._input_row(inputs, 2, "Declination δ", self.dec_var, "degrees")

        ttk.Separator(inputs).grid(row=3, column=0, columnspan=3, sticky="ew", pady=9)
        ttk.Label(inputs, text="Sky rotation given as:").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        modes = ttk.Frame(inputs)
        modes.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 5))
        ttk.Radiobutton(
            modes,
            text="LST",
            variable=self.forward_time_mode,
            value="lst",
            command=self._forward_mode_changed,
        ).pack(side="left")
        ttk.Radiobutton(
            modes,
            text="Hour angle",
            variable=self.forward_time_mode,
            value="ha",
            command=self._forward_mode_changed,
        ).pack(side="left", padx=(16, 0))

        self.forward_time_input_label = ttk.Label(inputs, text="Local sidereal time")
        self.forward_time_input_label.grid(row=6, column=0, sticky="w", pady=4)
        self.forward_time_input = ttk.Entry(inputs, width=19)
        self.forward_time_input.grid(row=6, column=1, sticky="ew", padx=(10, 0), pady=4)
        self.forward_time_input_unit = ttk.Label(
            inputs, text="hours", font=("TkDefaultFont", 8, "italic")
        )
        self.forward_time_input_unit.grid(row=6, column=2, sticky="w", padx=(6, 0), pady=4)

        results = ttk.LabelFrame(body, text="Calculated", padding=12)
        results.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        results.columnconfigure(1, weight=1)
        self.forward_time_result_label = ttk.Label(results, text="Hour angle H")
        self.forward_time_result_label.grid(row=0, column=0, sticky="w", pady=5)
        self.forward_time_result = ttk.Entry(results, state="readonly", width=19)
        self.forward_time_result.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=5)
        ttk.Label(results, text="hours", font=("TkDefaultFont", 8, "italic")).grid(
            row=0, column=2, sticky="w", padx=(6, 0), pady=5
        )
        ttk.Separator(results).grid(row=1, column=0, columnspan=3, sticky="ew", pady=9)
        self._result_row(results, 2, "Altitude h", self.alt_var, "degrees")
        self._result_row(results, 3, "Azimuth A", self.az_var, "degrees")

        guidance = ttk.Frame(body)
        guidance.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        guidance.columnconfigure(0, weight=1)
        ttk.Label(
            guidance,
            textvariable=self.forward_status,
            wraplength=700,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            guidance,
            text=(
                "Most problems give LST. Select Hour angle only when H is supplied "
                "directly; the converter will then find LST from RA + H."
            ),
            wraplength=700,
            justify="left",
            font=("TkDefaultFont", 9, "italic"),
        ).grid(row=1, column=0, sticky="w", pady=(7, 0))

        visualizer = self._build_celestial_sphere(body)
        visualizer.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 4))

        self._update_forward_time_widgets()

    def _build_reverse_tab(self) -> None:
        self.reverse_tab.columnconfigure(0, weight=1)
        self.reverse_tab.rowconfigure(0, weight=1)
        scroller = VerticalScrolledFrame(self.reverse_tab, padding=10)
        scroller.grid(row=0, column=0, sticky="nsew")
        body = scroller.content
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        ttk.Label(
            body,
            text="Given horizontal position",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        inputs = ttk.LabelFrame(body, text="Given", padding=12)
        inputs.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        inputs.columnconfigure(1, weight=1)
        self._input_row(inputs, 0, "Observer latitude φ", self.latitude_var, "degrees")
        self._input_row(inputs, 1, "Altitude h", self.alt_var, "degrees")
        self._input_row(inputs, 2, "Azimuth A", self.az_var, "degrees")

        ttk.Separator(inputs).grid(row=3, column=0, columnspan=3, sticky="ew", pady=9)
        ttk.Label(
            inputs,
            text="Optional time anchor:",
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 4))
        modes = ttk.Frame(inputs)
        modes.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 5))
        ttk.Radiobutton(
            modes,
            text="I know LST",
            variable=self.reverse_time_anchor,
            value="lst",
            command=self._reverse_mode_changed,
        ).pack(side="left")
        ttk.Radiobutton(
            modes,
            text="I know RA",
            variable=self.reverse_time_anchor,
            value="ra",
            command=self._reverse_mode_changed,
        ).pack(side="left", padx=(16, 0))

        self.reverse_time_input_label = ttk.Label(inputs, text="Local sidereal time")
        self.reverse_time_input_label.grid(row=6, column=0, sticky="w", pady=4)
        self.reverse_time_input = ttk.Entry(inputs, width=19)
        self.reverse_time_input.grid(row=6, column=1, sticky="ew", padx=(10, 0), pady=4)
        ttk.Label(inputs, text="hours", font=("TkDefaultFont", 8, "italic")).grid(
            row=6, column=2, sticky="w", padx=(6, 0), pady=4
        )

        results = ttk.LabelFrame(body, text="Calculated", padding=12)
        results.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        results.columnconfigure(1, weight=1)
        self._result_row(results, 0, "Declination δ", self.dec_var, "degrees")
        self._result_row(results, 1, "Hour angle H", self.ha_var, "hours")
        ttk.Separator(results).grid(row=2, column=0, columnspan=3, sticky="ew", pady=9)
        self.reverse_time_result_label = ttk.Label(results, text="Right ascension α")
        self.reverse_time_result_label.grid(row=3, column=0, sticky="w", pady=5)
        self.reverse_time_result = ttk.Entry(results, state="readonly", width=19)
        self.reverse_time_result.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=5)
        ttk.Label(results, text="hours", font=("TkDefaultFont", 8, "italic")).grid(
            row=3, column=2, sticky="w", padx=(6, 0), pady=5
        )

        guidance = ttk.Frame(body)
        guidance.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        guidance.columnconfigure(0, weight=1)
        ttk.Label(
            guidance,
            textvariable=self.reverse_status,
            wraplength=700,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            guidance,
            text=(
                "Latitude + Alt/Az is already enough for Dec and hour angle. "
                "Supply either LST or RA only if you also want the other one."
            ),
            wraplength=700,
            justify="left",
            font=("TkDefaultFont", 9, "italic"),
        ).grid(row=1, column=0, sticky="w", pady=(7, 0))

        visualizer = self._build_celestial_sphere(body)
        visualizer.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 4))

        self._update_reverse_time_widgets()

    def _build_celestial_sphere(self, parent: ttk.Frame) -> CelestialSphereTriangle:
        visualizer = CelestialSphereTriangle(
            parent,
            latitude_var=self.latitude_var,
            ra_var=self.ra_var,
            dec_var=self.dec_var,
            lst_var=self.lst_var,
            ha_var=self.ha_var,
            alt_var=self.alt_var,
            az_var=self.az_var,
        )
        self._sphere_visualizers.append(visualizer)
        return visualizer

    def _input_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        unit: str,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=variable, width=19).grid(
            row=row, column=1, sticky="ew", padx=(10, 0), pady=4
        )
        ttk.Label(parent, text=unit, font=("TkDefaultFont", 8, "italic")).grid(
            row=row, column=2, sticky="w", padx=(6, 0), pady=4
        )

    def _result_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        unit: str,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(parent, textvariable=variable, state="readonly", width=19).grid(
            row=row, column=1, sticky="ew", padx=(10, 0), pady=5
        )
        ttk.Label(parent, text=unit, font=("TkDefaultFont", 8, "italic")).grid(
            row=row, column=2, sticky="w", padx=(6, 0), pady=5
        )

    # ---------------------------------------------------------- interaction
    def _install_live_updates(self) -> None:
        for variable in (
            self.latitude_var,
            self.ra_var,
            self.dec_var,
            self.lst_var,
            self.ha_var,
            self.alt_var,
            self.az_var,
        ):
            variable.trace_add("write", self._field_changed)

    def _field_changed(self, *_args) -> None:
        if self._programmatic_update:
            return
        self._schedule_solve()

    def _schedule_solve(self) -> None:
        if self._solve_job is not None:
            try:
                self.after_cancel(self._solve_job)
            except tk.TclError:
                pass
        self._solve_job = self.after(self.AUTOFILL_DELAY_MS, self._solve_active_tab)

    def _solve_active_tab(self) -> None:
        self._solve_job = None
        try:
            selected = self.notebook.index(self.notebook.select())
        except tk.TclError:
            return
        if selected == 0:
            self._solve_forward()
        else:
            self._solve_reverse()

    def _forward_mode_changed(self) -> None:
        self._update_forward_time_widgets()
        self._schedule_solve()

    def _reverse_mode_changed(self) -> None:
        self._update_reverse_time_widgets()
        self._schedule_solve()

    def _update_forward_time_widgets(self) -> None:
        if self.forward_time_mode.get() == "lst":
            self.forward_time_input_label.configure(text="Local sidereal time")
            self.forward_time_input.configure(textvariable=self.lst_var)
            self.forward_time_result_label.configure(text="Hour angle H")
            self.forward_time_result.configure(textvariable=self.ha_var)
        else:
            self.forward_time_input_label.configure(text="Hour angle H")
            self.forward_time_input.configure(textvariable=self.ha_var)
            self.forward_time_result_label.configure(text="Local sidereal time")
            self.forward_time_result.configure(textvariable=self.lst_var)

    def _update_reverse_time_widgets(self) -> None:
        if self.reverse_time_anchor.get() == "lst":
            self.reverse_time_input_label.configure(text="Local sidereal time")
            self.reverse_time_input.configure(textvariable=self.lst_var)
            self.reverse_time_result_label.configure(text="Right ascension α")
            self.reverse_time_result.configure(textvariable=self.ra_var)
        else:
            self.reverse_time_input_label.configure(text="Right ascension α")
            self.reverse_time_input.configure(textvariable=self.ra_var)
            self.reverse_time_result_label.configure(text="Local sidereal time")
            self.reverse_time_result.configure(textvariable=self.lst_var)

    # -------------------------------------------------------------- solving
    def _solve_forward(self) -> None:
        mode = self.forward_time_mode.get()
        try:
            latitude = self._optional_degrees(
                self.latitude_var, -90.0, 90.0, "Latitude"
            )
            ra = self._optional_hours(self.ra_var, signed=False)
            dec = self._optional_degrees(self.dec_var, -90.0, 90.0, "Declination")
            time_value = (
                self._optional_hours(self.lst_var, signed=False)
                if mode == "lst"
                else self._optional_hours(self.ha_var, signed=True)
            )
        except ValueError as error:
            self.forward_status.set(str(error))
            return

        missing = []
        if latitude is None:
            missing.append("latitude")
        if ra is None:
            missing.append("RA")
        if dec is None:
            missing.append("Dec")
        if time_value is None:
            missing.append("LST" if mode == "lst" else "hour angle")
        if missing:
            self.forward_status.set("Still needed: " + ", ".join(missing) + ".")
            return

        assert latitude is not None and ra is not None and dec is not None
        assert time_value is not None
        if mode == "lst":
            ha = hour_angle_from_lst_ra(time_value, ra)
            self._set_derived(self.ha_var, format_hours(ha, signed=True))
        else:
            ha = time_value
            lst = lst_from_ra_hour_angle(ra, ha)
            self._set_derived(self.lst_var, format_hours(lst))

        altitude, azimuth = horizontal_from_equatorial(latitude, dec, ha)
        self._set_derived(self.alt_var, format_degrees(altitude, signed=True))
        self._set_derived(self.az_var, format_degrees(azimuth, signed=False))
        self.forward_status.set("Complete — all calculated values are shown on the right.")

    def _solve_reverse(self) -> None:
        anchor = self.reverse_time_anchor.get()
        try:
            latitude = self._optional_degrees(
                self.latitude_var, -90.0, 90.0, "Latitude"
            )
            altitude = self._optional_degrees(
                self.alt_var, -90.0, 90.0, "Altitude"
            )
            azimuth = self._optional_degrees(
                self.az_var, 0.0, 360.0, "Azimuth", wrap_360=True
            )
        except ValueError as error:
            self.reverse_status.set(str(error))
            return

        missing = []
        if latitude is None:
            missing.append("latitude")
        if altitude is None:
            missing.append("altitude")
        if azimuth is None:
            missing.append("azimuth")
        if missing:
            self.reverse_status.set("Still needed: " + ", ".join(missing) + ".")
            return

        assert latitude is not None and altitude is not None and azimuth is not None
        declination, hour_angle = equatorial_from_horizontal(
            latitude, altitude, azimuth
        )
        self._set_derived(self.dec_var, format_degrees(declination, signed=True))
        self._set_derived(self.ha_var, format_hours(hour_angle, signed=True))

        try:
            if anchor == "lst":
                lst = self._optional_hours(self.lst_var, signed=False)
                if lst is None:
                    self._clear_derived(self.ra_var)
                    self.reverse_status.set(
                        "Dec and hour angle are complete. Add LST if you also want RA."
                    )
                    return
                ra = ra_from_lst_hour_angle(lst, hour_angle)
                self._set_derived(self.ra_var, format_hours(ra))
            else:
                ra = self._optional_hours(self.ra_var, signed=False)
                if ra is None:
                    self._clear_derived(self.lst_var)
                    self.reverse_status.set(
                        "Dec and hour angle are complete. Add RA if you also want LST."
                    )
                    return
                lst = lst_from_ra_hour_angle(ra, hour_angle)
                self._set_derived(self.lst_var, format_hours(lst))
        except ValueError as error:
            self.reverse_status.set(str(error))
            return

        self.reverse_status.set("Complete — all calculated values are shown on the right.")

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _optional_hours(variable: tk.StringVar, *, signed: bool) -> float | None:
        text = variable.get().strip()
        return None if not text else parse_hours(text, signed=signed)

    @staticmethod
    def _optional_degrees(
        variable: tk.StringVar,
        minimum: float,
        maximum: float,
        label: str,
        *,
        wrap_360: bool = False,
    ) -> float | None:
        text = variable.get().strip()
        if not text:
            return None
        return parse_degrees(
            text,
            minimum=minimum,
            maximum=maximum,
            label=label,
            wrap_360=wrap_360,
        )

    def _set_derived(self, variable: tk.StringVar, text: str) -> None:
        self._programmatic_update = True
        try:
            variable.set(text)
        finally:
            self._programmatic_update = False

    def _clear_derived(self, variable: tk.StringVar) -> None:
        if variable.get():
            self._set_derived(variable, "")

    def _copy_values(self) -> None:
        fields = [
            ("Latitude", self.latitude_var.get()),
            ("RA", self.ra_var.get()),
            ("Dec", self.dec_var.get()),
            ("LST", self.lst_var.get()),
            ("Hour angle", self.ha_var.get()),
            ("Altitude", self.alt_var.get()),
            ("Azimuth", self.az_var.get()),
        ]
        text = "\n".join(f"{name}: {value}" for name, value in fields if value.strip())
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)

    def _clear_all(self) -> None:
        if self._solve_job is not None:
            try:
                self.after_cancel(self._solve_job)
            except tk.TclError:
                pass
            self._solve_job = None
        self._programmatic_update = True
        try:
            for variable in (
                self.latitude_var,
                self.ra_var,
                self.dec_var,
                self.lst_var,
                self.ha_var,
                self.alt_var,
                self.az_var,
            ):
                variable.set("")
        finally:
            self._programmatic_update = False
        self.forward_status.set(
            "Enter latitude, RA, Dec and LST. Results appear automatically."
        )
        self.reverse_status.set(
            "Enter latitude, altitude and azimuth. Add LST to also determine RA."
        )


def run_coordinate_converter() -> int:
    app = CoordinateConverterApplication()
    app.mainloop()
    return 0
