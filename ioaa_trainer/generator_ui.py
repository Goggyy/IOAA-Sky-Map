"""Standalone, fully configurable sky-map generator UI."""

from __future__ import annotations

import queue
import random
import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from .astronomy import AstronomyData, SkyMapCalculator, format_local_sidereal_time
from .generation_settings import load_generation_settings
from .models import MapSettings, SkyMapModel
from .rendering import RenderOptions, SkyMapRenderer
from .theme import apply_night_theme
from .time_utils import (
    datetime_for_local_sidereal_time,
    datetime_from_mjd,
    format_clock_hours,
    local_sidereal_time_hours,
    mjd_from_datetime,
    parse_clock_hours,
)
from .widgets import CelestialSphereSelector, ToggleSwitch, VerticalScrolledFrame


class SkyMapGeneratorApplication(tk.Tk):
    """Generate an analytical sky chart from an observer or a chosen zenith."""

    CALCULATION_MAGNITUDE_LIMIT = 8.0
    MAXIMUM_SKY_RADIUS = 180.0

    def __init__(self) -> None:
        super().__init__()
        self.title("IOAA Sky Map Generator")
        self.geometry("1280x860")
        self.minsize(1000, 710)

        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="ioaa-map-generator",
        )
        self._calculator = SkyMapCalculator(AstronomyData())
        self._progress_messages: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._generation = 0
        self._model: SkyMapModel | None = None
        self._source_description = "Observer location + time"
        self._live_update_job: str | None = None
        self._current_future: Future[SkyMapModel] | None = None
        self._input_trace_ids: list[tuple[tk.Variable, str]] = []
        self._zenith_drag_recalculation_pending = False

        self._build_variables()
        apply_night_theme(self, self.night_mode)
        self._build_ui()
        self._update_observation_states()
        self._update_rotation_state()
        self._install_live_updates()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(180, lambda: self._schedule_recalculation(delay_ms=0))

    def _build_variables(self) -> None:
        saved = load_generation_settings()
        self.night_mode = saved.night_mode
        now = datetime.now(timezone.utc).replace(microsecond=0)
        observation = saved.fixed_datetime() if saved.time_mode == "fixed_utc" else now
        latitude = saved.fixed_latitude
        longitude = saved.fixed_longitude

        self.position_mode_var = tk.StringVar(value="observer")
        self.latitude_var = tk.StringVar(value=f"{latitude:.6f}")
        self.longitude_var = tk.StringVar(value=f"{longitude:.6f}")

        self.time_input_var = tk.StringVar(value="UTC date/time")
        self.date_var = tk.StringVar(value=f"{observation:%Y-%m-%d}")
        self.time_var = tk.StringVar(value=f"{observation:%H:%M:%S}")
        self.lst_date_var = tk.StringVar(value=f"{observation:%Y-%m-%d}")
        self.lst_time_var = tk.StringVar(
            value=format_clock_hours(local_sidereal_time_hours(observation, longitude))
        )
        self.mjd_var = tk.StringVar(value=f"{mjd_from_datetime(observation):.6f}")

        self.zenith_ra_var = tk.DoubleVar(
            value=local_sidereal_time_hours(observation, longitude)
        )
        self.zenith_dec_var = tk.DoubleVar(value=latitude)
        self.zenith_date_var = tk.StringVar(value=f"{observation:%Y-%m-%d}")
        self.zenith_ra_value_var = tk.StringVar()
        self.zenith_dec_value_var = tk.StringVar()
        self.zenith_ra_input_var = tk.StringVar()
        self.zenith_dec_input_var = tk.StringVar()

        self.status_var = tk.StringVar(value="Preparing sky map…")
        self.metadata_var = tk.StringVar(value="No sky has been calculated yet.")

        self.direction_labels_var = tk.BooleanVar(value=False)
        self.altitude_grid_var = tk.BooleanVar(value=False)
        self.coordinate_grid_var = tk.BooleanVar(value=False)
        self.ecliptic_var = tk.BooleanVar(value=False)
        self.celestial_equator_var = tk.BooleanVar(value=False)
        self.galactic_equator_var = tk.BooleanVar(value=False)
        self.constellation_lines_var = tk.BooleanVar(value=False)
        self.constellation_names_var = tk.BooleanVar(value=False)
        self.star_names_var = tk.BooleanVar(value=False)
        self.solar_system_objects_var = tk.BooleanVar(value=False)
        self.solar_system_labels_var = tk.BooleanVar(value=False)
        self.zenith_label_var = tk.BooleanVar(value=False)
        self.title_var = tk.BooleanVar(value=False)

        self.inverted_colors_var = tk.BooleanVar(value=saved.inverted_colors)
        self.sky_radius_var = tk.DoubleVar(value=saved.sky_radius_degrees)
        self.sky_radius_value_var = tk.StringVar()
        self.magnitude_var = tk.DoubleVar(value=saved.faintest_visible_magnitude)
        self.magnitude_value_var = tk.StringVar()
        self.marker_scale_var = tk.DoubleVar(value=saved.star_marker_scale)
        self.marker_scale_value_var = tk.StringVar()
        self.rotation_enabled_var = tk.BooleanVar(value=False)
        self.rotation_var = tk.DoubleVar(value=0.0)
        self.rotation_value_var = tk.StringVar()
        self._update_view_readouts()
        self._update_zenith_readouts()

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        controls = ttk.Frame(self, padding=12)
        controls.grid(row=0, column=0, sticky="nsew")
        controls.columnconfigure(0, weight=1)
        controls.rowconfigure(1, weight=1)

        ttk.Label(
            controls,
            text="IOAA Sky Map Generator",
            font=("TkDefaultFont", 15, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        notebook = ttk.Notebook(controls)
        notebook.grid(row=1, column=0, sticky="nsew")
        observation_tab = ttk.Frame(notebook)
        layers_tab = ttk.Frame(notebook, padding=10)
        view_tab = ttk.Frame(notebook, padding=10)
        notebook.add(observation_tab, text="Observation")
        notebook.add(layers_tab, text="Layers")
        notebook.add(view_tab, text="View")
        observation_tab.columnconfigure(0, weight=1)
        observation_tab.rowconfigure(0, weight=1)
        observation_scroller = VerticalScrolledFrame(observation_tab, padding=10)
        observation_scroller.grid(row=0, column=0, sticky="nsew")
        self._build_observation_tab(observation_scroller.content)
        self._build_layers_tab(layers_tab)
        self._build_view_tab(view_tab)

        actions = ttk.Frame(controls)
        actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        actions.columnconfigure(0, weight=1)
        ttk.Label(
            actions,
            text="Live update enabled",
        ).grid(row=0, column=0, sticky="w")
        self.save_button = ttk.Button(
            actions,
            text="Save PNG…",
            command=self._save_png,
            state="disabled",
        )
        self.save_button.grid(row=0, column=1, sticky="e", padx=(10, 0))
        ttk.Label(
            controls,
            textvariable=self.status_var,
            wraplength=320,
            justify="left",
        ).grid(row=3, column=0, sticky="ew", pady=(10, 0))

        chart_frame = ttk.Frame(self, padding=(0, 8, 8, 8))
        chart_frame.grid(row=0, column=1, sticky="nsew")
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)
        self.figure = Figure(figsize=(8.7, 7.6), dpi=100)
        self.renderer = SkyMapRenderer(self.figure)
        self.renderer.set_night_mode(self.night_mode)
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        toolbar_frame = ttk.Frame(chart_frame)
        toolbar_frame.grid(row=1, column=0, sticky="ew")
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side="left")

        self.figure.set_facecolor(self.renderer.BACKGROUND)
        self.renderer.axes.set_facecolor(self.renderer.BACKGROUND)
        self.renderer.axes.set_axis_off()
        self.canvas.draw_idle()

    def _build_observation_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(0, weight=1)

        mode = ttk.LabelFrame(tab, text="How to place the sky", padding=9)
        mode.grid(row=0, column=0, sticky="ew")
        ttk.Radiobutton(
            mode,
            text="Observer location + time",
            variable=self.position_mode_var,
            value="observer",
            command=self._position_mode_changed,
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            mode,
            text="Directly set the zenith on the celestial sphere",
            variable=self.position_mode_var,
            value="zenith",
            command=self._position_mode_changed,
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        observer = ttk.LabelFrame(tab, text="Observer and time", padding=9)
        observer.grid(row=1, column=0, sticky="ew", pady=(9, 0))
        observer.columnconfigure(1, weight=1)
        ttk.Label(observer, text="Latitude (°)").grid(row=0, column=0, sticky="w")
        self.latitude_entry = ttk.Entry(observer, textvariable=self.latitude_var)
        self.latitude_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(observer, text="Longitude (°)").grid(
            row=1, column=0, sticky="w", pady=(5, 0)
        )
        self.longitude_entry = ttk.Entry(observer, textvariable=self.longitude_var)
        self.longitude_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(5, 0))
        ttk.Label(observer, text="Time input").grid(
            row=2, column=0, sticky="w", pady=(7, 0)
        )
        self.time_input_combo = ttk.Combobox(
            observer,
            textvariable=self.time_input_var,
            state="readonly",
            values=("UTC date/time", "LST + UTC date", "MJD"),
        )
        self.time_input_combo.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(7, 0))
        self.time_input_combo.bind("<<ComboboxSelected>>", self._time_input_changed)

        ttk.Label(observer, text="UTC date").grid(row=3, column=0, sticky="w", pady=(5, 0))
        self.utc_date_entry = ttk.Entry(observer, textvariable=self.date_var)
        self.utc_date_entry.grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=(5, 0))
        ttk.Label(observer, text="UTC time").grid(row=4, column=0, sticky="w", pady=(5, 0))
        self.utc_time_entry = ttk.Entry(observer, textvariable=self.time_var)
        self.utc_time_entry.grid(row=4, column=1, sticky="ew", padx=(8, 0), pady=(5, 0))

        ttk.Label(observer, text="LST reference date").grid(
            row=5, column=0, sticky="w", pady=(5, 0)
        )
        self.lst_date_entry = ttk.Entry(observer, textvariable=self.lst_date_var)
        self.lst_date_entry.grid(row=5, column=1, sticky="ew", padx=(8, 0), pady=(5, 0))
        ttk.Label(observer, text="LST").grid(row=6, column=0, sticky="w", pady=(5, 0))
        self.lst_time_entry = ttk.Entry(observer, textvariable=self.lst_time_var)
        self.lst_time_entry.grid(row=6, column=1, sticky="ew", padx=(8, 0), pady=(5, 0))

        ttk.Label(observer, text="MJD (UTC)").grid(row=7, column=0, sticky="w", pady=(5, 0))
        self.mjd_entry = ttk.Entry(observer, textvariable=self.mjd_var)
        self.mjd_entry.grid(row=7, column=1, sticky="ew", padx=(8, 0), pady=(5, 0))
        ttk.Label(
            observer,
            text=(
                "UTC uses YYYY-MM-DD and HH:MM:SS. LST accepts HH:MM:SS or "
                "decimal hours. Positive longitude is east."
            ),
            wraplength=300,
            justify="left",
        ).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(7, 0))

        zenith = ttk.LabelFrame(tab, text="Direct zenith", padding=9)
        zenith.grid(row=2, column=0, sticky="ew", pady=(9, 0))
        zenith.columnconfigure(0, weight=1)
        ttk.Label(
            zenith,
            text=(
                "Drag on the celestial-sphere projection to place the zenith. "
                "The highlighted boundary shows the part of the sphere included "
                "by the current distance-from-zenith setting."
            ),
            wraplength=300,
            justify="left",
        ).grid(row=0, column=0, sticky="ew")
        self.zenith_selector = CelestialSphereSelector(
            zenith,
            ra_variable=self.zenith_ra_var,
            dec_variable=self.zenith_dec_var,
            sky_radius_variable=self.sky_radius_var,
            command=self._zenith_selector_moved,
            release_command=self._zenith_selector_released,
            height=235,
        )
        self.zenith_selector.grid(row=1, column=0, sticky="ew", pady=(7, 0))
        readout = ttk.Frame(zenith)
        readout.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        readout.columnconfigure((0, 1), weight=1)
        ttk.Label(readout, textvariable=self.zenith_ra_value_var).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(readout, textvariable=self.zenith_dec_value_var).grid(
            row=0, column=1, sticky="e"
        )

        manual = ttk.LabelFrame(zenith, text="Precise RA / Dec", padding=8)
        manual.grid(row=3, column=0, sticky="ew", pady=(7, 0))
        manual.columnconfigure(1, weight=1)
        ttk.Label(manual, text="RA (hours or HH:MM:SS)").grid(
            row=0, column=0, sticky="w"
        )
        self.zenith_ra_entry = ttk.Entry(
            manual, textvariable=self.zenith_ra_input_var
        )
        self.zenith_ra_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(manual, text="Dec (°)").grid(
            row=1, column=0, sticky="w", pady=(5, 0)
        )
        self.zenith_dec_entry = ttk.Entry(
            manual, textvariable=self.zenith_dec_input_var
        )
        self.zenith_dec_entry.grid(
            row=1, column=1, sticky="ew", padx=(8, 0), pady=(5, 0)
        )
        self.apply_zenith_button = ttk.Button(
            manual,
            text="Apply precise coordinates",
            command=self._apply_manual_zenith,
        )
        self.apply_zenith_button.grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(7, 0)
        )
        self.zenith_ra_entry.bind("<Return>", self._apply_manual_zenith)
        self.zenith_dec_entry.bind("<Return>", self._apply_manual_zenith)
        ttk.Label(
            manual,
            text="RA accepts decimal hours or sexagesimal time; Dec accepts decimal degrees.",
            wraplength=280,
            justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 0))

        date_row = ttk.Frame(zenith)
        date_row.grid(row=4, column=0, sticky="ew", pady=(7, 0))
        date_row.columnconfigure(1, weight=1)
        ttk.Label(date_row, text="Reference UTC date").grid(row=0, column=0, sticky="w")
        self.zenith_date_entry = ttk.Entry(date_row, textvariable=self.zenith_date_var)
        self.zenith_date_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        metadata = ttk.LabelFrame(tab, text="Calculated observation", padding=9)
        metadata.grid(row=3, column=0, sticky="ew", pady=(9, 0))
        ttk.Label(
            metadata,
            textvariable=self.metadata_var,
            justify="left",
            wraplength=300,
        ).grid(row=0, column=0, sticky="ew")

        self._observer_inputs = (
            self.latitude_entry,
            self.longitude_entry,
            self.time_input_combo,
            self.utc_date_entry,
            self.utc_time_entry,
            self.lst_date_entry,
            self.lst_time_entry,
            self.mjd_entry,
        )
        self._zenith_inputs = (
            self.zenith_selector,
            self.zenith_ra_entry,
            self.zenith_dec_entry,
            self.apply_zenith_button,
            self.zenith_date_entry,
        )

    def _build_layers_tab(self, tab: ttk.Frame) -> None:
        layer_variables = [
            ("Horizon directions", self.direction_labels_var),
            ("Altitude/azimuth grid", self.altitude_grid_var),
            ("RA/Dec coordinate grid", self.coordinate_grid_var),
            ("Ecliptic", self.ecliptic_var),
            ("Celestial equator", self.celestial_equator_var),
            ("Galactic equator", self.galactic_equator_var),
            ("Constellation diagrams", self.constellation_lines_var),
            ("Constellation names", self.constellation_names_var),
            ("Bright-star names", self.star_names_var),
            ("Solar system objects", self.solar_system_objects_var),
            ("Solar system object names", self.solar_system_labels_var),
            ("Zenith label", self.zenith_label_var),
            ("Observation details title", self.title_var),
        ]
        for row, (label, variable) in enumerate(layer_variables):
            ToggleSwitch(
                tab,
                text=label,
                variable=variable,
                command=self._redraw,
            ).grid(row=row, column=0, sticky="w", pady=2)

        buttons = ttk.Frame(tab)
        buttons.grid(row=len(layer_variables), column=0, sticky="ew", pady=(10, 0))
        buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(buttons, text="All off", command=self._all_layers_off).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ttk.Button(buttons, text="Study view", command=self._study_view).grid(
            row=0, column=1, sticky="ew", padx=(4, 0)
        )

    def _build_view_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(0, weight=1)

        colours = ttk.LabelFrame(tab, text="Colours", padding=9)
        colours.grid(row=0, column=0, sticky="ew")
        ToggleSwitch(
            colours,
            text="Invert colours (white stars on black background)",
            variable=self.inverted_colors_var,
            command=self._redraw,
        ).grid(row=0, column=0, sticky="w")

        field = ttk.LabelFrame(tab, text="Field of view", padding=9)
        field.grid(row=1, column=0, sticky="ew", pady=(9, 0))
        field.columnconfigure(0, weight=1)
        self._build_scale(
            field,
            row=0,
            label="Distance from zenith",
            variable=self.sky_radius_var,
            value_variable=self.sky_radius_value_var,
            from_value=0.0,
            to_value=self.MAXIMUM_SKY_RADIUS,
            command=self._sky_radius_changed,
        )
        ttk.Label(
            field,
            text="0° is the zenith point, 90° is a hemisphere, and 180° is the full sky.",
            wraplength=300,
            justify="left",
        ).grid(row=2, column=0, sticky="ew", pady=(5, 0))

        stars = ttk.LabelFrame(tab, text="Stars", padding=9)
        stars.grid(row=2, column=0, sticky="ew", pady=(9, 0))
        stars.columnconfigure(0, weight=1)
        self._build_scale(
            stars,
            row=0,
            label="Faintest visible magnitude",
            variable=self.magnitude_var,
            value_variable=self.magnitude_value_var,
            from_value=-1.5,
            to_value=self.CALCULATION_MAGNITUDE_LIMIT,
            command=self._magnitude_changed,
        )
        self._build_scale(
            stars,
            row=2,
            label="Star marker scale",
            variable=self.marker_scale_var,
            value_variable=self.marker_scale_value_var,
            from_value=0.45,
            to_value=2.0,
            command=self._marker_scale_changed,
        )

        orientation = ttk.LabelFrame(tab, text="Chart orientation", padding=9)
        orientation.grid(row=3, column=0, sticky="ew", pady=(9, 0))
        orientation.columnconfigure(0, weight=1)
        self.rotation_switch = ToggleSwitch(
            orientation,
            text="Enable map rotation (otherwise north is up)",
            variable=self.rotation_enabled_var,
            command=self._rotation_enabled_changed,
        )
        self.rotation_switch.grid(row=0, column=0, sticky="w")
        self.rotation_scale = self._build_scale(
            orientation,
            row=1,
            label="Map rotation",
            variable=self.rotation_var,
            value_variable=self.rotation_value_var,
            from_value=0.0,
            to_value=360.0,
            command=self._rotation_changed,
        )
        orientation_buttons = ttk.Frame(orientation)
        orientation_buttons.grid(row=3, column=0, sticky="ew", pady=(7, 0))
        orientation_buttons.columnconfigure((0, 1), weight=1)
        self.north_up_button = ttk.Button(
            orientation_buttons,
            text="North up",
            command=lambda: self._set_rotation(0.0),
        )
        self.north_up_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.random_rotation_button = ttk.Button(
            orientation_buttons,
            text="Random rotation",
            command=lambda: self._set_rotation(random.uniform(0.0, 360.0)),
        )
        self.random_rotation_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(
            tab,
            text=(
                "The catalogue is calculated to magnitude 8.0 over the full "
                "celestial sphere. View controls redraw immediately, while observation "
                "inputs recalculate automatically after a short pause."
            ),
            wraplength=300,
            justify="left",
        ).grid(row=4, column=0, sticky="ew", pady=(9, 0))

    def _build_scale(
        self,
        parent: ttk.Widget,
        *,
        row: int,
        label: str,
        variable: tk.DoubleVar,
        value_variable: tk.StringVar,
        from_value: float,
        to_value: float,
        command,
    ) -> ttk.Scale:
        header = ttk.Frame(parent)
        header.grid(row=row, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=label).grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=value_variable).grid(row=0, column=1, sticky="e")
        scale = ttk.Scale(
            parent,
            from_=from_value,
            to=to_value,
            variable=variable,
            command=command,
        )
        scale.grid(row=row + 1, column=0, sticky="ew", pady=(5, 0))
        return scale

    def _time_input_changed(self, _event=None) -> None:
        self._update_observation_states()
        self._schedule_recalculation()

    def _position_mode_changed(self) -> None:
        self._update_observation_states()
        self._schedule_recalculation(delay_ms=120)

    def _install_live_updates(self) -> None:
        """Recalculate after editable observation inputs settle briefly."""
        variables: tuple[tk.Variable, ...] = (
            self.latitude_var,
            self.longitude_var,
            self.date_var,
            self.time_var,
            self.lst_date_var,
            self.lst_time_var,
            self.mjd_var,
            self.zenith_date_var,
        )
        for variable in variables:
            trace_id = variable.trace_add(
                "write",
                lambda *_args: self._schedule_recalculation(),
            )
            self._input_trace_ids.append((variable, trace_id))

    def _schedule_recalculation(self, *, delay_ms: int = 650) -> None:
        """Debounce expensive astronomical transformations for live editing."""
        if not self.winfo_exists():
            return
        if self._live_update_job is not None:
            try:
                self.after_cancel(self._live_update_job)
            except tk.TclError:
                pass
        self.status_var.set("Updating automatically after input settles…")
        self._live_update_job = self.after(
            max(0, int(delay_ms)),
            lambda: self.generate_map(show_errors=False),
        )

    def _apply_manual_zenith(self, _event=None) -> str:
        try:
            ra_hours = parse_clock_hours(self.zenith_ra_input_var.get())
        except ValueError:
            messagebox.showerror(
                "Invalid zenith coordinates",
                "RA must be decimal hours or HH:MM:SS between 0h and 24h.",
                parent=self,
            )
            return "break"
        try:
            declination = float(self.zenith_dec_input_var.get().strip())
        except ValueError:
            messagebox.showerror(
                "Invalid zenith coordinates",
                "Declination must be a number between -90 and +90 degrees.",
                parent=self,
            )
            return "break"
        if not -90.0 <= declination <= 90.0:
            messagebox.showerror(
                "Invalid zenith coordinates",
                "Declination must be between -90 and +90 degrees.",
                parent=self,
            )
            return "break"

        self.zenith_ra_var.set(ra_hours)
        self.zenith_dec_var.set(declination)
        self._update_zenith_readouts(sync_inputs=True)
        if self.position_mode_var.get() == "zenith":
            self._request_live_zenith_recalculation()
        return "break"

    def _zenith_selector_moved(self) -> None:
        self._update_zenith_readouts(sync_inputs=True)
        if self.position_mode_var.get() == "zenith":
            self._request_live_zenith_recalculation()

    def _zenith_selector_released(self) -> None:
        self._update_zenith_readouts(sync_inputs=True)
        if self.position_mode_var.get() == "zenith":
            self._request_live_zenith_recalculation()

    def _request_live_zenith_recalculation(self) -> None:
        """Continuously follow a dragged zenith without queuing stale maps.

        Only one astronomical calculation is allowed to run at a time. If the
        marker moves while that calculation is in progress, one follow-up
        calculation is queued using the newest RA and Dec. This keeps the map
        updating throughout a drag while avoiding an unbounded executor queue.
        """
        if self._current_future is not None and not self._current_future.done():
            self._zenith_drag_recalculation_pending = True
            self.status_var.set("Updating sky continuously as the zenith moves…")
            return
        self._zenith_drag_recalculation_pending = False
        self._schedule_recalculation(delay_ms=0)

    def _update_observation_states(self) -> None:
        if not hasattr(self, "_observer_inputs"):
            return
        observer_mode = self.position_mode_var.get() == "observer"
        for widget in (self.latitude_entry, self.longitude_entry, self.time_input_combo):
            widget.configure(state="normal" if observer_mode else "disabled")
        if observer_mode:
            self.time_input_combo.configure(state="readonly")
            time_form = self.time_input_var.get()
            utc_state = "normal" if time_form == "UTC date/time" else "disabled"
            lst_state = "normal" if time_form == "LST + UTC date" else "disabled"
            mjd_state = "normal" if time_form == "MJD" else "disabled"
        else:
            utc_state = lst_state = mjd_state = "disabled"
        for widget in (self.utc_date_entry, self.utc_time_entry):
            widget.configure(state=utc_state)
        for widget in (self.lst_date_entry, self.lst_time_entry):
            widget.configure(state=lst_state)
        self.mjd_entry.configure(state=mjd_state)
        zenith_enabled = not observer_mode
        self.zenith_selector.set_enabled(zenith_enabled)
        zenith_state = "normal" if zenith_enabled else "disabled"
        for widget in (
            self.zenith_ra_entry,
            self.zenith_dec_entry,
            self.apply_zenith_button,
            self.zenith_date_entry,
        ):
            widget.configure(state=zenith_state)

    def _update_rotation_state(self) -> None:
        if not hasattr(self, "rotation_scale"):
            return
        enabled = self.rotation_enabled_var.get()
        state = "normal" if enabled else "disabled"
        self.rotation_scale.configure(state=state)
        self.north_up_button.configure(state=state)
        self.random_rotation_button.configure(state=state)
        if not enabled:
            self.rotation_var.set(0.0)
            self.rotation_value_var.set("0.0°")

    def _parse_settings(self) -> MapSettings:
        if self.position_mode_var.get() == "zenith":
            latitude = float(self.zenith_dec_var.get())
            longitude = 0.0
            zenith_ra = float(self.zenith_ra_var.get()) % 24.0
            observation = datetime_for_local_sidereal_time(
                self.zenith_date_var.get(),
                zenith_ra,
                longitude,
            )
            self._source_description = (
                f"Direct zenith: RA {format_clock_hours(zenith_ra)}, "
                f"Dec {latitude:+.2f}°"
            )
        else:
            try:
                latitude = float(self.latitude_var.get().strip())
                longitude = float(self.longitude_var.get().strip())
            except ValueError as error:
                raise ValueError("Latitude and longitude must be numbers.") from error
            if not -90.0 <= latitude <= 90.0:
                raise ValueError("Latitude must be between -90 and +90 degrees.")
            if not -180.0 <= longitude <= 180.0:
                raise ValueError("Longitude must be between -180 and +180 degrees.")

            time_form = self.time_input_var.get()
            if time_form == "UTC date/time":
                try:
                    observation = datetime.strptime(
                        f"{self.date_var.get().strip()} {self.time_var.get().strip()}",
                        "%Y-%m-%d %H:%M:%S",
                    ).replace(tzinfo=timezone.utc)
                except ValueError as error:
                    raise ValueError(
                        "UTC date/time must use YYYY-MM-DD and HH:MM:SS."
                    ) from error
            elif time_form == "LST + UTC date":
                observation = datetime_for_local_sidereal_time(
                    self.lst_date_var.get(),
                    parse_clock_hours(self.lst_time_var.get()),
                    longitude,
                )
            elif time_form == "MJD":
                observation = datetime_from_mjd(float(self.mjd_var.get().strip()))
            else:
                raise ValueError("Select a supported time input form.")
            self._source_description = f"Observer location + {time_form}"

        rotation = float(self.rotation_var.get()) % 360.0 if self.rotation_enabled_var.get() else 0.0
        return MapSettings(
            latitude=latitude,
            longitude=longitude,
            observation_datetime=observation,
            limiting_magnitude=self.CALCULATION_MAGNITUDE_LIMIT,
            map_rotation_degrees=rotation,
            include_solar_system_objects=True,
            inverted_colors=self.inverted_colors_var.get(),
            sky_radius_degrees=self.MAXIMUM_SKY_RADIUS,
            star_marker_scale=float(self.marker_scale_var.get()),
        )

    def generate_map(self, *, show_errors: bool = True) -> None:
        """Start a live sky calculation from the current complete inputs."""
        self._live_update_job = None
        try:
            settings = self._parse_settings()
        except (TypeError, ValueError) as error:
            self.status_var.set(f"Waiting for complete observation input: {error}")
            if show_errors:
                messagebox.showerror("Invalid observation", str(error), parent=self)
            return

        self._generation += 1
        generation = self._generation
        self.status_var.set("Calculating star positions…")
        while True:
            try:
                self._progress_messages.get_nowait()
            except queue.Empty:
                break

        if self._current_future is not None and not self._current_future.done():
            self._current_future.cancel()

        def calculate() -> SkyMapModel:
            return self._calculator.calculate(
                settings,
                progress=self._progress_messages.put,
            )

        future = self._executor.submit(calculate)
        self._current_future = future
        self.after(80, lambda: self._poll_future(future, generation))

    def _poll_future(self, future: Future[SkyMapModel], generation: int) -> None:
        if generation != self._generation or not self.winfo_exists():
            return
        latest: str | None = None
        while True:
            try:
                latest = self._progress_messages.get_nowait()
            except queue.Empty:
                break
        if latest:
            self.status_var.set(latest)
        if not future.done():
            self.after(80, lambda: self._poll_future(future, generation))
            return
        try:
            model = future.result()
        except Exception as error:
            self.status_var.set("Sky-map calculation failed.")
            messagebox.showerror(
                "Could not generate sky map",
                f"{type(error).__name__}: {error}",
                parent=self,
            )
            return

        self._model = model
        self.save_button.configure(state="normal")
        self.status_var.set(
            f"Sky ready with {len(model.stars.hip):,} catalogue stars in the calculated field."
        )
        self._redraw()

        if (
            self._zenith_drag_recalculation_pending
            and self.position_mode_var.get() == "zenith"
        ):
            self._zenith_drag_recalculation_pending = False
            self._schedule_recalculation(delay_ms=0)

    def _refresh_metadata(self, model: SkyMapModel) -> None:
        settings = model.settings
        utc = settings.observation_datetime.astimezone(timezone.utc)
        zenith_ra = format_local_sidereal_time(settings)
        self.metadata_var.set(
            f"{self._source_description}\n"
            f"Latitude: {settings.latitude:.5f}°\n"
            f"Longitude: {settings.longitude:.5f}°\n"
            f"UTC: {utc:%Y-%m-%d %H:%M:%S}\n"
            f"MJD: {mjd_from_datetime(utc):.6f}\n"
            f"LST / zenith RA: {zenith_ra}\n"
            f"Zenith Dec: {settings.latitude:+.5f}°\n"
            f"Map rotation: {settings.map_rotation_degrees:.1f}°\n"
            f"Visible solar-system objects: {len(model.solar_system_objects)}"
        )

    def _render_options(self) -> RenderOptions:
        return RenderOptions(
            show_direction_labels=self.direction_labels_var.get(),
            show_altitude_grid=self.altitude_grid_var.get(),
            show_title=self.title_var.get(),
            show_ecliptic=self.ecliptic_var.get(),
            show_celestial_equator=self.celestial_equator_var.get(),
            show_galactic_equator=self.galactic_equator_var.get(),
            show_constellation_names=self.constellation_names_var.get(),
            show_constellation_lines=self.constellation_lines_var.get(),
            show_star_names=self.star_names_var.get(),
            show_coordinate_grid=self.coordinate_grid_var.get(),
            show_solar_system_objects=self.solar_system_objects_var.get(),
            show_solar_system_labels=self.solar_system_labels_var.get(),
            show_zenith_label=self.zenith_label_var.get(),
            limiting_magnitude=self.magnitude_var.get(),
            star_marker_scale=self.marker_scale_var.get(),
        )

    def _redraw(self) -> None:
        if self._model is None:
            return
        rotation = (
            float(self.rotation_var.get()) % 360.0
            if self.rotation_enabled_var.get()
            else 0.0
        )
        display_model = replace(
            self._model,
            settings=replace(
                self._model.settings,
                map_rotation_degrees=rotation,
                inverted_colors=self.inverted_colors_var.get(),
                sky_radius_degrees=float(self.sky_radius_var.get()),
                star_marker_scale=float(self.marker_scale_var.get()),
            ),
        )
        self._refresh_metadata(display_model)
        self.renderer.draw(display_model, self._render_options())
        self.canvas.draw_idle()

    def _update_view_readouts(self) -> None:
        radius = float(self.sky_radius_var.get())
        if abs(radius - 180.0) < 0.6:
            radius_text = f"{radius:.0f}° (full sky)"
        elif abs(radius - 90.0) < 0.6:
            radius_text = f"{radius:.0f}° (hemisphere)"
        else:
            radius_text = f"{radius:.0f}°"
        self.sky_radius_value_var.set(radius_text)
        self.magnitude_value_var.set(f"{float(self.magnitude_var.get()):.1f}")
        self.marker_scale_value_var.set(f"{float(self.marker_scale_var.get()):.2f}×")
        self.rotation_value_var.set(f"{float(self.rotation_var.get()) % 360.0:.1f}°")

    def _update_zenith_readouts(self, *, sync_inputs: bool = True) -> None:
        ra_hours = float(self.zenith_ra_var.get()) % 24.0
        declination = float(self.zenith_dec_var.get())
        self.zenith_ra_value_var.set(
            f"Zenith RA: {format_clock_hours(ra_hours)}"
        )
        self.zenith_dec_value_var.set(
            f"Zenith Dec: {declination:+.4f}°"
        )
        if sync_inputs:
            self.zenith_ra_input_var.set(f"{ra_hours:.8f}")
            self.zenith_dec_input_var.set(f"{declination:.8f}")

    def _magnitude_changed(self, value: str) -> None:
        self.magnitude_value_var.set(f"{float(value):.1f}")
        self._redraw()

    def _sky_radius_changed(self, value: str) -> None:
        radius = float(value)
        if abs(radius - 180.0) < 0.6:
            radius_text = f"{radius:.0f}° (full sky)"
        elif abs(radius - 90.0) < 0.6:
            radius_text = f"{radius:.0f}° (hemisphere)"
        else:
            radius_text = f"{radius:.0f}°"
        self.sky_radius_value_var.set(radius_text)
        self._redraw()

    def _rotation_changed(self, value: str) -> None:
        numeric = float(value) % 360.0
        self.rotation_value_var.set(f"{numeric:.1f}°")
        self._redraw()

    def _marker_scale_changed(self, value: str) -> None:
        self.marker_scale_value_var.set(f"{float(value):.2f}×")
        self._redraw()

    def _rotation_enabled_changed(self) -> None:
        self._update_rotation_state()
        self._redraw()

    def _set_rotation(self, value: float) -> None:
        self.rotation_var.set(value % 360.0)
        self.rotation_value_var.set(f"{value % 360.0:.1f}°")
        self._redraw()

    def _all_layers_off(self) -> None:
        for variable in self._layer_variables():
            variable.set(False)
        self._redraw()

    def _study_view(self) -> None:
        for variable in self._layer_variables():
            variable.set(True)
        self._redraw()

    def _layer_variables(self) -> tuple[tk.BooleanVar, ...]:
        return (
            self.direction_labels_var,
            self.altitude_grid_var,
            self.coordinate_grid_var,
            self.ecliptic_var,
            self.celestial_equator_var,
            self.galactic_equator_var,
            self.constellation_lines_var,
            self.constellation_names_var,
            self.star_names_var,
            self.solar_system_objects_var,
            self.solar_system_labels_var,
            self.zenith_label_var,
            self.title_var,
        )

    def _save_png(self) -> None:
        if self._model is None:
            return
        utc = self._model.settings.observation_datetime.astimezone(timezone.utc)
        filename = filedialog.asksaveasfilename(
            parent=self,
            title="Save generated sky map",
            defaultextension=".png",
            initialfile=f"sky_map_{utc:%Y%m%d_%H%M%S}.png",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            self.figure.savefig(
                filename,
                dpi=220,
                bbox_inches="tight",
                facecolor=self.figure.get_facecolor(),
            )
        except OSError as error:
            messagebox.showerror("Could not save image", str(error), parent=self)

    def _on_close(self) -> None:
        self._generation += 1
        self._zenith_drag_recalculation_pending = False
        if self._live_update_job is not None:
            try:
                self.after_cancel(self._live_update_job)
            except tk.TclError:
                pass
        for variable, trace_id in self._input_trace_ids:
            try:
                variable.trace_remove("write", trace_id)
            except (tk.TclError, ValueError):
                pass
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.destroy()


def run_generator() -> int:
    app = SkyMapGeneratorApplication()
    app.mainloop()
    return 0
