"""Standalone, fully configurable PyQt6 sky-map generator UI."""

from __future__ import annotations

import math
import queue
import random
import sys

import numpy as np
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtCore import QEvent, QSize, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QSlider, QTabWidget, QVBoxLayout, QWidget,
)

from .astronomy import AstronomyData, SkyMapCalculator, format_local_sidereal_time
from .coordinate_converter import equatorial_from_horizontal, ra_from_lst_hour_angle
from .generation_settings import load_generation_settings
from .local_time import local_to_utc, zone_for_coordinates
from .models import MapSettings, SkyMapModel
from .rendering import RenderOptions, SkyMapRenderer
from .theme import apply_night_theme
from .time_utils import (
    datetime_for_local_sidereal_time, datetime_from_mjd, format_clock_hours,
    local_sidereal_time_hours, mjd_from_datetime, parse_clock_hours,
)
from .widgets import (
    BooleanVar, CelestialSphereSelector, DoubleVar, SegmentedControl, StringVar, ToggleSwitch, bind_line_edit,
)
from .world_map_picker import ExpandedWorldMap, WorldMapPicker


class InteractiveSkyCanvas(FigureCanvasQTAgg):
    """QtAgg canvas with smooth wheel/trackpad zoom independent of toolbar mode."""

    zoomRequested = pyqtSignal(float)

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt API
        angle_y = event.angleDelta().y()
        pixel_y = event.pixelDelta().y()
        if angle_y:
            steps = float(angle_y) / 120.0
        elif pixel_y:
            # Precision touchpads report small pixel deltas rather than wheel
            # notches.  Keep those values continuous for genuinely smooth zoom.
            steps = float(pixel_y) / 80.0
        else:
            super().wheelEvent(event)
            return
        self.zoomRequested.emit(steps)
        event.accept()

    def event(self, event) -> bool:
        # macOS trackpads can deliver pinch-to-zoom as a native gesture rather
        # than a wheel event.  Supporting both paths makes the map feel native
        # across touchpads and conventional mice.
        if event.type() == QEvent.Type.NativeGesture:
            try:
                if event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
                    self.zoomRequested.emit(float(event.value()) * 5.0)
                    event.accept()
                    return True
            except (AttributeError, TypeError):
                pass
        return super().event(event)


class CompactNavigationToolbar(NavigationToolbar2QT):
    """Small map toolbar containing only useful navigation controls."""

    toolitems = (
        ("Home", "Reset the chart view", "home", "home"),
        ("Back", "Back to previous chart view", "back", "back"),
        ("Forward", "Forward to next chart view", "forward", "forward"),
        (None, None, None, None),
        ("Pan", "Pan using the Matplotlib navigation mode", "move", "pan"),
        ("Zoom", "Zoom to a rectangle", "zoom_to_rect", "zoom"),
    )

    def __init__(self, canvas, parent=None) -> None:
        super().__init__(canvas, parent)
        self.setObjectName("MapToolbar")
        self.setIconSize(QSize(16, 16))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setMovable(False)
        self.setFloatable(False)
        self.setFixedHeight(30)
        layout = self.layout()
        if layout is not None:
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(1)


class SkyMapGeneratorApplication(QWidget):
    """Generate an analytical sky chart from an observer or a chosen zenith."""

    CALCULATION_MAGNITUDE_LIMIT = 8.0
    MAXIMUM_SKY_RADIUS = 180.0

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sky Map Generator")
        self.resize(1320, 860); self.setMinimumSize(980, 680)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ioaa-map-generator")
        self._calculator = SkyMapCalculator(AstronomyData())
        self._progress_messages: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._generation = 0; self._model: SkyMapModel | None = None; self._source_description = "Observer location + time"
        self._current_future: Future[SkyMapModel] | None = None; self._future_generation = 0
        self._map_drag_state: dict[str, float | bool] | None = None
        self._model_zenith_ra: float | None = None
        self._model_zenith_dec: float | None = None
        self._zenith_preview_target: tuple[float, float] | None = None
        self._zenith_preview_background = None
        self._zenith_preview_bbox: tuple[float, float, float, float] | None = None
        self._zenith_preview_active = False
        self._build_variables(); self._build_ui(); apply_night_theme(self, self.night_mode)
        self._update_zenith_readouts(sync_inputs=True)
        self._update_observation_states(); self._update_rotation_state(); self._install_live_updates()
        self._debounce = QTimer(self); self._debounce.setSingleShot(True); self._debounce.timeout.connect(lambda: self.generate_map(show_errors=False))
        self._poll_timer = QTimer(self); self._poll_timer.setInterval(80); self._poll_timer.timeout.connect(self._poll_future)
        self._preview_timer = QTimer(self); self._preview_timer.setSingleShot(True); self._preview_timer.setInterval(16); self._preview_timer.timeout.connect(self._draw_zenith_preview)
        self._zoom_pending_radius: float | None = None
        self._zoom_timer = QTimer(self); self._zoom_timer.setSingleShot(True); self._zoom_timer.setInterval(36); self._zoom_timer.timeout.connect(self._apply_pending_sky_map_zoom)
        QTimer.singleShot(180, lambda: self._schedule_recalculation(delay_ms=0))

    def _build_variables(self) -> None:
        saved = load_generation_settings(); self.night_mode = saved.night_mode
        latitude, longitude = saved.fixed_latitude, saved.fixed_longitude
        now = datetime.now(timezone.utc).replace(microsecond=0)
        observation = (
            saved.resolved_datetime(longitude)
            if saved.time_mode != "random"
            else now
        )
        self.position_mode_var = StringVar("observer"); self.latitude_var = StringVar(f"{latitude:.6f}"); self.longitude_var = StringVar(f"{longitude:.6f}")
        self.time_input_var = StringVar("UTC date/time"); self.date_var = StringVar(f"{observation:%Y-%m-%d}"); self.time_var = StringVar(f"{observation:%H:%M:%S}")
        self.lst_date_var = StringVar(f"{observation:%Y-%m-%d}"); self.lst_time_var = StringVar(format_clock_hours(local_sidereal_time_hours(observation, longitude))); self.mjd_var = StringVar(f"{mjd_from_datetime(observation):.6f}")
        self.zenith_ra_var = DoubleVar(local_sidereal_time_hours(observation, longitude)); self.zenith_dec_var = DoubleVar(latitude); self.zenith_date_var = StringVar(f"{observation:%Y-%m-%d}")
        self.zenith_ra_input_var = StringVar(); self.zenith_dec_input_var = StringVar()
        self.direction_labels_var=BooleanVar(False); self.altitude_grid_var=BooleanVar(False); self.coordinate_grid_var=BooleanVar(False); self.ecliptic_var=BooleanVar(False); self.celestial_equator_var=BooleanVar(False); self.galactic_equator_var=BooleanVar(False)
        self.constellation_lines_var=BooleanVar(False); self.constellation_names_var=BooleanVar(False); self.star_names_var=BooleanVar(False); self.solar_system_objects_var=BooleanVar(saved.include_solar_system_objects); self.solar_system_labels_var=BooleanVar(False); self.zenith_label_var=BooleanVar(False); self.title_var=BooleanVar(False)
        self.inverted_colors_var=BooleanVar(saved.inverted_colors); self.sky_radius_var=DoubleVar(saved.sky_radius_degrees); self.magnitude_var=DoubleVar(saved.faintest_visible_magnitude); self.marker_scale_var=DoubleVar(saved.star_marker_scale); self.rotation_enabled_var=BooleanVar(False); self.rotation_var=DoubleVar(0.0)
        self._update_zenith_input_values()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self); layout.setContentsMargins(12,12,12,12); layout.setSpacing(12)
        controls = QFrame(); controls.setObjectName("Card"); controls.setFixedWidth(350); cl = QVBoxLayout(controls); cl.setContentsMargins(14,14,14,14); cl.setSpacing(10)
        title = QLabel("Sky Map Generator"); title.setObjectName("PageTitle"); cl.addWidget(title)
        self.tabs = QTabWidget(); cl.addWidget(self.tabs,1)
        self.tabs.addTab(self._build_observation_tab(), "Observation"); self.tabs.addTab(self._build_layers_tab(), "Layers"); self.tabs.addTab(self._build_view_tab(), "View")
        action_row=QHBoxLayout(); action_row.addStretch(1); self.save_button=QPushButton("Save PNG…"); self.save_button.setEnabled(False); self.save_button.clicked.connect(self._save_png); action_row.addWidget(self.save_button); cl.addLayout(action_row)
        self.status_label=QLabel("Preparing sky map…"); self.status_label.setObjectName("Status"); self.status_label.setWordWrap(True); cl.addWidget(self.status_label)
        layout.addWidget(controls)

        chart=QFrame(); chart.setObjectName("Card"); ql=QVBoxLayout(chart); ql.setContentsMargins(8,8,8,8); ql.setSpacing(4)
        self.figure=Figure(figsize=(8.7,7.6),dpi=100); self.renderer=SkyMapRenderer(self.figure); self.renderer.set_night_mode(self.night_mode); self.canvas=InteractiveSkyCanvas(self.figure); self.canvas.zoomRequested.connect(self._sky_map_zoom); ql.addWidget(self.canvas,1)
        self.canvas.mpl_connect("button_press_event", self._sky_map_press)
        self.canvas.mpl_connect("motion_notify_event", self._sky_map_move)
        self.canvas.mpl_connect("button_release_event", self._sky_map_release)
        toolbar=CompactNavigationToolbar(self.canvas,self)
        if self.night_mode: toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        ql.addWidget(toolbar, 0, Qt.AlignmentFlag.AlignLeft)
        self.figure.set_facecolor(self.renderer.BACKGROUND); self.renderer.axes.set_facecolor(self.renderer.BACKGROUND); self.renderer.axes.set_axis_off(); self.canvas.draw_idle(); layout.addWidget(chart,1)

    def _scroll_wrap(self, body: QWidget) -> QScrollArea:
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame); scroll.setWidget(body); return scroll

    def _build_observation_tab(self) -> QWidget:
        body=QWidget(); l=QVBoxLayout(body); l.setContentsMargins(8,8,8,8); l.setSpacing(10)
        mode=QGroupBox("Position")
        ml=QVBoxLayout(mode)
        self.position_selector=SegmentedControl(
            (("observer","Observer + time"),("zenith","Direct zenith")),
            value="observer",
        )
        self.position_selector.valueChanged.connect(self._position_mode_changed)
        ml.addWidget(self.position_selector)
        l.addWidget(mode)
        observer=QGroupBox("Observer"); self.observer_group=observer; og=QGridLayout(observer); og.addWidget(QLabel("Latitude"),0,0); self.latitude_entry=bind_line_edit(QLineEdit(),self.latitude_var); og.addWidget(self.latitude_entry,0,1); og.addWidget(QLabel("Longitude"),1,0); self.longitude_entry=bind_line_edit(QLineEdit(),self.longitude_var); og.addWidget(self.longitude_entry,1,1)
        og.addWidget(QLabel("Time"),2,0); self.time_input_combo=QComboBox(); self.time_input_combo.addItems(("UTC date/time","Local date/time","LST + UTC date","MJD")); self.time_input_combo.currentTextChanged.connect(self._time_input_changed); og.addWidget(self.time_input_combo,2,1)
        self.utc_date_label=QLabel("UTC date"); og.addWidget(self.utc_date_label,3,0); self.utc_date_entry=bind_line_edit(QLineEdit(),self.date_var); og.addWidget(self.utc_date_entry,3,1); self.utc_time_label=QLabel("UTC time"); og.addWidget(self.utc_time_label,4,0); self.utc_time_entry=bind_line_edit(QLineEdit(),self.time_var); og.addWidget(self.utc_time_entry,4,1)
        self.lst_date_label=QLabel("Date"); og.addWidget(self.lst_date_label,5,0); self.lst_date_entry=bind_line_edit(QLineEdit(),self.lst_date_var); og.addWidget(self.lst_date_entry,5,1); self.lst_time_label=QLabel("LST"); og.addWidget(self.lst_time_label,6,0); self.lst_time_entry=bind_line_edit(QLineEdit(),self.lst_time_var); og.addWidget(self.lst_time_entry,6,1)
        self.mjd_label=QLabel("MJD"); og.addWidget(self.mjd_label,7,0); self.mjd_entry=bind_line_edit(QLineEdit(),self.mjd_var); og.addWidget(self.mjd_entry,7,1); og.setColumnStretch(1,1); l.addWidget(observer)

        self.location_group = QGroupBox("Pick location")
        location_layout = QVBoxLayout(self.location_group)
        self.world_map = WorldMapPicker()
        self.world_map.set_coordinates(float(self.latitude_var.get()), float(self.longitude_var.get()))
        self.world_map.coordinateSelected.connect(self._map_location_selected)
        location_layout.addWidget(self.world_map)
        expand = QPushButton("Expand map")
        expand.clicked.connect(self._expand_world_map)
        location_layout.addWidget(expand)
        self.zone_label = QLabel("")
        self.zone_label.setObjectName("Muted")
        location_layout.addWidget(self.zone_label)
        l.addWidget(self.location_group)
        self._sync_location()

        zenith=QGroupBox("Zenith"); self.zenith_group=zenith; zl=QVBoxLayout(zenith)
        self.zenith_selector=CelestialSphereSelector(ra_variable=self.zenith_ra_var,dec_variable=self.zenith_dec_var,sky_radius_variable=self.sky_radius_var,command=self._zenith_selector_moved,release_command=self._zenith_selector_released,height=235); zl.addWidget(self.zenith_selector)
        zr=QHBoxLayout(); self.zenith_ra_label=QLabel(); self.zenith_dec_label=QLabel(); zr.addWidget(self.zenith_ra_label); zr.addStretch(1); zr.addWidget(self.zenith_dec_label); zl.addLayout(zr)
        manual=QGroupBox("Exact position"); mg=QGridLayout(manual); mg.addWidget(QLabel("RA"),0,0); self.zenith_ra_entry=bind_line_edit(QLineEdit(),self.zenith_ra_input_var); mg.addWidget(self.zenith_ra_entry,0,1); mg.addWidget(QLabel("Dec"),1,0); self.zenith_dec_entry=bind_line_edit(QLineEdit(),self.zenith_dec_input_var); mg.addWidget(self.zenith_dec_entry,1,1); self.apply_zenith_button=QPushButton("Apply"); self.apply_zenith_button.clicked.connect(self._apply_manual_zenith); mg.addWidget(self.apply_zenith_button,2,0,1,2); self.zenith_ra_entry.returnPressed.connect(self._apply_manual_zenith); self.zenith_dec_entry.returnPressed.connect(self._apply_manual_zenith); zl.addWidget(manual)
        date_row=QHBoxLayout(); date_row.addWidget(QLabel("UTC date")); self.zenith_date_entry=bind_line_edit(QLineEdit(),self.zenith_date_var); date_row.addWidget(self.zenith_date_entry,1); zl.addLayout(date_row); l.addWidget(zenith)
        metadata=QGroupBox("Details"); m=QVBoxLayout(metadata); self.metadata_label=QLabel("Waiting…"); self.metadata_label.setWordWrap(True); m.addWidget(self.metadata_label); l.addWidget(metadata); l.addStretch(1)
        self._observer_inputs=(self.latitude_entry,self.longitude_entry,self.time_input_combo,self.utc_date_entry,self.utc_time_entry,self.lst_date_entry,self.lst_time_entry,self.mjd_entry); self._zenith_inputs=(self.zenith_selector,self.zenith_ra_entry,self.zenith_dec_entry,self.apply_zenith_button,self.zenith_date_entry)
        return self._scroll_wrap(body)

    def _build_layers_tab(self) -> QWidget:
        body=QWidget(); l=QVBoxLayout(body); l.setContentsMargins(10,10,10,10); l.setSpacing(4)
        items=[("Directions",self.direction_labels_var),("Alt/Az grid",self.altitude_grid_var),("RA/Dec grid",self.coordinate_grid_var),("Ecliptic",self.ecliptic_var),("Celestial equator",self.celestial_equator_var),("Galactic equator",self.galactic_equator_var),("Constellations",self.constellation_lines_var),("Constellation names",self.constellation_names_var),("Star names",self.star_names_var),("Solar system",self.solar_system_objects_var),("Solar labels",self.solar_system_labels_var),("Zenith",self.zenith_label_var),("Details",self.title_var)]
        for text,var in items: l.addWidget(ToggleSwitch(text=text,variable=var,command=self._redraw))
        row=QHBoxLayout(); off=QPushButton("All off"); off.clicked.connect(self._all_layers_off); study=QPushButton("Study view"); study.clicked.connect(self._study_view); row.addWidget(off); row.addWidget(study); l.addLayout(row); l.addStretch(1); return self._scroll_wrap(body)

    def _build_view_tab(self) -> QWidget:
        body = QWidget()
        l = QVBoxLayout(body)
        l.setContentsMargins(10, 10, 10, 10)
        l.setSpacing(12)

        colours = QGroupBox("Colours")
        c = QVBoxLayout(colours)
        c.setSpacing(8)
        c.addWidget(ToggleSwitch(
            text="Invert colours",
            variable=self.inverted_colors_var,
            command=self._redraw,
        ))
        l.addWidget(colours)

        field = QGroupBox("Coverage")
        f = QVBoxLayout(field)
        f.setSpacing(8)
        self.sky_radius_slider, self.sky_radius_value = self._make_slider(
            f, "From zenith", 0, 1800,
            round(self.sky_radius_var.get() * 10),
            lambda v: self._sky_radius_changed(v / 10),
        )
        l.addWidget(field)

        stars = QGroupBox("Stars")
        st = QVBoxLayout(stars)
        st.setSpacing(10)
        self.magnitude_slider, self.magnitude_value = self._make_slider(
            st, "Magnitude limit", -15, 80,
            round(self.magnitude_var.get() * 10),
            lambda v: self._magnitude_changed(v / 10),
        )
        self.marker_slider, self.marker_scale_value = self._make_slider(
            st, "Marker size", 45, 200,
            round(self.marker_scale_var.get() * 100),
            lambda v: self._marker_scale_changed(v / 100),
        )
        l.addWidget(stars)

        orient = QGroupBox("Orientation")
        o = QVBoxLayout(orient)
        o.setSpacing(9)
        self.rotation_switch = ToggleSwitch(
            text="Rotate map",
            variable=self.rotation_enabled_var,
            command=self._rotation_enabled_changed,
        )
        o.addWidget(self.rotation_switch)
        self.rotation_slider, self.rotation_value = self._make_slider(
            o, "Map rotation", 0, 3600, 0,
            lambda v: self._rotation_changed(v / 10),
        )
        rr = QHBoxLayout()
        rr.setSpacing(8)
        self.north_up_button = QPushButton("North up")
        self.north_up_button.clicked.connect(lambda: self._set_rotation(0))
        self.random_rotation_button = QPushButton("Random")
        self.random_rotation_button.clicked.connect(lambda: self._set_rotation(random.uniform(0, 360)))
        rr.addWidget(self.north_up_button)
        rr.addWidget(self.random_rotation_button)
        rr.addStretch(1)
        o.addLayout(rr)
        l.addWidget(orient)

        l.addStretch(1)
        self._update_view_readouts()
        return self._scroll_wrap(body)

    def _muted(self,text:str)->QLabel:
        label=QLabel(text); label.setObjectName("Muted"); label.setWordWrap(True); return label

    def _make_slider(self,parent:QVBoxLayout,label:str,minimum:int,maximum:int,value:int,callback):
        row=QHBoxLayout(); row.addWidget(QLabel(label)); row.addStretch(1); readout=QLabel(); readout.setObjectName("Muted"); row.addWidget(readout); parent.addLayout(row); slider=QSlider(Qt.Orientation.Horizontal); slider.setRange(minimum,maximum); slider.setValue(value); slider.valueChanged.connect(callback); parent.addWidget(slider); return slider,readout

    def _time_input_changed(self,text:str) -> None:
        previous = self.time_input_var.get()
        if previous != text and {previous, text} <= {"UTC date/time", "Local date/time"}:
            try:
                entered = datetime.strptime(f"{self.date_var.get().strip()} {self.time_var.get().strip()}", "%Y-%m-%d %H:%M:%S")
                zone = zone_for_coordinates(float(self.latitude_var.get()), float(self.longitude_var.get()))
                instant = entered.replace(tzinfo=timezone.utc) if previous == "UTC date/time" else local_to_utc(entered, zone)
                converted = instant.astimezone(zone) if text == "Local date/time" else instant.astimezone(timezone.utc)
                self.date_var.set(f"{converted:%Y-%m-%d}")
                self.time_var.set(f"{converted:%H:%M:%S}")
            except (ValueError, OverflowError) as error:
                self.time_input_combo.blockSignals(True)
                self.time_input_combo.setCurrentText(previous)
                self.time_input_combo.blockSignals(False)
                QMessageBox.warning(self, "Could not convert time", str(error))
                return
        self.time_input_var.set(text); self._update_observation_states(); self._schedule_recalculation()

    def _map_location_selected(self, latitude: float, longitude: float) -> None:
        self.latitude_var.set(f"{latitude:.4f}")
        self.longitude_var.set(f"{longitude:.4f}")

    def _expand_world_map(self) -> None:
        try:
            latitude, longitude = float(self.latitude_var.get()), float(self.longitude_var.get())
        except ValueError:
            latitude, longitude = 0.0, 0.0
        dialog = ExpandedWorldMap(latitude, longitude, self)
        dialog.map.coordinateSelected.connect(self._map_location_selected)
        dialog.exec()

    def _sync_location(self) -> None:
        try:
            latitude, longitude = float(self.latitude_var.get()), float(self.longitude_var.get())
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError
            self.world_map.set_coordinates(latitude, longitude)
            zone = zone_for_coordinates(latitude, longitude)
            self.zone_label.setText(f"Time zone: {zone.key}")
        except ValueError:
            self.zone_label.setText("Enter valid coordinates")

    def _position_mode_changed(self, value: str) -> None:
        self.position_mode_var.set(value); self._update_observation_states(); self._schedule_recalculation(delay_ms=120)

    def _install_live_updates(self) -> None:
        for var in (self.latitude_var,self.longitude_var,self.date_var,self.time_var,self.lst_date_var,self.lst_time_var,self.mjd_var,self.zenith_date_var): var.changed.connect(lambda _value:self._schedule_recalculation())
        self.latitude_var.changed.connect(lambda _value: self._sync_location())
        self.longitude_var.changed.connect(lambda _value: self._sync_location())

    def _schedule_recalculation(self, *, delay_ms: int = 650) -> None:
        if not hasattr(self,"_debounce"): return
        self.status_label.setText("Updating…"); self._debounce.start(max(0,int(delay_ms)))

    def _apply_manual_zenith(self) -> None:
        try: ra=parse_clock_hours(self.zenith_ra_input_var.get()); dec=float(self.zenith_dec_input_var.get().strip())
        except ValueError:
            QMessageBox.critical(self,"Invalid zenith coordinates","RA must be decimal hours or HH:MM:SS and declination must be numeric."); return
        if not -90<=dec<=90: QMessageBox.critical(self,"Invalid zenith coordinates","Declination must be between -90 and +90 degrees."); return
        self.zenith_ra_var.set(ra); self.zenith_dec_var.set(dec); self._update_zenith_readouts(sync_inputs=True)
        if self.position_mode_var.get()=="zenith": self._request_exact_zenith_recalculation()

    def _update_zenith_input_values(self) -> None:
        self.zenith_ra_input_var.set(f"{self.zenith_ra_var.get()%24:.8f}"); self.zenith_dec_input_var.set(f"{self.zenith_dec_var.get():.8f}")

    def _zenith_selector_moved(self) -> None:
        self._update_zenith_readouts(sync_inputs=True)
        if self.position_mode_var.get()=="zenith": self._request_zenith_preview()

    def _zenith_selector_released(self) -> None:
        self._update_zenith_readouts(sync_inputs=True)
        if self.position_mode_var.get()=="zenith":
            self._request_zenith_preview()
            self._draw_zenith_preview()
            self._request_exact_zenith_recalculation()

    def _request_zenith_preview(self) -> None:
        """Schedule a cheap, frame-limited preview while the zenith moves."""
        if self._model is None or self.position_mode_var.get() != "zenith":
            return
        self._zenith_preview_target = (
            self.zenith_ra_var.get() % 24.0,
            self.zenith_dec_var.get(),
        )
        self.save_button.setEnabled(False)
        if not self._preview_timer.isActive():
            self._preview_timer.start()

    def _request_exact_zenith_recalculation(self) -> None:
        """Keep the preview visible, then calculate one exact final sky."""
        if self.position_mode_var.get() != "zenith":
            return
        self._preview_timer.stop()
        self._zenith_preview_target = None
        self._zenith_preview_background = None
        self._zenith_preview_bbox = None
        self._zenith_preview_active = False
        # Make the final lightweight frame part of normal painting so it stays
        # visible while the authoritative Astropy/Skyfield calculation runs.
        self.renderer.freeze_interactive_preview()
        self.save_button.setEnabled(False)
        self._schedule_recalculation(delay_ms=0)
        self.status_label.setText("Refining…")

    @staticmethod
    def _reproject_horizontal_arrays(
        altitude_degrees,
        azimuth_degrees,
        *,
        source_zenith_ra_hours: float,
        source_zenith_dec_degrees: float,
        target_zenith_ra_hours: float,
        target_zenith_dec_degrees: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Rotate cached horizontal directions to a new celestial zenith.

        This is the fast drag path.  It treats the already-calculated sky as a
        rigid celestial sphere and changes only the observer basis.  That is
        visually exact for panning the sphere and avoids rebuilding Astropy
        frames, catalogues, constellation geometry, and ephemerides for every
        mouse event.  A full calculation still runs when the drag finishes.
        """
        altitude = np.deg2rad(np.asarray(altitude_degrees, dtype=float))
        azimuth = np.deg2rad(np.asarray(azimuth_degrees, dtype=float))
        source_latitude = math.radians(float(source_zenith_dec_degrees))
        target_latitude = math.radians(float(target_zenith_dec_degrees))

        sin_altitude = np.sin(altitude)
        cos_altitude = np.cos(altitude)
        sin_source_latitude = math.sin(source_latitude)
        cos_source_latitude = math.cos(source_latitude)

        sin_declination = (
            sin_source_latitude * sin_altitude
            + cos_source_latitude * cos_altitude * np.cos(azimuth)
        )
        sin_declination = np.clip(sin_declination, -1.0, 1.0)
        declination = np.arcsin(sin_declination)
        cos_declination = np.cos(declination)

        sin_hour_angle_component = -cos_altitude * np.sin(azimuth)
        cos_hour_angle_component = (
            cos_source_latitude * sin_altitude
            - sin_source_latitude * cos_altitude * np.cos(azimuth)
        )
        source_hour_angle = np.arctan2(
            sin_hour_angle_component,
            cos_hour_angle_component,
        )
        source_lst = math.radians((float(source_zenith_ra_hours) % 24.0) * 15.0)
        right_ascension = source_lst - source_hour_angle
        target_lst = math.radians((float(target_zenith_ra_hours) % 24.0) * 15.0)
        target_hour_angle = target_lst - right_ascension

        sin_target_latitude = math.sin(target_latitude)
        cos_target_latitude = math.cos(target_latitude)
        sin_target_altitude = (
            sin_target_latitude * sin_declination
            + cos_target_latitude * cos_declination * np.cos(target_hour_angle)
        )
        target_altitude = np.arcsin(np.clip(sin_target_altitude, -1.0, 1.0))

        east = -cos_declination * np.sin(target_hour_angle)
        north = (
            sin_declination * cos_target_latitude
            - cos_declination * np.cos(target_hour_angle) * sin_target_latitude
        )
        target_azimuth = np.mod(np.arctan2(east, north), 2.0 * np.pi)
        return np.rad2deg(target_altitude), np.rad2deg(target_azimuth)

    def _fast_preview_model(self, target_ra: float, target_dec: float) -> SkyMapModel | None:
        model = self._model
        if model is None:
            return None
        source_ra = self._model_zenith_ra
        source_dec = self._model_zenith_dec
        if source_ra is None:
            source_ra = local_sidereal_time_hours(
                model.settings.observation_datetime, model.settings.longitude
            )
            self._model_zenith_ra = source_ra
        if source_dec is None:
            source_dec = float(model.settings.latitude)
            self._model_zenith_dec = source_dec

        preview_limit = min(float(self.magnitude_var.get()), 6.25)
        preview_mask = model.stars.magnitude <= preview_limit
        altitude, azimuth = self._reproject_horizontal_arrays(
            model.stars.altitude[preview_mask],
            model.stars.azimuth[preview_mask],
            source_zenith_ra_hours=source_ra,
            source_zenith_dec_degrees=source_dec,
            target_zenith_ra_hours=target_ra,
            target_zenith_dec_degrees=target_dec,
        )
        preview_stars = replace(
            model.stars,
            hip=model.stars.hip[preview_mask],
            altitude=altitude,
            azimuth=azimuth,
            magnitude=model.stars.magnitude[preview_mask],
        )
        rotation = self.rotation_var.get() % 360.0 if self.rotation_enabled_var.get() else 0.0
        preview_settings = replace(
            model.settings,
            latitude=float(target_dec),
            longitude=0.0,
            map_rotation_degrees=rotation,
            inverted_colors=self.inverted_colors_var.get(),
            sky_radius_degrees=self.sky_radius_var.get(),
            star_marker_scale=self.marker_scale_var.get(),
        )
        return replace(model, settings=preview_settings, stars=preview_stars)

    def _fast_preview_options(self) -> RenderOptions:
        """Use a deliberately light layer set while the mouse is down."""
        return RenderOptions(
            show_direction_labels=self.direction_labels_var.get(),
            show_altitude_grid=self.altitude_grid_var.get(),
            show_zenith_label=self.zenith_label_var.get(),
            # A modest preview cap keeps dense magnitude-8 catalogues fluid.
            # The user's exact magnitude and every detailed layer return on
            # mouse release after the authoritative calculation completes.
            limiting_magnitude=min(float(self.magnitude_var.get()), 6.25),
            star_marker_scale=self.marker_scale_var.get(),
        )

    def _draw_zenith_preview(self) -> None:
        target = self._zenith_preview_target
        if target is None or self.position_mode_var.get() != "zenith":
            return
        preview = self._fast_preview_model(*target)
        if preview is None:
            return
        options = self._fast_preview_options()
        axes = self.renderer.axes
        current_bbox = tuple(float(value) for value in axes.bbox.bounds)
        needs_background = (
            not self._zenith_preview_active
            or self._zenith_preview_background is None
            or self._zenith_preview_bbox != current_bbox
        )
        if needs_background:
            self.renderer.prepare_interactive_preview(preview, options)
            # Render the static axes once, cache them, then blit only the stars
            # on subsequent mouse events.  This avoids repainting every label,
            # spine, and Matplotlib widget dozens of times per second.
            self.canvas.draw()
            self._zenith_preview_background = self.canvas.copy_from_bbox(axes.bbox)
            self._zenith_preview_bbox = tuple(float(value) for value in axes.bbox.bounds)
            self._zenith_preview_active = True

        artist = self.renderer.update_interactive_stars(preview, options)
        if self._zenith_preview_background is not None:
            self.canvas.restore_region(self._zenith_preview_background)
            axes.draw_artist(artist)
            self.canvas.blit(axes.bbox)
        else:
            self.canvas.draw_idle()
        self.status_label.setText("Preview — release to refine.")

    @staticmethod
    def _sky_map_point_equatorial_for_center(
        center_ra: float,
        center_dec: float,
        theta_radians: float,
        radius_degrees: float,
    ) -> tuple[float, float]:
        """Return RA/Dec for one polar-chart point around a supplied zenith."""
        radius = max(0.0, min(179.999, float(radius_degrees)))
        altitude = 90.0 - radius
        azimuth = math.degrees(float(theta_radians)) % 360.0
        dec, hour_angle = equatorial_from_horizontal(center_dec, altitude, azimuth)
        ra = ra_from_lst_hour_angle(center_ra % 24.0, hour_angle)
        return ra, dec

    def _sky_map_point_equatorial(self, theta_radians: float, radius_degrees: float) -> tuple[float, float]:
        return self._sky_map_point_equatorial_for_center(
            self.zenith_ra_var.get(), self.zenith_dec_var.get(), theta_radians, radius_degrees
        )

    def _set_direct_zenith(self, ra: float, dec: float, *, preview: bool) -> None:
        self.zenith_ra_var.set(float(ra) % 24.0)
        self.zenith_dec_var.set(max(-90.0, min(90.0, float(dec))))
        self._update_zenith_readouts(sync_inputs=True)
        if self.position_mode_var.get() == "zenith":
            if preview:
                self._request_zenith_preview()
            else:
                self._request_exact_zenith_recalculation()

    def _sky_map_press(self, event) -> None:
        if self.position_mode_var.get() != "zenith" or event.button != 1:
            return
        if event.inaxes is not self.renderer.axes or event.xdata is None or event.ydata is None:
            return
        if not 0.0 <= float(event.ydata) <= self.sky_radius_var.get() + 1e-6:
            return
        if event.x is None or event.y is None:
            return
        center_x, center_y = self.renderer.axes.transData.transform((0.0, 0.0))
        self._map_drag_state = {
            "start_x": float(event.x),
            "start_y": float(event.y),
            "center_x": float(center_x),
            "center_y": float(center_y),
            "initial_ra": self.zenith_ra_var.get() % 24.0,
            "initial_dec": self.zenith_dec_var.get(),
            "press_theta": float(event.xdata),
            "press_radius": float(event.ydata),
            "moved": False,
        }
        self.canvas.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _zenith_from_drag_displacement(self, state: dict[str, float | bool], x: float, y: float) -> tuple[float, float]:
        """Translate a screen-space pan into a new celestial zenith."""
        dx = float(x) - float(state["start_x"])
        dy = float(y) - float(state["start_y"])
        # Dragging the picture right means the viewport centre moves left, so
        # sample the opposite displacement around the old zenith.  Using the
        # actual Matplotlib inverse transform automatically respects map radius,
        # aspect ratio, north-up rotation, and any explicit map rotation.
        theta, radius = self.renderer.axes.transData.inverted().transform((
            float(state["center_x"]) - dx,
            float(state["center_y"]) - dy,
        ))
        return self._sky_map_point_equatorial_for_center(
            float(state["initial_ra"]),
            float(state["initial_dec"]),
            float(theta),
            float(radius),
        )

    def _sky_map_move(self, event) -> None:
        state = self._map_drag_state
        if state is None or self.position_mode_var.get() != "zenith" or event.x is None or event.y is None:
            return
        distance = math.hypot(float(event.x) - float(state["start_x"]), float(event.y) - float(state["start_y"]))
        if distance < 3.0 and not bool(state["moved"]):
            return
        state["moved"] = True
        ra, dec = self._zenith_from_drag_displacement(state, float(event.x), float(event.y))
        self._set_direct_zenith(ra, dec, preview=True)
        self.status_label.setText("Drag to reposition.")

    def _sky_map_release(self, event) -> None:
        state = self._map_drag_state
        if state is None:
            return
        self._map_drag_state = None
        self.canvas.setCursor(Qt.CursorShape.OpenHandCursor if self.position_mode_var.get() == "zenith" else Qt.CursorShape.ArrowCursor)
        if event.x is None or event.y is None:
            return
        if bool(state["moved"]):
            ra, dec = self._zenith_from_drag_displacement(state, float(event.x), float(event.y))
        elif event.inaxes is self.renderer.axes and event.xdata is not None and event.ydata is not None:
            ra, dec = self._sky_map_point_equatorial_for_center(
                float(state["initial_ra"]), float(state["initial_dec"]),
                float(event.xdata), float(event.ydata),
            )
        else:
            return
        # Show the final selected position immediately, even for a simple
        # click, then hand off to the exact astronomy calculation.
        self._set_direct_zenith(ra, dec, preview=True)
        self._draw_zenith_preview()
        self._request_exact_zenith_recalculation()


    def _sky_map_zoom(self, steps: float) -> None:
        """Queue smooth sky-coverage zoom from a wheel or touchpad gesture."""
        if not math.isfinite(steps) or abs(steps) < 1e-6:
            return
        current = self._zoom_pending_radius
        if current is None:
            current = max(5.0, float(self.sky_radius_var.get()))
        target = current * math.exp(-0.08 * float(steps))
        self._zoom_pending_radius = max(5.0, min(180.0, target))
        if not self._zoom_timer.isActive():
            self._zoom_timer.start()

    def _apply_pending_sky_map_zoom(self) -> None:
        target = self._zoom_pending_radius
        self._zoom_pending_radius = None
        if target is None:
            return
        slider_value = int(round(target * 10.0))
        if slider_value != self.sky_radius_slider.value():
            self.sky_radius_slider.setValue(slider_value)
        self.status_label.setText(f"Coverage · {slider_value / 10.0:.1f}°")

    def _update_observation_states(self) -> None:
        if not hasattr(self,"_observer_inputs"): return
        observer=self.position_mode_var.get()=="observer"
        if observer:
            self._map_drag_state = None
            if hasattr(self, "_preview_timer"):
                self._preview_timer.stop()
            self._zenith_preview_target = None
            self._zenith_preview_background = None
            self._zenith_preview_bbox = None
            self._zenith_preview_active = False
            if hasattr(self, "renderer"):
                self.renderer.end_interactive_preview()
        for w in (self.latitude_entry,self.longitude_entry): w.setEnabled(observer)
        self.observer_group.setVisible(observer)
        self.location_group.setVisible(observer)
        self.zenith_group.setVisible(not observer)
        self.time_input_combo.setEnabled(observer)
        form=self.time_input_var.get();
        for w in (self.utc_date_label,self.utc_date_entry,self.utc_time_label,self.utc_time_entry): w.setVisible(form in {"UTC date/time", "Local date/time"})
        self.utc_date_label.setText("Local date" if form == "Local date/time" else "UTC date")
        self.utc_time_label.setText("Local time" if form == "Local date/time" else "UTC time")
        for w in (self.lst_date_label,self.lst_date_entry,self.lst_time_label,self.lst_time_entry): w.setVisible(form=="LST + UTC date")
        for w in (self.mjd_label,self.mjd_entry): w.setVisible(form=="MJD")
        self.zenith_selector.set_enabled(not observer)
        for w in (self.zenith_ra_entry,self.zenith_dec_entry,self.apply_zenith_button,self.zenith_date_entry): w.setEnabled(not observer)
        if hasattr(self, "canvas"):
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor if observer else Qt.CursorShape.OpenHandCursor)

    def _update_rotation_state(self) -> None:
        if not hasattr(self,"rotation_slider"): return
        enabled=self.rotation_enabled_var.get(); self.rotation_slider.setEnabled(enabled); self.north_up_button.setEnabled(enabled); self.random_rotation_button.setEnabled(enabled)
        if not enabled: self.rotation_var.set(0); self.rotation_slider.blockSignals(True); self.rotation_slider.setValue(0); self.rotation_slider.blockSignals(False); self.rotation_value.setText("0.0°")

    def _parse_settings(self) -> MapSettings:
        if self.position_mode_var.get()=="zenith":
            latitude=self.zenith_dec_var.get(); longitude=0.0; zenith_ra=self.zenith_ra_var.get()%24; observation=datetime_for_local_sidereal_time(self.zenith_date_var.get(),zenith_ra,longitude); self._source_description=f"Direct zenith: RA {format_clock_hours(zenith_ra)}, Dec {latitude:+.2f}°"
        else:
            try: latitude=float(self.latitude_var.get().strip()); longitude=float(self.longitude_var.get().strip())
            except ValueError as error: raise ValueError("Latitude and longitude must be numbers.") from error
            if not -90<=latitude<=90: raise ValueError("Latitude must be between -90 and +90 degrees.")
            if not -180<=longitude<=180: raise ValueError("Longitude must be between -180 and +180 degrees.")
            form=self.time_input_var.get()
            if form=="UTC date/time":
                try: observation=datetime.strptime(f"{self.date_var.get().strip()} {self.time_var.get().strip()}","%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                except ValueError as error: raise ValueError("UTC date/time must use YYYY-MM-DD and HH:MM:SS.") from error
            elif form=="Local date/time":
                try: local_value=datetime.strptime(f"{self.date_var.get().strip()} {self.time_var.get().strip()}","%Y-%m-%d %H:%M:%S")
                except ValueError as error: raise ValueError("Local date/time must use YYYY-MM-DD and HH:MM:SS.") from error
                observation=local_to_utc(local_value, zone_for_coordinates(latitude, longitude))
            elif form=="LST + UTC date": observation=datetime_for_local_sidereal_time(self.lst_date_var.get(),parse_clock_hours(self.lst_time_var.get()),longitude)
            elif form=="MJD": observation=datetime_from_mjd(float(self.mjd_var.get().strip()))
            else: raise ValueError("Select a supported time input form.")
            self._source_description=f"Observer location + {form}"
        rotation=self.rotation_var.get()%360 if self.rotation_enabled_var.get() else 0.0
        return MapSettings(latitude=latitude,longitude=longitude,observation_datetime=observation,limiting_magnitude=self.CALCULATION_MAGNITUDE_LIMIT,map_rotation_degrees=rotation,include_solar_system_objects=True,inverted_colors=self.inverted_colors_var.get(),sky_radius_degrees=self.MAXIMUM_SKY_RADIUS,star_marker_scale=self.marker_scale_var.get())

    def generate_map(self, *, show_errors: bool = True) -> None:
        try: settings=self._parse_settings()
        except (TypeError,ValueError) as error:
            self.status_label.setText(f"Check input: {error}")
            if show_errors: QMessageBox.critical(self,"Invalid observation",str(error))
            return
        self._generation+=1; self._future_generation=self._generation; self.status_label.setText("Calculating star positions…")
        if hasattr(self, "_preview_timer"):
            self._preview_timer.stop()
        self._zenith_preview_target=None; self._zenith_preview_background=None; self._zenith_preview_bbox=None; self._zenith_preview_active=False; self.renderer.end_interactive_preview()
        while True:
            try: self._progress_messages.get_nowait()
            except queue.Empty: break
        if self._current_future is not None and not self._current_future.done(): self._current_future.cancel()
        self._current_future=self._executor.submit(lambda:self._calculator.calculate(settings,progress=self._progress_messages.put)); self._poll_timer.start()

    def _poll_future(self) -> None:
        future=self._current_future
        if future is None or self._future_generation!=self._generation: self._poll_timer.stop(); return
        latest=None
        while True:
            try: latest=self._progress_messages.get_nowait()
            except queue.Empty: break
        if latest: self.status_label.setText(latest)
        if not future.done(): return
        self._poll_timer.stop()
        try: model=future.result()
        except Exception as error: self.status_label.setText("Sky-map calculation failed."); QMessageBox.critical(self,"Could not generate sky map",f"{type(error).__name__}: {error}"); return
        self._model=model
        self._model_zenith_ra=local_sidereal_time_hours(model.settings.observation_datetime, model.settings.longitude)
        self._model_zenith_dec=float(model.settings.latitude)
        self._zenith_preview_background=None; self._zenith_preview_bbox=None; self._zenith_preview_active=False; self.renderer.end_interactive_preview()
        self.save_button.setEnabled(True); self.status_label.setText(f"Ready · {len(model.stars.hip):,} stars"); self._redraw()

    def _refresh_metadata(self, model: SkyMapModel) -> None:
        s=model.settings; utc=s.observation_datetime.astimezone(timezone.utc); self.metadata_label.setText(f"Lat {s.latitude:.5f}°  ·  Lon {s.longitude:.5f}°\nUTC {utc:%Y-%m-%d %H:%M:%S}\nMJD {mjd_from_datetime(utc):.6f}  ·  LST {format_local_sidereal_time(s)}\nRotation {s.map_rotation_degrees:.1f}°")

    def _render_options(self) -> RenderOptions:
        return RenderOptions(show_direction_labels=self.direction_labels_var.get(),show_altitude_grid=self.altitude_grid_var.get(),show_title=self.title_var.get(),show_ecliptic=self.ecliptic_var.get(),show_celestial_equator=self.celestial_equator_var.get(),show_galactic_equator=self.galactic_equator_var.get(),show_constellation_names=self.constellation_names_var.get(),show_constellation_lines=self.constellation_lines_var.get(),show_star_names=self.star_names_var.get(),show_coordinate_grid=self.coordinate_grid_var.get(),show_solar_system_objects=self.solar_system_objects_var.get(),show_solar_system_labels=self.solar_system_labels_var.get(),show_zenith_label=self.zenith_label_var.get(),limiting_magnitude=self.magnitude_var.get(),star_marker_scale=self.marker_scale_var.get())

    def _redraw(self) -> None:
        if self._model is None: return
        rotation=self.rotation_var.get()%360 if self.rotation_enabled_var.get() else 0.0; display=replace(self._model,settings=replace(self._model.settings,map_rotation_degrees=rotation,inverted_colors=self.inverted_colors_var.get(),sky_radius_degrees=self.sky_radius_var.get(),star_marker_scale=self.marker_scale_var.get())); self._refresh_metadata(display); self.renderer.draw(display,self._render_options()); self.canvas.draw_idle()

    def _update_view_readouts(self) -> None:
        if not hasattr(self,"sky_radius_value"): return
        r=self.sky_radius_var.get(); suffix=" (full sky)" if abs(r-180)<.6 else (" (hemisphere)" if abs(r-90)<.6 else ""); self.sky_radius_value.setText(f"{r:.0f}°{suffix}"); self.magnitude_value.setText(f"{self.magnitude_var.get():.1f}"); self.marker_scale_value.setText(f"{self.marker_scale_var.get():.2f}×"); self.rotation_value.setText(f"{self.rotation_var.get()%360:.1f}°")

    def _update_zenith_readouts(self, *, sync_inputs: bool=True) -> None:
        ra=self.zenith_ra_var.get()%24; dec=self.zenith_dec_var.get()
        if hasattr(self,"zenith_ra_label"): self.zenith_ra_label.setText(f"RA {format_clock_hours(ra)}"); self.zenith_dec_label.setText(f"Dec {dec:+.4f}°")
        if sync_inputs: self.zenith_ra_input_var.set(f"{ra:.8f}"); self.zenith_dec_input_var.set(f"{dec:.8f}")

    def _magnitude_changed(self,value:float)->None: self.magnitude_var.set(value); self._update_view_readouts(); self._redraw()
    def _sky_radius_changed(self,value:float)->None: self.sky_radius_var.set(value); self._update_view_readouts(); self._redraw()
    def _rotation_changed(self,value:float)->None: self.rotation_var.set(value%360); self._update_view_readouts(); self._redraw()
    def _marker_scale_changed(self,value:float)->None: self.marker_scale_var.set(value); self._update_view_readouts(); self._redraw()
    def _rotation_enabled_changed(self)->None: self._update_rotation_state(); self._redraw()
    def _set_rotation(self,value:float)->None:
        self.rotation_var.set(value%360); self.rotation_slider.setValue(round((value%360)*10)); self._update_view_readouts(); self._redraw()

    def _layer_variables(self): return (self.direction_labels_var,self.altitude_grid_var,self.coordinate_grid_var,self.ecliptic_var,self.celestial_equator_var,self.galactic_equator_var,self.constellation_lines_var,self.constellation_names_var,self.star_names_var,self.solar_system_objects_var,self.solar_system_labels_var,self.zenith_label_var,self.title_var)
    def _all_layers_off(self)->None:
        for v in self._layer_variables(): v.set(False)
        self._redraw()
    def _study_view(self)->None:
        for v in self._layer_variables(): v.set(True)
        self._redraw()

    def _save_png(self) -> None:
        if self._model is None:return
        utc=self._model.settings.observation_datetime.astimezone(timezone.utc); filename,_=QFileDialog.getSaveFileName(self,"Save generated sky map",f"sky_map_{utc:%Y%m%d_%H%M%S}.png","PNG image (*.png);;All files (*)")
        if not filename:return
        if not filename.lower().endswith(".png"):filename+=".png"
        try:self.figure.savefig(filename,dpi=220,bbox_inches="tight",facecolor=self.figure.get_facecolor()); self.status_label.setText(f"Saved {filename}")
        except OSError as error:QMessageBox.critical(self,"Could not save image",str(error))

    def closeEvent(self,event)->None:  # noqa: N802
        self._generation+=1
        if hasattr(self,"_debounce"):self._debounce.stop()
        if hasattr(self,"_preview_timer"):self._preview_timer.stop()
        if hasattr(self,"_zoom_timer"):self._zoom_timer.stop()
        self._poll_timer.stop() if hasattr(self,"_poll_timer") else None; self._executor.shutdown(wait=False,cancel_futures=True); event.accept()


def run_generator() -> int:
    app=QApplication.instance() or QApplication(sys.argv); window=SkyMapGeneratorApplication(); window.show(); return app.exec()
