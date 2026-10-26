"""Guided PyQt6 equatorial / horizontal coordinate converter UI."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea,
    QTabWidget, QVBoxLayout, QWidget,
)

from .coordinate_converter import (
    equatorial_from_horizontal, format_degrees, format_hours,
    horizontal_from_equatorial, hour_angle_from_lst_ra, lst_from_ra_hour_angle,
    parse_degrees, parse_hours, ra_from_lst_hour_angle,
)
from .generation_settings import load_generation_settings
from .theme import apply_night_theme
from .celestial_sphere_widget import CelestialSphereTriangle
from .widgets import SegmentedControl, StringVar, bind_line_edit


class CoordinateConverterApplication(QWidget):
    """A guided converter between equatorial and horizontal coordinates."""

    AUTOFILL_DELAY_MS = 220

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Coordinate Converter")
        self.resize(920, 760); self.setMinimumSize(680, 520)
        settings=load_generation_settings(); self._programmatic_update=False; self._sphere_visualizers:list[CelestialSphereTriangle]=[]
        self.latitude_var=StringVar(); self.ra_var=StringVar(); self.dec_var=StringVar(); self.lst_var=StringVar(); self.ha_var=StringVar(); self.alt_var=StringVar(); self.az_var=StringVar()
        self.forward_time_mode=StringVar("lst"); self.reverse_time_anchor=StringVar("lst")
        self._build_ui(); apply_night_theme(self,settings.night_mode); self._install_live_updates()
        self._solve_timer=QTimer(self); self._solve_timer.setSingleShot(True); self._solve_timer.timeout.connect(self._solve_active_tab); QTimer.singleShot(0,self._solve_active_tab)

    def _build_ui(self)->None:
        layout=QVBoxLayout(self);layout.setContentsMargins(14,14,14,14);layout.setSpacing(10)
        title=QLabel("Coordinate Converter");title.setObjectName("PageTitle");layout.addWidget(title)
        self.tabs=QTabWidget();self.tabs.currentChanged.connect(lambda _i:self._solve_active_tab());layout.addWidget(self.tabs,1)
        self.tabs.addTab(self._build_forward_tab(),"RA / Dec  →  Alt / Az");self.tabs.addTab(self._build_reverse_tab(),"Alt / Az  →  RA / Dec")
        foot=QFrame();fl=QVBoxLayout(foot);fl.setContentsMargins(0,0,0,0);row=QHBoxLayout();row.addStretch(1);copy=QPushButton("Copy");copy.clicked.connect(self._copy_values);clear=QPushButton("Clear");clear.clicked.connect(self._clear_all);row.addWidget(copy);row.addWidget(clear);fl.addLayout(row);layout.addWidget(foot)

    def _scroll(self,body:QWidget)->QScrollArea:
        s=QScrollArea();s.setWidgetResizable(True);s.setFrameShape(QFrame.Shape.NoFrame);s.setWidget(body);return s

    def _build_forward_tab(self)->QWidget:
        body=QWidget();l=QVBoxLayout(body);l.setContentsMargins(10,10,10,10);l.setSpacing(10)
        columns=QHBoxLayout();inputs=QGroupBox("Input");ig=QGridLayout(inputs);self._input_row(ig,0,"Latitude φ",self.latitude_var,"°");self._input_row(ig,1,"RA α",self.ra_var,"h");self._input_row(ig,2,"Dec δ",self.dec_var,"°")
        self.forward_time_selector=SegmentedControl((("lst","LST"),("ha","Hour angle")),value="lst")
        self.forward_time_selector.valueChanged.connect(self._forward_mode_changed)
        ig.addWidget(self.forward_time_selector,4,0,1,3)
        self.forward_time_input_label=QLabel("LST");ig.addWidget(self.forward_time_input_label,5,0);self.forward_time_input=QLineEdit();ig.addWidget(self.forward_time_input,5,1);ig.addWidget(QLabel("h"),5,2);columns.addWidget(inputs,1)
        results=QGroupBox("Result");rg=QGridLayout(results);self.forward_time_result_label=QLabel("Hour angle H");rg.addWidget(self.forward_time_result_label,0,0);self.forward_time_result=QLineEdit();self.forward_time_result.setReadOnly(True);rg.addWidget(self.forward_time_result,0,1);rg.addWidget(QLabel("h"),0,2);self._result_row(rg,1,"Altitude h",self.alt_var,"°");self._result_row(rg,2,"Azimuth A",self.az_var,"°");columns.addWidget(results,1);l.addLayout(columns)
        self.forward_status=QLabel("Enter the input values.");self.forward_status.setObjectName("Status");self.forward_status.setWordWrap(True);l.addWidget(self.forward_status)
        visualizer=self._build_celestial_sphere();l.addWidget(visualizer);l.addStretch(1);self._update_forward_time_widgets();return self._scroll(body)

    def _build_reverse_tab(self)->QWidget:
        body=QWidget();l=QVBoxLayout(body);l.setContentsMargins(10,10,10,10);l.setSpacing(10)
        columns=QHBoxLayout();inputs=QGroupBox("Input");ig=QGridLayout(inputs);self._input_row(ig,0,"Latitude φ",self.latitude_var,"°");self._input_row(ig,1,"Altitude h",self.alt_var,"°");self._input_row(ig,2,"Azimuth A",self.az_var,"°")
        self.reverse_time_selector=SegmentedControl((("lst","LST"),("ra","RA")),value="lst")
        self.reverse_time_selector.valueChanged.connect(self._reverse_mode_changed)
        ig.addWidget(self.reverse_time_selector,4,0,1,3)
        self.reverse_time_input_label=QLabel("LST");ig.addWidget(self.reverse_time_input_label,5,0);self.reverse_time_input=QLineEdit();ig.addWidget(self.reverse_time_input,5,1);ig.addWidget(QLabel("h"),5,2);columns.addWidget(inputs,1)
        results=QGroupBox("Result");rg=QGridLayout(results);self._result_row(rg,0,"Dec δ",self.dec_var,"°");self._result_row(rg,1,"Hour angle H",self.ha_var,"h");self.reverse_time_result_label=QLabel("RA α");rg.addWidget(self.reverse_time_result_label,2,0);self.reverse_time_result=QLineEdit();self.reverse_time_result.setReadOnly(True);rg.addWidget(self.reverse_time_result,2,1);rg.addWidget(QLabel("h"),2,2);columns.addWidget(results,1);l.addLayout(columns)
        self.reverse_status=QLabel("Enter the input values.");self.reverse_status.setObjectName("Status");self.reverse_status.setWordWrap(True);l.addWidget(self.reverse_status)
        visualizer=self._build_celestial_sphere();l.addWidget(visualizer);l.addStretch(1);self._update_reverse_time_widgets();return self._scroll(body)

    def _build_celestial_sphere(self)->CelestialSphereTriangle:
        v=CelestialSphereTriangle(latitude_var=self.latitude_var,ra_var=self.ra_var,dec_var=self.dec_var,lst_var=self.lst_var,ha_var=self.ha_var,alt_var=self.alt_var,az_var=self.az_var);self._sphere_visualizers.append(v);return v

    def _input_row(self,grid:QGridLayout,row:int,label:str,var:StringVar,unit:str)->None:
        grid.addWidget(QLabel(label),row,0);edit=bind_line_edit(QLineEdit(),var);grid.addWidget(edit,row,1);u=QLabel(unit);u.setObjectName("Muted");grid.addWidget(u,row,2);grid.setColumnStretch(1,1)

    def _result_row(self,grid:QGridLayout,row:int,label:str,var:StringVar,unit:str)->None:
        grid.addWidget(QLabel(label),row,0);edit=bind_line_edit(QLineEdit(),var,readonly=True);grid.addWidget(edit,row,1);u=QLabel(unit);u.setObjectName("Muted");grid.addWidget(u,row,2);grid.setColumnStretch(1,1)

    def _install_live_updates(self)->None:
        for variable in (self.latitude_var,self.ra_var,self.dec_var,self.lst_var,self.ha_var,self.alt_var,self.az_var):variable.changed.connect(lambda _v:self._field_changed())

    def _field_changed(self)->None:
        if not self._programmatic_update:self._schedule_solve()

    def _schedule_solve(self)->None:
        if hasattr(self,"_solve_timer"):self._solve_timer.start(self.AUTOFILL_DELAY_MS)

    def _solve_active_tab(self)->None:
        if self.tabs.currentIndex()==0:self._solve_forward()
        else:self._solve_reverse()

    def _forward_mode_changed(self,value:str)->None:
        self.forward_time_mode.set(value);self._update_forward_time_widgets();self._schedule_solve()

    def _reverse_mode_changed(self,value:str)->None:
        self.reverse_time_anchor.set(value);self._update_reverse_time_widgets();self._schedule_solve()

    def _rebind_edit(self,edit:QLineEdit,var:StringVar,readonly:bool=False)->None:
        # These two fields change meaning when their radio mode changes.  Remove
        # both sides of the previous binding so an inactive variable cannot later
        # overwrite the visible value.
        old_var=getattr(edit,"_ioaa_bound_var",None); old_slot=getattr(edit,"_ioaa_var_slot",None)
        if old_var is not None and old_slot is not None:
            try: old_var.changed.disconnect(old_slot)
            except (TypeError,RuntimeError): pass
        try: edit.textChanged.disconnect()
        except TypeError: pass
        edit.setReadOnly(readonly); edit.setText(var.get())
        if not readonly: edit.textChanged.connect(lambda text,v=var:v.set(text))
        slot=lambda value,e=edit:e.setText(str(value)) if e.text()!=str(value) else None
        var.changed.connect(slot); edit._ioaa_bound_var=var; edit._ioaa_var_slot=slot

    def _update_forward_time_widgets(self)->None:
        if not hasattr(self,"forward_time_input"):return
        if self.forward_time_mode.get()=="lst":self.forward_time_input_label.setText("LST");self._rebind_edit(self.forward_time_input,self.lst_var);self.forward_time_result_label.setText("Hour angle H");self._rebind_edit(self.forward_time_result,self.ha_var,True)
        else:self.forward_time_input_label.setText("Hour angle H");self._rebind_edit(self.forward_time_input,self.ha_var);self.forward_time_result_label.setText("LST");self._rebind_edit(self.forward_time_result,self.lst_var,True)

    def _update_reverse_time_widgets(self)->None:
        if not hasattr(self,"reverse_time_input"):return
        if self.reverse_time_anchor.get()=="lst":self.reverse_time_input_label.setText("LST");self._rebind_edit(self.reverse_time_input,self.lst_var);self.reverse_time_result_label.setText("RA α");self._rebind_edit(self.reverse_time_result,self.ra_var,True)
        else:self.reverse_time_input_label.setText("RA α");self._rebind_edit(self.reverse_time_input,self.ra_var);self.reverse_time_result_label.setText("LST");self._rebind_edit(self.reverse_time_result,self.lst_var,True)

    def _solve_forward(self)->None:
        mode=self.forward_time_mode.get()
        try:latitude=self._optional_degrees(self.latitude_var,-90,90,"Latitude");ra=self._optional_hours(self.ra_var,signed=False);dec=self._optional_degrees(self.dec_var,-90,90,"Declination");time_value=self._optional_hours(self.lst_var,signed=False) if mode=="lst" else self._optional_hours(self.ha_var,signed=True)
        except ValueError as error:self.forward_status.setText(str(error));return
        missing=[]
        if latitude is None:missing.append("latitude")
        if ra is None:missing.append("RA")
        if dec is None:missing.append("Dec")
        if time_value is None:missing.append("LST" if mode=="lst" else "hour angle")
        if missing:self.forward_status.setText("Still needed: "+", ".join(missing)+".");return
        assert latitude is not None and ra is not None and dec is not None and time_value is not None
        if mode=="lst":ha=hour_angle_from_lst_ra(time_value,ra);self._set_derived(self.ha_var,format_hours(ha,signed=True))
        else:ha=time_value;lst=lst_from_ra_hour_angle(ra,ha);self._set_derived(self.lst_var,format_hours(lst))
        altitude,azimuth=horizontal_from_equatorial(latitude,dec,ha);self._set_derived(self.alt_var,format_degrees(altitude,signed=True));self._set_derived(self.az_var,format_degrees(azimuth,signed=False));self.forward_status.setText("Complete.")

    def _solve_reverse(self)->None:
        anchor=self.reverse_time_anchor.get()
        try:latitude=self._optional_degrees(self.latitude_var,-90,90,"Latitude");altitude=self._optional_degrees(self.alt_var,-90,90,"Altitude");azimuth=self._optional_degrees(self.az_var,0,360,"Azimuth",wrap_360=True)
        except ValueError as error:self.reverse_status.setText(str(error));return
        missing=[]
        if latitude is None:missing.append("latitude")
        if altitude is None:missing.append("altitude")
        if azimuth is None:missing.append("azimuth")
        if missing:self.reverse_status.setText("Still needed: "+", ".join(missing)+".");return
        assert latitude is not None and altitude is not None and azimuth is not None
        dec,ha=equatorial_from_horizontal(latitude,altitude,azimuth);self._set_derived(self.dec_var,format_degrees(dec,signed=True));self._set_derived(self.ha_var,format_hours(ha,signed=True))
        try:
            if anchor=="lst":
                lst=self._optional_hours(self.lst_var,signed=False)
                if lst is None:self._clear_derived(self.ra_var);self.reverse_status.setText("Add LST for RA.");return
                self._set_derived(self.ra_var,format_hours(ra_from_lst_hour_angle(lst,ha)))
            else:
                ra=self._optional_hours(self.ra_var,signed=False)
                if ra is None:self._clear_derived(self.lst_var);self.reverse_status.setText("Add RA for LST.");return
                self._set_derived(self.lst_var,format_hours(lst_from_ra_hour_angle(ra,ha)))
        except ValueError as error:self.reverse_status.setText(str(error));return
        self.reverse_status.setText("Complete.")

    @staticmethod
    def _optional_hours(variable:StringVar,*,signed:bool)->float|None:
        text=variable.get().strip();return None if not text else parse_hours(text,signed=signed)

    @staticmethod
    def _optional_degrees(variable:StringVar,minimum:float,maximum:float,label:str,*,wrap_360:bool=False)->float|None:
        text=variable.get().strip();return None if not text else parse_degrees(text,minimum=minimum,maximum=maximum,label=label,wrap_360=wrap_360)

    def _set_derived(self,variable:StringVar,text:str)->None:
        self._programmatic_update=True
        try:variable.set(text)
        finally:self._programmatic_update=False

    def _clear_derived(self,variable:StringVar)->None:
        if variable.get():self._set_derived(variable,"")

    def _copy_values(self)->None:
        fields=[("Latitude",self.latitude_var.get()),("RA",self.ra_var.get()),("Dec",self.dec_var.get()),("LST",self.lst_var.get()),("Hour angle",self.ha_var.get()),("Altitude",self.alt_var.get()),("Azimuth",self.az_var.get())];text="\n".join(f"{name}: {value}" for name,value in fields if value.strip())
        if text:QApplication.clipboard().setText(text)

    def _clear_all(self)->None:
        if hasattr(self,"_solve_timer"):self._solve_timer.stop()
        self._programmatic_update=True
        try:
            for v in (self.latitude_var,self.ra_var,self.dec_var,self.lst_var,self.ha_var,self.alt_var,self.az_var):v.set("")
        finally:self._programmatic_update=False
        self.forward_status.setText("Enter the input values.");self.reverse_status.setText("Enter the input values.")


def run_coordinate_converter()->int:
    app=QApplication.instance() or QApplication(sys.argv);window=CoordinateConverterApplication();window.show();return app.exec()
