"""Full-featured PyQt6 sky-analysis view for the current exercise sky."""

from __future__ import annotations

from zoneinfo import ZoneInfo
from typing import Callable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QSlider, QSizePolicy, QVBoxLayout, QWidget,
)

from .activity_api import SkyActivity
from .astronomy import format_local_sidereal_time
from .models import QuestionBundle
from .rendering import RenderOptions, SkyMapRenderer
from .theme import apply_night_theme, night_mode_enabled
from .widgets import BooleanVar, ToggleSwitch


class AnalysisWindow(QWidget):
    """Inspect the current question with independently toggleable layers."""

    def __init__(
        self,
        parent: QWidget | None,
        bundle: QuestionBundle,
        activity: SkyActivity,
        *,
        back_callback: Callable[[], None] | None = None,
        night_mode: bool | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.bundle = bundle
        self.activity = activity
        self._back_callback = back_callback
        self.night_mode = night_mode_enabled(parent) if night_mode is None else bool(night_mode)
        self.setWindowTitle(f"Analysis — {activity.title}")
        self.resize(1280, 820)
        self.setMinimumSize(920, 620)
        self._build_variables()
        self._build_ui()
        apply_night_theme(self, self.night_mode)
        self._redraw()

    def _build_variables(self) -> None:
        settings = self.bundle.model.settings
        self.layer_vars = {
            "direction": BooleanVar(False), "altgrid": BooleanVar(False), "coordgrid": BooleanVar(False),
            "ecliptic": BooleanVar(False), "equator": BooleanVar(False), "galactic": BooleanVar(False),
            "const_lines": BooleanVar(False), "const_names": BooleanVar(False), "star_names": BooleanVar(False),
            "answer": BooleanVar(False),
            "solar": BooleanVar(settings.include_solar_system_objects),
            "solar_labels": BooleanVar(False),
            "zenith": BooleanVar(False), "title": BooleanVar(False),
        }
        self.magnitude = settings.limiting_magnitude

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame); scroll.setFixedWidth(285)
        controls = QWidget(); scroll.setWidget(controls)
        cl = QVBoxLayout(controls); cl.setContentsMargins(2,2,8,2); cl.setSpacing(10)

        heading = QLabel("Analysis"); heading.setObjectName("PageTitle"); cl.addWidget(heading)
        prompt = QGroupBox("Question")
        pl = QVBoxLayout(prompt)
        p = QLabel(self.bundle.question.prompt); p.setWordWrap(True); p.setObjectName("QuestionText"); pl.addWidget(p)
        cl.addWidget(prompt)

        answer = QGroupBox("Answer")
        al = QVBoxLayout(answer)
        a = QLabel(self.bundle.question.answer_text); a.setWordWrap(True); al.addWidget(a)
        cl.addWidget(answer)

        layers = QGroupBox("Layers"); ll = QVBoxLayout(layers); ll.setSpacing(5)
        items = [
            ("Directions", "direction"), ("Alt/Az grid", "altgrid"),
            ("RA/Dec grid", "coordgrid"), ("Ecliptic", "ecliptic"),
            ("Celestial equator", "equator"), ("Galactic equator", "galactic"),
            ("Constellations", "const_lines"), ("Constellation names", "const_names"),
            ("Star names", "star_names"), ("Solar system", "solar"),
            ("Solar labels", "solar_labels"), ("Zenith", "zenith"),
            ("Answer", "answer"), ("Details", "title"),
        ]
        for label, key in items:
            ll.addWidget(ToggleSwitch(text=label, variable=self.layer_vars[key], command=self._redraw))
        cl.addWidget(layers)

        stars = QGroupBox("Stars"); sl = QVBoxLayout(stars)
        row = QHBoxLayout(); row.addWidget(QLabel("Magnitude limit")); row.addStretch(1)
        self.mag_value = QLabel(f"{self.magnitude:.1f}"); self.mag_value.setObjectName("Muted"); row.addWidget(self.mag_value); sl.addLayout(row)
        self.mag_slider = QSlider(Qt.Orientation.Horizontal); self.mag_slider.setRange(-15, round(self.bundle.model.settings.limiting_magnitude*10)); self.mag_slider.setValue(round(self.magnitude*10)); self.mag_slider.valueChanged.connect(self._magnitude_changed); sl.addWidget(self.mag_slider)
        cl.addWidget(stars)

        metadata = QGroupBox("Revealed sky"); ml = QVBoxLayout(metadata)
        settings = self.bundle.model.settings; utc = settings.observation_datetime.astimezone(ZoneInfo("UTC"))
        text = (
            f"Latitude: {settings.latitude:.5f}°\nLongitude: {settings.longitude:.5f}°\n"
            f"UTC: {utc:%Y-%m-%d %H:%M:%S}\nLST: {format_local_sidereal_time(settings)}\n"
            f"Rotation: {settings.map_rotation_degrees:.1f}°\nSeed: {self.bundle.seed}"
        )
        ml.addWidget(QLabel(text)); cl.addWidget(metadata)

        buttons = QHBoxLayout()
        save = QPushButton("Save PNG…")
        save.clicked.connect(self._save_png)
        buttons.addWidget(save)
        if self._back_callback is None:
            close = QPushButton("Close")
            close.clicked.connect(self.close)
            buttons.addWidget(close)
        buttons.addStretch(1)
        cl.addLayout(buttons)
        self.status = QLabel(""); self.status.setObjectName("Status"); self.status.setWordWrap(True); self.status.setVisible(False); cl.addWidget(self.status)
        cl.addStretch(1)
        root.addWidget(scroll)

        chart_card = QFrame(); chart_card.setObjectName("Card"); chart_layout = QVBoxLayout(chart_card); chart_layout.setContentsMargins(8,8,8,8); chart_layout.setSpacing(4)
        self.figure = Figure(figsize=(8.5, 7.5), dpi=100)
        self.renderer = SkyMapRenderer(self.figure); self.renderer.set_night_mode(self.night_mode)
        self.canvas = FigureCanvasQTAgg(self.figure); self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        chart_layout.addWidget(self.canvas, 1)
        toolbar = NavigationToolbar2QT(self.canvas, self)
        if self.night_mode:
            toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        chart_layout.addWidget(toolbar)
        root.addWidget(chart_card, 1)

    def _render_options(self) -> RenderOptions:
        v = self.layer_vars
        return RenderOptions(
            show_direction_labels=v["direction"].get(), show_altitude_grid=v["altgrid"].get(),
            show_title=v["title"].get(), show_ecliptic=v["ecliptic"].get(),
            show_celestial_equator=v["equator"].get(), show_galactic_equator=v["galactic"].get(),
            show_constellation_names=v["const_names"].get(), show_constellation_lines=v["const_lines"].get(),
            show_star_names=v["star_names"].get(), show_coordinate_grid=v["coordgrid"].get(),
            show_solar_system_objects=v["solar"].get(), show_solar_system_labels=v["solar_labels"].get(),
            show_zenith_label=v["zenith"].get(), limiting_magnitude=self.magnitude,
        )

    def _magnitude_changed(self, value: int) -> None:
        self.magnitude = value / 10.0; self.mag_value.setText(f"{self.magnitude:.1f}"); self._redraw()

    def _redraw(self) -> None:
        if not hasattr(self, "renderer"): return
        def overlay(renderer: SkyMapRenderer, model) -> None:
            if self.layer_vars["answer"].get(): self.activity.draw_answer(renderer, model, self.bundle.question)
        self.renderer.draw(self.bundle.model, self._render_options(), answer_overlay=overlay)
        self.canvas.draw_idle()

    def _save_png(self) -> None:
        utc = self.bundle.model.settings.observation_datetime.astimezone(ZoneInfo("UTC"))
        filename, _ = QFileDialog.getSaveFileName(self, "Save analysed sky map", f"sky_analysis_{utc:%Y%m%d_%H%M%S}.png", "PNG image (*.png);;All files (*)")
        if not filename: return
        if not filename.lower().endswith(".png"): filename += ".png"
        try:
            self.figure.savefig(filename, dpi=220, bbox_inches="tight", facecolor=self.figure.get_facecolor())
            self.status.setText(f"Saved {filename}")
            self.status.setVisible(True)
        except OSError as error:
            QMessageBox.critical(self, "Could not save image", str(error))
