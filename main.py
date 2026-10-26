"""Main navigation, exercise settings, exercises, and tools for the IOAA sky trainer."""

from __future__ import annotations

import argparse
import importlib
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Type

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ioaa_trainer.activity_api import SkyActivity
from ioaa_trainer.generation_settings import GenerationSettings, load_generation_settings, save_generation_settings
from ioaa_trainer.help_ui import HelpPage
from ioaa_trainer.tool_api import SkyTool
from ioaa_trainer.theme import apply_night_theme
from ioaa_trainer.widgets import BooleanVar, SegmentedControl, ToggleSwitch

PROJECT_ROOT = Path(__file__).resolve().parent
ACTIVITIES_DIRECTORY = PROJECT_ROOT / "activities"
TOOLS_DIRECTORY = PROJECT_ROOT / "tools"

TIME_MODE_LABELS = {
    "random": "Random",
    "fixed_utc": "UTC",
    "fixed_lst": "LST + date",
    "fixed_mjd": "MJD",
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
        module = importlib.import_module(f"activities.{file_path.stem}")
        activity_class = getattr(module, "ACTIVITY_CLASS", None)
        if isinstance(activity_class, type) and issubclass(activity_class, SkyActivity):
            activities.append(DiscoveredActivity(module, activity_class, file_path))
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
        module = importlib.import_module(f"tools.{file_path.stem}")
        tool_class = getattr(module, "TOOL_CLASS", None)
        if isinstance(tool_class, type) and issubclass(tool_class, SkyTool):
            tools.append(DiscoveredTool(module, tool_class, file_path))
    tools.sort(key=lambda item: (getattr(item.instance, "sort_order", 100), item.instance.title.lower()))
    return tools


def _label(text: str, *, muted: bool = False, wrap: bool = True) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(wrap)
    if muted:
        label.setObjectName("Muted")
    return label


def _card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(7)
    return frame, layout


class Launcher(QMainWindow):
    """Focused Qt launcher for exercises, tools, and shared settings."""

    def __init__(self, activities: list[DiscoveredActivity], tools: list[DiscoveredTool]) -> None:
        super().__init__()
        self.activities = activities
        self.tools = tools
        self._loaded_settings = load_generation_settings()
        self._current_root_index = 0
        self._detail_stack: list[tuple[QWidget, str]] = []
        self.setWindowTitle("Sky Map Trainer")
        self.resize(1040, 760)
        self.setMinimumSize(760, 560)
        self._build_ui()
        self._load_settings_into_ui(self._loaded_settings)
        apply_night_theme(self, self.night_switch.isChecked())
        self._update_constraint_states()
        self._select_page(0)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("AppHeader")
        h = QHBoxLayout(header)
        h.setContentsMargins(22, 16, 22, 14)
        title_box = QVBoxLayout()
        title = QLabel("Sky Map Trainer")
        title.setObjectName("Title")
        title_box.addWidget(title)
        h.addLayout(title_box, 1)
        help_button = QPushButton("Help")
        help_button.clicked.connect(self._open_help)
        h.addWidget(help_button)
        root_layout.addWidget(header)

        body = QHBoxLayout()
        body.setContentsMargins(16, 0, 16, 16)
        body.setSpacing(14)
        root_layout.addLayout(body, 1)

        nav = QFrame()
        nav.setObjectName("Sidebar")
        nav.setFixedWidth(165)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(10, 12, 10, 12)
        nav_layout.setSpacing(4)
        self.nav_buttons: list[QPushButton] = []
        for index, text in enumerate(("Exercises", "Tools", "Settings")):
            button = QPushButton(text)
            button.setCheckable(True)
            button.setProperty("flatNav", True)
            button.clicked.connect(lambda _checked=False, i=index: self._select_page(i))
            nav_layout.addWidget(button)
            self.nav_buttons.append(button)
        nav_layout.addStretch(1)
        body.addWidget(nav)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        self.detail_nav = QFrame()
        self.detail_nav.setObjectName("ContextNav")
        detail_layout = QHBoxLayout(self.detail_nav)
        detail_layout.setContentsMargins(4, 0, 4, 0)
        detail_layout.setSpacing(10)
        self.back_button = QPushButton("← Back")
        self.back_button.setProperty("compact", True)
        self.back_button.clicked.connect(self._navigate_back)
        detail_layout.addWidget(self.back_button)
        self.breadcrumb_label = _label("", muted=True, wrap=False)
        detail_layout.addWidget(self.breadcrumb_label, 1)
        self.detail_nav.setVisible(False)
        content_layout.addWidget(self.detail_nav)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_activities_page())
        self.pages.addWidget(self._build_tools_page())
        self.pages.addWidget(self._build_settings_page())
        content_layout.addWidget(self.pages, 1)
        body.addWidget(content, 1)

    ROOT_TITLES = ("Exercises", "Tools", "Settings")
    def _select_page(self, index: int) -> None:
        """Go directly to a primary section and close any nested views."""
        self._clear_detail_stack()
        self._current_root_index = index
        self.pages.setCurrentIndex(index)
        self._update_navigation_chrome()

    def _push_detail(self, widget: QWidget, title: str) -> None:
        """Show a view inside the existing launcher instead of a new window."""
        widget.setMinimumSize(0, 0)
        widget.setParent(self.pages)
        widget.setWindowFlags(Qt.WindowType.Widget)
        self.pages.addWidget(widget)
        self._detail_stack.append((widget, title))
        self.pages.setCurrentWidget(widget)
        self._update_navigation_chrome()

    def _navigate_back(self) -> None:
        if not self._detail_stack:
            return
        widget, _title = self._detail_stack.pop()
        self._dispose_detail(widget)
        if self._detail_stack:
            self.pages.setCurrentWidget(self._detail_stack[-1][0])
        else:
            self.pages.setCurrentIndex(self._current_root_index)
        self._update_navigation_chrome()

    def _clear_detail_stack(self) -> None:
        while self._detail_stack:
            widget, _title = self._detail_stack.pop()
            self._dispose_detail(widget)

    def _dispose_detail(self, widget: QWidget) -> None:
        self.pages.removeWidget(widget)
        widget.close()
        widget.deleteLater()

    def _update_navigation_chrome(self) -> None:
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == self._current_root_index)
        if not self._detail_stack:
            self.detail_nav.setVisible(False)
            return
        breadcrumb = "  /  ".join(
            [self.ROOT_TITLES[self._current_root_index]]
            + [title for _widget, title in self._detail_stack]
        )
        self.back_button.setText("← Back")
        self.breadcrumb_label.setText(breadcrumb)
        self.detail_nav.setVisible(True)

    def _scroll_page(self, content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        return scroll

    def _build_activities_page(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)
        title = QLabel("Exercises"); title.setObjectName("PageTitle"); layout.addWidget(title)
        if not self.activities:
            layout.addWidget(_label("No exercise modules were found."))
        else:
            cards = QGridLayout()
            cards.setHorizontalSpacing(12)
            cards.setVerticalSpacing(12)
            for index, discovered in enumerate(self.activities):
                exercise = discovered.instance
                card, card_layout = _card()
                heading = QLabel(exercise.title); heading.setObjectName("SectionTitle"); heading.setWordWrap(True)
                action_row = QHBoxLayout()
                action_row.addWidget(heading, 1)
                open_button = QPushButton("Start")
                open_button.setProperty("primary", True)
                open_button.clicked.connect(lambda _checked=False, d=discovered: self._launch_exercise(d))
                action_row.addWidget(open_button)
                card_layout.addLayout(action_row)
                cards.addWidget(card, index // 2, index % 2)
            cards.setColumnStretch(0, 1)
            cards.setColumnStretch(1, 1)
            layout.addLayout(cards)
        layout.addStretch(1)
        return self._scroll_page(content)

    def _build_tools_page(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)
        title = QLabel("Tools"); title.setObjectName("PageTitle"); layout.addWidget(title)
        cards = QGridLayout()
        cards.setHorizontalSpacing(12)
        cards.setVerticalSpacing(12)
        for index, discovered in enumerate(self.tools):
            tool = discovered.instance
            card, card_layout = _card()
            heading = QLabel(tool.title); heading.setObjectName("SectionTitle")
            row = QHBoxLayout(); row.addWidget(heading, 1)
            button = QPushButton("Open")
            button.setProperty("primary", True)
            button.clicked.connect(lambda _checked=False, d=discovered: self._launch_tool(d))
            row.addWidget(button)
            card_layout.addLayout(row)
            cards.addWidget(card, 0, index)
            cards.setColumnStretch(index, 1)
        layout.addLayout(cards)
        if not self.tools:
            layout.addWidget(_label("No tool modules were found."))
        layout.addStretch(1)
        return self._scroll_page(content)

    def _build_settings_page(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)
        title = QLabel("Settings"); title.setObjectName("PageTitle"); layout.addWidget(title)
        coordinates = QGroupBox("Location")
        cg = QGridLayout(coordinates)
        self.coordinate_mode_selector = SegmentedControl(
            (("random", "Random"), ("fixed", "Fixed")),
            value="random",
        )
        self.coordinate_mode_selector.valueChanged.connect(lambda _value: self._update_constraint_states())
        cg.addWidget(self.coordinate_mode_selector, 0, 0, 1, 2)
        self.latitude_label = QLabel("Latitude (°)"); cg.addWidget(self.latitude_label, 1, 0); self.latitude_entry = QLineEdit(); cg.addWidget(self.latitude_entry, 1, 1)
        self.longitude_label = QLabel("Longitude (°)"); cg.addWidget(self.longitude_label, 2, 0); self.longitude_entry = QLineEdit(); cg.addWidget(self.longitude_entry, 2, 1)
        cg.setColumnStretch(1, 1)
        layout.addWidget(coordinates)

        time_group = QGroupBox("Time")
        tg = QGridLayout(time_group)
        tg.addWidget(QLabel("Mode"), 0, 0)
        self.time_mode_combo = QComboBox(); self.time_mode_combo.addItems(TIME_MODE_LABELS.values()); self.time_mode_combo.currentTextChanged.connect(self._update_constraint_states)
        tg.addWidget(self.time_mode_combo, 0, 1)
        self.time_note = _label("", muted=True); tg.addWidget(self.time_note, 1, 0, 1, 2)
        self.date_label = QLabel("UTC date"); tg.addWidget(self.date_label, 2, 0); self.date_entry = QLineEdit(); self.date_entry.setPlaceholderText("YYYY-MM-DD"); tg.addWidget(self.date_entry, 2, 1)
        self.time_label = QLabel("UTC time"); tg.addWidget(self.time_label, 3, 0); self.time_entry = QLineEdit(); self.time_entry.setPlaceholderText("HH:MM:SS"); tg.addWidget(self.time_entry, 3, 1)
        self.lst_date_label = QLabel("Date"); tg.addWidget(self.lst_date_label, 4, 0); self.lst_date_entry = QLineEdit(); self.lst_date_entry.setPlaceholderText("YYYY-MM-DD"); tg.addWidget(self.lst_date_entry, 4, 1)
        self.lst_time_label = QLabel("LST"); tg.addWidget(self.lst_time_label, 5, 0); self.lst_time_entry = QLineEdit(); self.lst_time_entry.setPlaceholderText("HH:MM:SS or hours"); tg.addWidget(self.lst_time_entry, 5, 1)
        self.mjd_label = QLabel("MJD"); tg.addWidget(self.mjd_label, 6, 0); self.mjd_entry = QLineEdit(); tg.addWidget(self.mjd_entry, 6, 1)
        tg.setColumnStretch(1, 1)
        layout.addWidget(time_group)

        view = QGroupBox("Display")
        vl = QVBoxLayout(view)
        self.include_solar_var = BooleanVar(False)
        self.include_solar_switch = ToggleSwitch(text="Sun, Moon and planets", variable=self.include_solar_var)
        vl.addWidget(self.include_solar_switch)
        self.inverted_var = BooleanVar(False); vl.addWidget(ToggleSwitch(text="Invert colours", variable=self.inverted_var))
        self.night_var = BooleanVar(False); self.night_switch = ToggleSwitch(text="Night mode", variable=self.night_var, command=self._night_mode_changed); vl.addWidget(self.night_switch)
        self.rotation_var = BooleanVar(True); vl.addWidget(ToggleSwitch(text="Random rotation", variable=self.rotation_var))
        self.sky_radius_slider, self.sky_radius_value = self._slider_row(vl, "Coverage", 0, 1800, 10)
        self.magnitude_slider, self.magnitude_value = self._slider_row(vl, "Magnitude limit", -15, 80, 10)
        self.marker_slider, self.marker_value = self._slider_row(vl, "Star size", 45, 200, 100)
        layout.addWidget(view)

        actions = QHBoxLayout()
        save = QPushButton("Save"); save.setProperty("primary", True); save.clicked.connect(lambda: self._save_settings(show_confirmation=True))
        defaults = QPushButton("Reset"); defaults.clicked.connect(self._restore_defaults)
        actions.addWidget(save); actions.addWidget(defaults); actions.addStretch(1)
        layout.addLayout(actions)
        self.settings_status = QLabel(""); self.settings_status.setObjectName("Status"); self.settings_status.setWordWrap(True); self.settings_status.setVisible(False); layout.addWidget(self.settings_status)
        layout.addStretch(1)
        return self._scroll_page(content)

    def _slider_row(self, parent: QVBoxLayout, text: str, minimum: int, maximum: int, divisor: int) -> tuple[QSlider, QLabel]:
        header = QHBoxLayout(); header.addWidget(QLabel(text)); header.addStretch(1); value = QLabel(); value.setObjectName("Muted"); header.addWidget(value); parent.addLayout(header)
        slider = QSlider(Qt.Orientation.Horizontal); slider.setRange(minimum, maximum); slider.setProperty("divisor", divisor); parent.addWidget(slider)
        slider.valueChanged.connect(self._update_view_readouts)
        return slider, value

    def _load_settings_into_ui(self, settings: GenerationSettings) -> None:
        fixed = settings.fixed_datetime()
        self.include_solar_var.set(settings.include_solar_system_objects)
        self.coordinate_mode_selector.set_value(settings.coordinate_mode if settings.coordinate_mode in {"random", "fixed"} else "random")
        self.latitude_entry.setText(f"{settings.fixed_latitude:.6f}")
        self.longitude_entry.setText(f"{settings.fixed_longitude:.6f}")
        self.time_mode_combo.setCurrentText(TIME_MODE_LABELS.get(settings.time_mode, TIME_MODE_LABELS["random"]))
        self.date_entry.setText(f"{fixed:%Y-%m-%d}"); self.time_entry.setText(f"{fixed:%H:%M:%S}")
        self.lst_date_entry.setText(settings.fixed_lst_date); self.lst_time_entry.setText(settings.fixed_lst_time); self.mjd_entry.setText(f"{settings.fixed_mjd:.6f}")
        self.inverted_var.set(settings.inverted_colors); self.night_var.set(settings.night_mode); self.rotation_var.set(settings.enable_map_rotation)
        self.sky_radius_slider.setValue(round(settings.sky_radius_degrees * 10)); self.magnitude_slider.setValue(round(settings.faintest_visible_magnitude * 10)); self.marker_slider.setValue(round(settings.star_marker_scale * 100))
        self._update_view_readouts()

    def _update_view_readouts(self) -> None:
        radius = self.sky_radius_slider.value() / 10.0
        suffix = " (full sky)" if abs(radius-180)<0.6 else (" (hemisphere)" if abs(radius-90)<0.6 else "")
        self.sky_radius_value.setText(f"{radius:.0f}°{suffix}")
        self.magnitude_value.setText(f"{self.magnitude_slider.value()/10:.1f}")
        self.marker_value.setText(f"{self.marker_slider.value()/100:.2f}×")

    def _night_mode_changed(self) -> None:
        apply_night_theme(self, self.night_var.get())
        self.settings_status.setText("Preview only — save to keep.")
        self.settings_status.setVisible(True)

    def _update_constraint_states(self) -> None:
        fixed = self.coordinate_mode_selector.value() == "fixed"
        for widget in (self.latitude_label, self.latitude_entry, self.longitude_label, self.longitude_entry):
            widget.setVisible(fixed)
        mode = TIME_MODE_VALUES.get(self.time_mode_combo.currentText(), "random")
        self.time_note.setVisible(False)
        groups = (
            ((self.date_label, self.date_entry, self.time_label, self.time_entry), mode == "fixed_utc"),
            ((self.lst_date_label, self.lst_date_entry, self.lst_time_label, self.lst_time_entry), mode == "fixed_lst"),
            ((self.mjd_label, self.mjd_entry), mode == "fixed_mjd"),
        )
        for widgets, visible in groups:
            for widget in widgets:
                widget.setVisible(visible)

    def _collect_settings(self) -> GenerationSettings:
        defaults = self._loaded_settings
        coordinate_mode = self.coordinate_mode_selector.value()
        time_mode = TIME_MODE_VALUES.get(self.time_mode_combo.currentText(), "random")
        try:
            latitude = float(self.latitude_entry.text().strip()); longitude = float(self.longitude_entry.text().strip())
        except ValueError as error:
            if coordinate_mode == "fixed": raise ValueError("Latitude and longitude must be numbers.") from error
            latitude, longitude = defaults.fixed_latitude, defaults.fixed_longitude
        try:
            fixed_datetime = datetime.strptime(f"{self.date_entry.text().strip()} {self.time_entry.text().strip()}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError as error:
            if time_mode == "fixed_utc": raise ValueError("Fixed UTC date/time must use YYYY-MM-DD and HH:MM:SS.") from error
            fixed_datetime = defaults.fixed_datetime()
        try:
            fixed_mjd = float(self.mjd_entry.text().strip())
        except ValueError as error:
            if time_mode == "fixed_mjd": raise ValueError("Fixed MJD must be a number.") from error
            fixed_mjd = defaults.fixed_mjd
        return GenerationSettings(
            include_solar_system_objects=self.include_solar_var.get(), coordinate_mode=coordinate_mode,
            fixed_latitude=latitude, fixed_longitude=longitude, time_mode=time_mode,
            fixed_utc_datetime=fixed_datetime.isoformat(), fixed_lst_date=self.lst_date_entry.text().strip(),
            fixed_lst_time=self.lst_time_entry.text().strip(), fixed_mjd=fixed_mjd,
            inverted_colors=self.inverted_var.get(), night_mode=self.night_var.get(),
            sky_radius_degrees=self.sky_radius_slider.value()/10.0,
            faintest_visible_magnitude=self.magnitude_slider.value()/10.0,
            star_marker_scale=self.marker_slider.value()/100.0,
            enable_map_rotation=self.rotation_var.get(),
        ).validated()

    def _save_settings(self, *, show_confirmation: bool) -> bool:
        try:
            settings = self._collect_settings(); save_generation_settings(settings); self._loaded_settings = settings
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Invalid generation settings", str(error)); return False
        self.settings_status.setText("Saved.")
        self.settings_status.setVisible(True)
        if show_confirmation:
            QMessageBox.information(self, "Saved", "Settings saved.")
        return True

    def _restore_defaults(self) -> None:
        self._load_settings_into_ui(GenerationSettings())
        apply_night_theme(self, self.night_var.get())
        self._update_constraint_states()
        self.settings_status.setText("Defaults restored — save to keep.")
        self.settings_status.setVisible(True)

    def _open_help(self) -> None:
        if self._detail_stack and self._detail_stack[-1][1] == "Help & About":
            return
        self._push_detail(HelpPage(self), "Help & About")

    def _launch_exercise(self, discovered: DiscoveredActivity) -> None:
        if not self._save_settings(show_confirmation=False):
            return
        try:
            from ioaa_trainer.activity_ui import ActivityApplication

            exercise = discovered.instance
            view = ActivityApplication(exercise, analysis_navigator=self._open_analysis)
        except Exception as error:
            QMessageBox.critical(self, "Could not open exercise", f"{type(error).__name__}: {error}")
            return
        self._push_detail(view, exercise.title)

    def _open_analysis(self, bundle, activity: SkyActivity) -> None:
        try:
            from ioaa_trainer.analysis_ui import AnalysisWindow

            parent = self._detail_stack[-1][0] if self._detail_stack else self
            view = AnalysisWindow(parent, bundle, activity, back_callback=self._navigate_back)
        except Exception as error:
            QMessageBox.critical(self, "Could not open sky analysis", f"{type(error).__name__}: {error}")
            return
        self._push_detail(view, "Sky analysis")

    def _launch_tool(self, discovered: DiscoveredTool) -> None:
        if not self._save_settings(show_confirmation=False):
            return
        factory = getattr(discovered.module, "create_widget", None)
        if not callable(factory):
            QMessageBox.critical(
                self,
                "Tool cannot open in the app",
                f"{discovered.instance.title} does not provide an embeddable Qt view.",
            )
            return
        try:
            view = factory()
        except Exception as error:
            QMessageBox.critical(self, "Could not open tool", f"{type(error).__name__}: {error}")
            return
        self._push_detail(view, discovered.instance.title)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._clear_detail_stack()
        event.accept()


def dependency_check(activities: list[DiscoveredActivity], tools: list[DiscoveredTool]) -> int:
    print("Python:", sys.version.split()[0])
    print("UI: PyQt6")
    print("Discovered exercises:")
    for discovered in activities: print(" -", discovered.instance.title, "->", discovered.file_path.name)
    print("Discovered tools:")
    for discovered in tools: print(" -", discovered.instance.title, "->", discovered.file_path.name)
    print("Generation settings: stored locally for the current user")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check imports plus exercise and tool discovery without opening a window")
    args = parser.parse_args()
    activities = discover_activities(); tools = discover_tools()
    if args.check: return dependency_check(activities, tools)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Sky Map Trainer")
    window = Launcher(activities, tools); window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
