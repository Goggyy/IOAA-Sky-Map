"""Full-featured analysis window for the current random sky."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from zoneinfo import ZoneInfo

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from .activity_api import SkyActivity
from .astronomy import format_local_sidereal_time
from .models import QuestionBundle
from .rendering import RenderOptions, SkyMapRenderer
from .theme import apply_night_theme, night_mode_enabled
from .widgets import ToggleSwitch


class AnalysisWindow(tk.Toplevel):
    """Inspect the current question with independently toggleable layers."""

    def __init__(
        self,
        parent: tk.Misc,
        bundle: QuestionBundle,
        activity: SkyActivity,
    ) -> None:
        super().__init__(parent)
        self.bundle = bundle
        self.activity = activity
        self.night_mode = night_mode_enabled(parent)
        apply_night_theme(self, self.night_mode)
        self.title(f"Analyse current sky — {activity.title}")
        self.geometry("1240x820")
        self.minsize(960, 680)

        self._build_variables()
        self._build_ui()
        self._redraw()

    def _build_variables(self) -> None:
        # The analysis page starts with the same clean star-only chart as the
        # exercise. Students can then add one reference layer at a time.
        self.direction_labels_var = tk.BooleanVar(value=False)
        self.altitude_grid_var = tk.BooleanVar(value=False)
        self.coordinate_grid_var = tk.BooleanVar(value=False)
        self.ecliptic_var = tk.BooleanVar(value=False)
        self.celestial_equator_var = tk.BooleanVar(value=False)
        self.galactic_equator_var = tk.BooleanVar(value=False)
        self.constellation_lines_var = tk.BooleanVar(value=False)
        self.constellation_names_var = tk.BooleanVar(value=False)
        self.star_names_var = tk.BooleanVar(value=False)
        self.answer_var = tk.BooleanVar(value=False)
        self.solar_system_objects_var = tk.BooleanVar(value=False)
        self.solar_system_labels_var = tk.BooleanVar(value=False)
        self.zenith_label_var = tk.BooleanVar(value=False)
        self.title_var = tk.BooleanVar(value=False)
        self.magnitude_var = tk.DoubleVar(
            value=self.bundle.model.settings.limiting_magnitude
        )
        self.magnitude_value_var = tk.StringVar(
            value=f"{self.magnitude_var.get():.1f}"
        )
        self.status_var = tk.StringVar(
            value="All overlays start off. Add layers or adjust the stellar magnitude limit."
        )

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        controls = ttk.Frame(self, padding=12)
        controls.grid(row=0, column=0, sticky="nsew")
        controls.columnconfigure(0, weight=1)

        prompt_frame = ttk.LabelFrame(controls, text="Question", padding=10)
        prompt_frame.grid(row=0, column=0, sticky="ew")
        ttk.Label(
            prompt_frame,
            text=self.bundle.question.prompt,
            wraplength=285,
            justify="left",
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(
            prompt_frame,
            text=self.bundle.question.answer_text,
            wraplength=285,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(7, 0))

        layers = ttk.LabelFrame(controls, text="Visible layers", padding=10)
        layers.grid(row=1, column=0, sticky="ew", pady=(12, 0))

        layer_variables = [
            ("Horizon directions", self.direction_labels_var),
            ("Altitude/azimuth grid", self.altitude_grid_var),
            ("RA/Dec coordinate grid", self.coordinate_grid_var),
            ("Ecliptic", self.ecliptic_var),
            ("Celestial equator", self.celestial_equator_var),
            ("Galactic equator", self.galactic_equator_var),
            ("All constellation diagrams", self.constellation_lines_var),
            ("Constellation names", self.constellation_names_var),
            ("Bright-star names", self.star_names_var),
            ("Solar system objects", self.solar_system_objects_var),
            ("Solar system object names", self.solar_system_labels_var),
            ("Zenith label", self.zenith_label_var),
            ("Exercise answer highlight", self.answer_var),
            ("Observation details title", self.title_var),
        ]
        for row, (label, variable) in enumerate(layer_variables):
            ToggleSwitch(
                layers,
                text=label,
                variable=variable,
                command=self._redraw,
            ).grid(row=row, column=0, sticky="w", pady=1)

        stars = ttk.LabelFrame(controls, text="Star visibility", padding=10)
        stars.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        stars.columnconfigure(0, weight=1)

        magnitude_header = ttk.Frame(stars)
        magnitude_header.grid(row=0, column=0, sticky="ew")
        magnitude_header.columnconfigure(0, weight=1)
        ttk.Label(magnitude_header, text="Faintest visible magnitude").grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(
            magnitude_header,
            textvariable=self.magnitude_value_var,
            width=4,
            anchor="e",
        ).grid(row=0, column=1, sticky="e")

        self.magnitude_scale = ttk.Scale(
            stars,
            from_=-1.5,
            to=self.bundle.model.settings.limiting_magnitude,
            variable=self.magnitude_var,
            command=self._magnitude_changed,
        )
        self.magnitude_scale.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        ttk.Label(
            stars,
            text="Lower values show only brighter stars; higher values include fainter stars.",
            wraplength=275,
            justify="left",
        ).grid(row=2, column=0, sticky="ew", pady=(5, 0))

        metadata = ttk.LabelFrame(controls, text="Revealed sky", padding=10)
        metadata.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        settings = self.bundle.model.settings
        utc_time = settings.observation_datetime.astimezone(ZoneInfo("UTC"))
        metadata_text = (
            f"Latitude: {settings.latitude:.5f}°\n"
            f"Longitude: {settings.longitude:.5f}°\n"
            f"Time: {utc_time:%Y-%m-%d %H:%M:%S} UTC\n"
            f"LST: {format_local_sidereal_time(settings)}\n"
            f"Map rotation: {settings.map_rotation_degrees:.1f}°\n"
            f"Solar-system data: "
            f"{'included' if settings.include_solar_system_objects else 'not included'}\n"
            f"Question seed: {self.bundle.seed}"
        )
        ttk.Label(
            metadata,
            text=metadata_text,
            justify="left",
        ).grid(row=0, column=0, sticky="ew")

        actions = ttk.Frame(controls)
        actions.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        actions.columnconfigure((0, 1), weight=1)
        ttk.Button(actions, text="Save PNG…", command=self._save_png).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 4),
        )
        ttk.Button(actions, text="Close", command=self.destroy).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(4, 0),
        )

        ttk.Label(
            controls,
            textvariable=self.status_var,
            wraplength=285,
            justify="left",
        ).grid(row=5, column=0, sticky="ew", pady=(12, 0))

        chart_frame = ttk.Frame(self, padding=(0, 8, 8, 8))
        chart_frame.grid(row=0, column=1, sticky="nsew")
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)

        self.figure = Figure(figsize=(8.5, 7.5), dpi=100)
        self.renderer = SkyMapRenderer(self.figure)
        self.renderer.set_night_mode(self.night_mode)
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        toolbar_frame = ttk.Frame(chart_frame)
        toolbar_frame.grid(row=1, column=0, sticky="ew")
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side="left")

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
        )

    def _magnitude_changed(self, value: str) -> None:
        """Update the readout and redraw while the scale is being moved."""
        try:
            magnitude = float(value)
        except (TypeError, ValueError):
            magnitude = self.magnitude_var.get()
        self.magnitude_value_var.set(f"{magnitude:.1f}")
        if hasattr(self, "renderer") and hasattr(self, "canvas"):
            self._redraw()

    def _redraw(self) -> None:
        def overlay(renderer: SkyMapRenderer, model) -> None:
            self.activity.draw_question(
                renderer,
                model,
                self.bundle.question,
            )
            if self.answer_var.get():
                self.activity.draw_answer(
                    renderer,
                    model,
                    self.bundle.question,
                )

        self.renderer.draw(self.bundle.model, self._render_options(), overlay)
        self.canvas.draw_idle()

    def _save_png(self) -> None:
        initial_name = f"ioaa_analysis_{self.bundle.seed}.png"
        filename = filedialog.asksaveasfilename(
            parent=self,
            title="Save sky analysis",
            defaultextension=".png",
            initialfile=initial_name,
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
            return
        self.status_var.set(f"Saved {filename}")
