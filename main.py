"""Launcher, random-sky settings, exercises, and tools for the IOAA sky trainer."""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox, ttk
from types import ModuleType
from typing import Type

from ioaa_trainer.activity_api import SkyActivity
from ioaa_trainer.generation_settings import (
    GenerationSettings,
    load_generation_settings,
    save_generation_settings,
)
from ioaa_trainer.help_ui import HelpWindow
from ioaa_trainer.tool_api import SkyTool
from ioaa_trainer.theme import apply_night_theme
from ioaa_trainer.widgets import ToggleSwitch, VerticalScrolledFrame

PROJECT_ROOT = Path(__file__).resolve().parent
ACTIVITIES_DIRECTORY = PROJECT_ROOT / "activities"
TOOLS_DIRECTORY = PROJECT_ROOT / "tools"

TIME_MODE_LABELS = {
    "random": "Random UTC date and time",
    "fixed_utc": "Fixed UTC date and time",
    "fixed_lst": "Fixed local sidereal time (LST)",
    "fixed_mjd": "Fixed Modified Julian Date (MJD)",
}
TIME_MODE_VALUES = {label: value for value, label in TIME_MODE_LABELS.items()}


@dataclass(frozen=True)
class DiscoveredActivity:
    module: ModuleType
    activity_class: Type[SkyActivity]
    file_path: Path

    @property
    def instance(self) -> SkyActivity:
        return self.activity_class()


def discover_activities() -> list[DiscoveredActivity]:
    activities: list[DiscoveredActivity] = []
    for file_path in sorted(ACTIVITIES_DIRECTORY.glob("activity_*.py")):
        module_name = f"activities.{file_path.stem}"
        module = importlib.import_module(module_name)
        activity_class = getattr(module, "ACTIVITY_CLASS", None)
        if (
            not isinstance(activity_class, type)
            or not issubclass(activity_class, SkyActivity)
        ):
            continue
        activities.append(
            DiscoveredActivity(
                module=module,
                activity_class=activity_class,
                file_path=file_path,
            )
        )
    activities.sort(key=lambda item: item.instance.title)
    return activities


@dataclass(frozen=True)
class DiscoveredTool:
    module: ModuleType
    tool_class: Type[SkyTool]
    file_path: Path

    @property
    def instance(self) -> SkyTool:
        return self.tool_class()


def discover_tools() -> list[DiscoveredTool]:
    tools: list[DiscoveredTool] = []
    for file_path in sorted(TOOLS_DIRECTORY.glob("tool_*.py")):
        module_name = f"tools.{file_path.stem}"
        module = importlib.import_module(module_name)
        tool_class = getattr(module, "TOOL_CLASS", None)
        if not isinstance(tool_class, type) or not issubclass(tool_class, SkyTool):
            continue
        tools.append(
            DiscoveredTool(
                module=module,
                tool_class=tool_class,
                file_path=file_path,
            )
        )
    tools.sort(key=lambda item: item.instance.title)
    return tools


class Launcher(tk.Tk):
    def __init__(
        self,
        activities: list[DiscoveredActivity],
        tools: list[DiscoveredTool],
    ) -> None:
        super().__init__()
        self.activities = activities
        self.tools = tools
        self._loaded_settings = load_generation_settings()
        self.title("IOAA Blind Sky Trainer")
        self.geometry("820x900")
        self.minsize(650, 680)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_variables()
        apply_night_theme(self, self.night_mode_var.get())
        self._build_ui()
        self._update_constraint_states()

    def _build_variables(self) -> None:
        settings = self._loaded_settings
        fixed_time = settings.fixed_datetime()
        self.include_solar_var = tk.BooleanVar(
            value=settings.include_solar_system_objects
        )
        self.coordinate_mode_var = tk.StringVar(value=settings.coordinate_mode)
        self.latitude_var = tk.StringVar(value=f"{settings.fixed_latitude:.6f}")
        self.longitude_var = tk.StringVar(value=f"{settings.fixed_longitude:.6f}")
        self.time_mode_var = tk.StringVar(value=settings.time_mode)
        self.time_mode_display_var = tk.StringVar(
            value=TIME_MODE_LABELS.get(settings.time_mode, TIME_MODE_LABELS["random"])
        )
        self.fixed_date_var = tk.StringVar(value=f"{fixed_time:%Y-%m-%d}")
        self.fixed_time_var = tk.StringVar(value=f"{fixed_time:%H:%M:%S}")
        self.fixed_lst_date_var = tk.StringVar(value=settings.fixed_lst_date)
        self.fixed_lst_time_var = tk.StringVar(value=settings.fixed_lst_time)
        self.fixed_mjd_var = tk.StringVar(value=f"{float(settings.fixed_mjd):.6f}")

        self.inverted_colors_var = tk.BooleanVar(value=settings.inverted_colors)
        self.night_mode_var = tk.BooleanVar(value=settings.night_mode)
        self.enable_map_rotation_var = tk.BooleanVar(value=settings.enable_map_rotation)
        self.sky_radius_var = tk.DoubleVar(value=settings.sky_radius_degrees)
        self.sky_radius_value_var = tk.StringVar()
        self.faintest_magnitude_var = tk.DoubleVar(
            value=settings.faintest_visible_magnitude
        )
        self.faintest_magnitude_value_var = tk.StringVar()
        self.star_marker_scale_var = tk.DoubleVar(value=settings.star_marker_scale)
        self.star_marker_scale_value_var = tk.StringVar()
        self._update_view_readouts()

        self.settings_status_var = tk.StringVar(
            value="Random-sky settings are saved locally."
        )

    def _build_ui(self) -> None:
        frame = ttk.Frame(self, padding=22)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        header = ttk.Frame(frame)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="IOAA Blind Sky Trainer",
            font=("TkDefaultFont", 18, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            header,
            text="Instructions & About…",
            command=self._open_help,
        ).grid(row=0, column=1, sticky="e", padx=(16, 0))
        ttk.Label(
            frame,
            text=(
                "Choose an exercise from the main page. Tools and random-sky "
                "constraints are available in the secondary tabs."
            ),
            wraplength=700,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(6, 16))

        self.notebook = ttk.Notebook(frame)
        self.notebook.grid(row=2, column=0, sticky="nsew")

        activities_tab = ttk.Frame(self.notebook, padding=14)
        tools_tab = ttk.Frame(self.notebook, padding=14)
        settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(activities_tab, text="Exercises")
        self.notebook.add(tools_tab, text="Tools")
        self.notebook.add(settings_tab, text="Random sky settings")
        self._build_activities_tab(activities_tab)
        self._build_tools_tab(tools_tab)
        settings_tab.columnconfigure(0, weight=1)
        settings_tab.rowconfigure(0, weight=1)
        settings_scroller = VerticalScrolledFrame(settings_tab, padding=14)
        settings_scroller.grid(row=0, column=0, sticky="nsew")
        self._build_settings_tab(settings_scroller.content)
        self.notebook.select(activities_tab)

        ttk.Label(
            frame,
            text=(
                "First use requires internet access to cache the Hipparcos "
                "catalogue and Stellarium constellation line data."
            ),
            wraplength=700,
            justify="left",
        ).grid(row=3, column=0, sticky="ew", pady=(14, 0))

    def _build_activities_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        introduction = ttk.Frame(tab)
        introduction.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        introduction.columnconfigure(0, weight=1)
        ttk.Label(
            introduction,
            text="Training exercises",
            font=("TkDefaultFont", 14, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            introduction,
            text=(
                "Open an exercise, solve the blind chart, reveal the answer, "
                "then inspect the same sky in the analysis window."
            ),
            wraplength=650,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

        exercise_frame = ttk.LabelFrame(tab, text="Available exercises", padding=12)
        exercise_frame.grid(row=1, column=0, sticky="nsew")
        exercise_frame.columnconfigure(0, weight=1)

        if not self.activities:
            ttk.Label(exercise_frame, text="No exercise modules were found.").grid(
                row=0,
                column=0,
                sticky="w",
            )
            return

        for row, discovered in enumerate(self.activities):
            exercise = discovered.instance
            item = ttk.Frame(exercise_frame)
            item.grid(row=row, column=0, sticky="ew", pady=(0 if row == 0 else 10, 0))
            item.columnconfigure(0, weight=1)
            ttk.Label(
                item,
                text=exercise.title,
                font=("TkDefaultFont", 11, "bold"),
            ).grid(row=0, column=0, sticky="w")
            ttk.Label(
                item,
                text=exercise.description,
                wraplength=530,
                justify="left",
            ).grid(row=1, column=0, sticky="ew", pady=(2, 0))
            ttk.Button(
                item,
                text="Open",
                command=lambda selected=discovered: self._launch_exercise(selected),
            ).grid(row=0, column=1, rowspan=2, sticky="e", padx=(12, 0))

    def _build_tools_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        introduction = ttk.Frame(tab)
        introduction.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        introduction.columnconfigure(0, weight=1)
        ttk.Label(
            introduction,
            text="Tools",
            font=("TkDefaultFont", 14, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            introduction,
            text=(
                "Open a supporting astronomy utility. New tools can be added as "
                "independent modules and are discovered automatically."
            ),
            wraplength=650,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

        tool_frame = ttk.LabelFrame(tab, text="Available tools", padding=12)
        tool_frame.grid(row=1, column=0, sticky="nsew")
        tool_frame.columnconfigure(0, weight=1)

        if not self.tools:
            ttk.Label(tool_frame, text="No tool modules were found.").grid(
                row=0,
                column=0,
                sticky="w",
            )
            return

        for row, discovered in enumerate(self.tools):
            tool = discovered.instance
            item = ttk.Frame(tool_frame)
            item.grid(row=row, column=0, sticky="ew", pady=(0 if row == 0 else 10, 0))
            item.columnconfigure(0, weight=1)
            ttk.Label(
                item,
                text=tool.title,
                font=("TkDefaultFont", 11, "bold"),
            ).grid(row=0, column=0, sticky="w")
            ttk.Label(
                item,
                text=tool.description,
                wraplength=530,
                justify="left",
            ).grid(row=1, column=0, sticky="ew", pady=(2, 0))
            ttk.Button(
                item,
                text="Open",
                command=lambda selected=discovered: self._launch_tool(selected),
            ).grid(row=0, column=1, rowspan=2, sticky="e", padx=(12, 0))

    def _build_settings_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(0, weight=1)

        objects = ttk.LabelFrame(tab, text="Objects included in blind maps", padding=10)
        objects.grid(row=0, column=0, sticky="ew")
        ToggleSwitch(
            objects,
            text="Include visible Sun, Moon, and planets",
            variable=self.include_solar_var,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            objects,
            text=(
                "When enabled, solar-system objects appear as unlabelled markers. "
                "The default remains the original star-only chart."
            ),
            wraplength=650,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

        coordinates = ttk.LabelFrame(tab, text="Observer coordinates", padding=10)
        coordinates.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        coordinates.columnconfigure(1, weight=1)
        ttk.Radiobutton(
            coordinates,
            text="Random coordinates",
            variable=self.coordinate_mode_var,
            value="random",
            command=self._update_constraint_states,
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Radiobutton(
            coordinates,
            text="Fixed coordinates",
            variable=self.coordinate_mode_var,
            value="fixed",
            command=self._update_constraint_states,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 5))
        ttk.Label(coordinates, text="Latitude (°)").grid(row=2, column=0, sticky="w")
        self.latitude_entry = ttk.Entry(coordinates, textvariable=self.latitude_var)
        self.latitude_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0))
        ttk.Label(coordinates, text="Longitude (°)").grid(
            row=3, column=0, sticky="w", pady=(5, 0)
        )
        self.longitude_entry = ttk.Entry(coordinates, textvariable=self.longitude_var)
        self.longitude_entry.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=(5, 0))

        time_frame = ttk.LabelFrame(tab, text="Observation time", padding=10)
        time_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        time_frame.columnconfigure(1, weight=1)
        ttk.Label(time_frame, text="Input form").grid(row=0, column=0, sticky="w")
        self.time_mode_combo = ttk.Combobox(
            time_frame,
            textvariable=self.time_mode_display_var,
            state="readonly",
            values=tuple(TIME_MODE_LABELS.values()),
        )
        self.time_mode_combo.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        self.time_mode_combo.bind("<<ComboboxSelected>>", self._time_mode_changed)
        ttk.Label(
            time_frame,
            text="LST uses the selected longitude and a UTC reference date.",
            wraplength=650,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(3, 6))

        ttk.Label(time_frame, text="UTC date (YYYY-MM-DD)").grid(row=2, column=0, sticky="w")
        self.date_entry = ttk.Entry(time_frame, textvariable=self.fixed_date_var)
        self.date_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0))
        ttk.Label(time_frame, text="UTC time (HH:MM:SS)").grid(
            row=3, column=0, sticky="w", pady=(4, 0)
        )
        self.time_entry = ttk.Entry(time_frame, textvariable=self.fixed_time_var)
        self.time_entry.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=(4, 0))

        ttk.Label(time_frame, text="LST reference date").grid(
            row=4, column=0, sticky="w", pady=(4, 0)
        )
        self.lst_date_entry = ttk.Entry(time_frame, textvariable=self.fixed_lst_date_var)
        self.lst_date_entry.grid(row=4, column=1, sticky="ew", padx=(10, 0), pady=(4, 0))
        ttk.Label(time_frame, text="LST (HH:MM:SS or hours)").grid(
            row=5, column=0, sticky="w", pady=(4, 0)
        )
        self.lst_time_entry = ttk.Entry(time_frame, textvariable=self.fixed_lst_time_var)
        self.lst_time_entry.grid(row=5, column=1, sticky="ew", padx=(10, 0), pady=(4, 0))

        ttk.Label(time_frame, text="MJD (UTC)").grid(
            row=6, column=0, sticky="w", pady=(4, 0)
        )
        self.mjd_entry = ttk.Entry(time_frame, textvariable=self.fixed_mjd_var)
        self.mjd_entry.grid(row=6, column=1, sticky="ew", padx=(10, 0), pady=(4, 0))

        view = ttk.LabelFrame(tab, text="View", padding=10)
        view.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        view.columnconfigure(0, weight=1)
        ToggleSwitch(
            view,
            text="Invert map colours (white stars on black background)",
            variable=self.inverted_colors_var,
        ).grid(row=0, column=0, sticky="w")
        ToggleSwitch(
            view,
            text="Night mode (red-only interface and charts)",
            variable=self.night_mode_var,
            command=self._night_mode_changed,
        ).grid(row=1, column=0, sticky="w", pady=(5, 0))
        ToggleSwitch(
            view,
            text="Randomise map rotation (otherwise north is up)",
            variable=self.enable_map_rotation_var,
        ).grid(row=2, column=0, sticky="w", pady=(5, 0))
        self._build_scale(
            view,
            row=3,
            label="Sky coverage from zenith",
            variable=self.sky_radius_var,
            value_variable=self.sky_radius_value_var,
            from_value=0.0,
            to_value=180.0,
            command=self._view_setting_changed,
        )
        self._build_scale(
            view,
            row=5,
            label="Faintest visible magnitude",
            variable=self.faintest_magnitude_var,
            value_variable=self.faintest_magnitude_value_var,
            from_value=-1.5,
            to_value=8.0,
            command=self._view_setting_changed,
        )
        self._build_scale(
            view,
            row=7,
            label="Star marker scale",
            variable=self.star_marker_scale_var,
            value_variable=self.star_marker_scale_value_var,
            from_value=0.45,
            to_value=2.0,
            command=self._view_setting_changed,
        )
        ttk.Label(
            view,
            text=(
                "0° is the zenith point, 90° is one hemisphere ending at the "
                "horizon, and 180° is the full celestial sphere."
            ),
            wraplength=650,
            justify="left",
        ).grid(row=9, column=0, sticky="ew", pady=(5, 0))

        actions = ttk.Frame(tab)
        actions.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        actions.columnconfigure((0, 1), weight=1)
        ttk.Button(
            actions,
            text="Save settings",
            command=lambda: self._save_settings(show_confirmation=True),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(
            actions,
            text="Restore defaults",
            command=self._restore_defaults,
        ).grid(row=0, column=1, sticky="ew", padx=(5, 0))
        ttk.Label(
            tab,
            textvariable=self.settings_status_var,
            wraplength=680,
            justify="left",
        ).grid(row=5, column=0, sticky="ew", pady=(8, 0))

    @staticmethod
    def _build_scale(
        parent: ttk.Widget,
        *,
        row: int,
        label: str,
        variable: tk.DoubleVar,
        value_variable: tk.StringVar,
        from_value: float,
        to_value: float,
        command,
    ) -> None:
        header = ttk.Frame(parent)
        header.grid(row=row, column=0, sticky="ew", pady=(7 if row else 0, 0))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=label).grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=value_variable).grid(row=0, column=1, sticky="e")
        ttk.Scale(
            parent,
            from_=from_value,
            to=to_value,
            variable=variable,
            command=command,
        ).grid(row=row + 1, column=0, sticky="ew", pady=(3, 0))

    def _night_mode_changed(self) -> None:
        apply_night_theme(self, self.night_mode_var.get())
        self.settings_status_var.set(
            "Night mode preview updated; select Save settings to use it in new windows."
        )

    def _view_setting_changed(self, _value: str | None = None) -> None:
        self._update_view_readouts()

    def _update_view_readouts(self) -> None:
        radius = float(self.sky_radius_var.get())
        if abs(radius - 180.0) < 0.6:
            radius_text = f"{radius:.0f}° (full sky)"
        elif abs(radius - 90.0) < 0.6:
            radius_text = f"{radius:.0f}° (hemisphere)"
        else:
            radius_text = f"{radius:.0f}°"
        self.sky_radius_value_var.set(radius_text)
        self.faintest_magnitude_value_var.set(
            f"{float(self.faintest_magnitude_var.get()):.1f}"
        )
        self.star_marker_scale_value_var.set(
            f"{float(self.star_marker_scale_var.get()):.2f}×"
        )

    def _time_mode_changed(self, _event=None) -> None:
        self.time_mode_var.set(
            TIME_MODE_VALUES.get(self.time_mode_display_var.get(), "random")
        )
        self._update_constraint_states()

    def _update_constraint_states(self) -> None:
        coordinate_state = (
            "normal" if self.coordinate_mode_var.get() == "fixed" else "disabled"
        )
        for widget in (self.latitude_entry, self.longitude_entry):
            widget.configure(state=coordinate_state)

        mode = self.time_mode_var.get()
        utc_state = "normal" if mode == "fixed_utc" else "disabled"
        lst_state = "normal" if mode == "fixed_lst" else "disabled"
        mjd_state = "normal" if mode == "fixed_mjd" else "disabled"
        for widget in (self.date_entry, self.time_entry):
            widget.configure(state=utc_state)
        for widget in (self.lst_date_entry, self.lst_time_entry):
            widget.configure(state=lst_state)
        self.mjd_entry.configure(state=mjd_state)

    def _collect_settings(self) -> GenerationSettings:
        defaults = self._loaded_settings
        coordinate_mode = self.coordinate_mode_var.get()
        time_mode = self.time_mode_var.get()

        try:
            latitude = float(self.latitude_var.get().strip())
            longitude = float(self.longitude_var.get().strip())
        except ValueError as error:
            if coordinate_mode == "fixed":
                raise ValueError("Latitude and longitude must be numbers.") from error
            latitude = defaults.fixed_latitude
            longitude = defaults.fixed_longitude

        try:
            fixed_datetime = datetime.strptime(
                f"{self.fixed_date_var.get().strip()} "
                f"{self.fixed_time_var.get().strip()}",
                "%Y-%m-%d %H:%M:%S",
            ).replace(tzinfo=timezone.utc)
        except ValueError as error:
            if time_mode == "fixed_utc":
                raise ValueError(
                    "Fixed UTC date/time must use YYYY-MM-DD and HH:MM:SS."
                ) from error
            fixed_datetime = defaults.fixed_datetime()

        try:
            fixed_mjd = float(self.fixed_mjd_var.get().strip())
        except ValueError as error:
            if time_mode == "fixed_mjd":
                raise ValueError("Fixed MJD must be a number.") from error
            fixed_mjd = defaults.fixed_mjd

        settings = GenerationSettings(
            include_solar_system_objects=self.include_solar_var.get(),
            coordinate_mode=coordinate_mode,
            fixed_latitude=latitude,
            fixed_longitude=longitude,
            time_mode=time_mode,
            fixed_utc_datetime=fixed_datetime.isoformat(),
            fixed_lst_date=self.fixed_lst_date_var.get().strip(),
            fixed_lst_time=self.fixed_lst_time_var.get().strip(),
            fixed_mjd=fixed_mjd,
            inverted_colors=self.inverted_colors_var.get(),
            night_mode=self.night_mode_var.get(),
            sky_radius_degrees=float(self.sky_radius_var.get()),
            faintest_visible_magnitude=float(self.faintest_magnitude_var.get()),
            star_marker_scale=float(self.star_marker_scale_var.get()),
            enable_map_rotation=self.enable_map_rotation_var.get(),
        ).validated()
        return settings

    def _save_settings(self, *, show_confirmation: bool) -> bool:
        try:
            settings = self._collect_settings()
            save_generation_settings(settings)
            self._loaded_settings = settings
        except (OSError, ValueError) as error:
            messagebox.showerror("Invalid generation settings", str(error), parent=self)
            return False
        self.settings_status_var.set("Random-sky settings saved locally.")
        if show_confirmation:
            messagebox.showinfo(
                "Settings saved",
                "New exercise processes will use these random-sky settings.",
                parent=self,
            )
        return True

    def _restore_defaults(self) -> None:
        defaults = GenerationSettings()
        fixed_time = defaults.fixed_datetime()
        self.include_solar_var.set(defaults.include_solar_system_objects)
        self.coordinate_mode_var.set(defaults.coordinate_mode)
        self.latitude_var.set(f"{defaults.fixed_latitude:.6f}")
        self.longitude_var.set(f"{defaults.fixed_longitude:.6f}")
        self.time_mode_var.set(defaults.time_mode)
        self.time_mode_display_var.set(TIME_MODE_LABELS[defaults.time_mode])
        self.fixed_date_var.set(f"{fixed_time:%Y-%m-%d}")
        self.fixed_time_var.set(f"{fixed_time:%H:%M:%S}")
        self.fixed_lst_date_var.set(defaults.fixed_lst_date)
        self.fixed_lst_time_var.set(defaults.fixed_lst_time)
        self.fixed_mjd_var.set(f"{float(defaults.fixed_mjd):.6f}")
        self.inverted_colors_var.set(defaults.inverted_colors)
        self.night_mode_var.set(False)
        self.enable_map_rotation_var.set(defaults.enable_map_rotation)
        self.sky_radius_var.set(defaults.sky_radius_degrees)
        self.faintest_magnitude_var.set(defaults.faintest_visible_magnitude)
        self.star_marker_scale_var.set(defaults.star_marker_scale)
        self._update_view_readouts()
        self._update_constraint_states()
        apply_night_theme(self, False)
        self.settings_status_var.set(
            "Defaults restored in the form; select Save settings to apply."
        )

    def _open_help(self) -> None:
        HelpWindow(self)

    def _launch_exercise(self, discovered: DiscoveredActivity) -> None:
        if not self._save_settings(show_confirmation=False):
            return
        try:
            subprocess.Popen(
                [sys.executable, str(discovered.file_path)],
                cwd=str(PROJECT_ROOT),
            )
        except OSError as error:
            messagebox.showerror("Could not launch exercise", str(error), parent=self)

    def _launch_tool(self, discovered: DiscoveredTool) -> None:
        if not self._save_settings(show_confirmation=False):
            return
        try:
            subprocess.Popen(
                [sys.executable, str(discovered.file_path)],
                cwd=str(PROJECT_ROOT),
            )
        except OSError as error:
            messagebox.showerror("Could not launch tool", str(error), parent=self)


def dependency_check(
    activities: list[DiscoveredActivity],
    tools: list[DiscoveredTool],
) -> int:
    print("Python:", sys.version.split()[0])
    print("Discovered exercises:")
    for discovered in activities:
        print(" -", discovered.instance.title, "->", discovered.file_path.name)
    print("Discovered tools:")
    for discovered in tools:
        print(" -", discovered.instance.title, "->", discovered.file_path.name)
    print("Generation settings: stored locally for the current user")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="check imports plus exercise and tool discovery without opening a window",
    )
    args = parser.parse_args()

    activities = discover_activities()
    tools = discover_tools()
    if args.check:
        return dependency_check(activities, tools)

    app = Launcher(activities, tools)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
