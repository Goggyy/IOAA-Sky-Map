"""Reusable PyQt6 widgets used throughout the application."""

from __future__ import annotations

import math
from typing import Callable, Generic, TypeVar

from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPainterPath, QPen, QWheelEvent
from PyQt6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .theme import (
    NIGHT_BACKGROUND,
    NIGHT_BORDER,
    NIGHT_FIELD,
    NIGHT_MUTED,
    NIGHT_TEXT,
    night_mode_enabled,
)

T = TypeVar("T")


class Value(QObject, Generic[T]):
    """Tiny observable value object used to keep calculation code UI-agnostic."""

    changed = pyqtSignal(object)

    def __init__(self, value: T) -> None:
        super().__init__()
        self._value = value

    def get(self) -> T:
        return self._value

    def set(self, value: T) -> None:
        if value == self._value:
            return
        self._value = value
        self.changed.emit(value)

    def trace_add(self, _mode: str, callback: Callable[..., None]):
        def wrapped(_value: object) -> None:
            callback()
        self.changed.connect(wrapped)
        return wrapped

    def trace_remove(self, _mode: str, token) -> None:
        try:
            self.changed.disconnect(token)
        except (TypeError, RuntimeError):
            pass


class StringVar(Value[str]):
    def __init__(self, value: str = "") -> None:
        super().__init__(str(value))

    def set(self, value: object) -> None:
        super().set(str(value))


class DoubleVar(Value[float]):
    def __init__(self, value: float = 0.0) -> None:
        super().__init__(float(value))

    def set(self, value: object) -> None:
        super().set(float(value))


class BooleanVar(Value[bool]):
    def __init__(self, value: bool = False) -> None:
        super().__init__(bool(value))

    def set(self, value: object) -> None:
        super().set(bool(value))


def bind_line_edit(edit: QLineEdit, variable: StringVar, *, readonly: bool = False) -> QLineEdit:
    """Two-way bind a QLineEdit to a StringVar."""
    edit.setText(variable.get())
    edit.setReadOnly(readonly)

    def from_widget(text: str) -> None:
        if not readonly:
            variable.set(text)

    def from_value(value: object) -> None:
        text = str(value)
        if edit.text() != text:
            edit.setText(text)

    edit.textChanged.connect(from_widget)
    variable.changed.connect(from_value)
    return edit


class SegmentedControl(QFrame):
    """Compact mutually-exclusive selector for two or more related modes."""

    valueChanged = pyqtSignal(str)

    def __init__(
        self,
        options: list[tuple[str, str]] | tuple[tuple[str, str], ...],
        *,
        value: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not options:
            raise ValueError("SegmentedControl requires at least one option.")
        self.setObjectName("SegmentedControl")
        self._buttons: dict[str, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        for key, label in options:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setProperty("segment", True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, k=key: self._emit_value(k))
            self._group.addButton(button)
            self._buttons[key] = button
            layout.addWidget(button, 1)
        self.set_value(value if value in self._buttons else options[0][0], emit=False)

    def _emit_value(self, key: str) -> None:
        if self._buttons[key].isChecked():
            self.valueChanged.emit(key)

    def value(self) -> str:
        for key, button in self._buttons.items():
            if button.isChecked():
                return key
        return next(iter(self._buttons))

    def set_value(self, value: str, *, emit: bool = False) -> None:
        if value not in self._buttons:
            raise ValueError(f"Unknown segmented-control value: {value}")
        changed = self.value() != value
        button = self._buttons[value]
        button.setChecked(True)
        if emit and changed:
            self.valueChanged.emit(value)

    def set_option_enabled(self, value: str, enabled: bool) -> None:
        if value in self._buttons:
            self._buttons[value].setEnabled(enabled)



class ToggleSwitch(QAbstractButton):
    """Compact modern switch with a text label."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        text: str,
        variable: BooleanVar | None = None,
        command: Callable[[], None] | None = None,
        wraplength: int | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(30)
        self._variable = variable
        self._command = command
        self._wraplength = wraplength
        if variable is not None:
            self.setChecked(bool(variable.get()))

            def sync_from_variable(value: object) -> None:
                self.blockSignals(True)
                try:
                    self.setChecked(bool(value))
                finally:
                    self.blockSignals(False)
                self.update()

            variable.changed.connect(sync_from_variable)
        self.toggled.connect(self._toggled)

    def _toggled(self, checked: bool) -> None:
        if self._variable is not None:
            self._variable.set(checked)
        if self._command is not None:
            self._command()
        self.update()

    def set_enabled(self, enabled: bool) -> None:
        self.setEnabled(enabled)

    def refresh_theme(self) -> None:
        self.update()

    def sizeHint(self):  # noqa: N802 - Qt API
        hint = super().sizeHint()
        hint.setHeight(max(30, hint.height()))
        hint.setWidth(max(190, hint.width() + 48))
        return hint

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        night = night_mode_enabled(self)
        enabled = self.isEnabled()
        checked = self.isChecked()
        track_on = QColor(NIGHT_TEXT if night else "#2867c7")
        track_off = QColor(NIGHT_BORDER if night else "#aab5c4")
        if not enabled:
            track_on = track_off = QColor(NIGHT_FIELD if night else "#d6dce5")
        knob = QColor(NIGHT_BACKGROUND if night else "#ffffff")
        text_color = QColor(
            (NIGHT_TEXT if enabled else NIGHT_MUTED)
            if night
            else ("#172033" if enabled else "#9aa4b2")
        )

        track = QRectF(1.0, (self.height() - 22.0) / 2.0, 40.0, 22.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_on if checked else track_off)
        painter.drawRoundedRect(track, 11.0, 11.0)
        knob_x = track.right() - 18.0 if checked else track.left() + 3.0
        painter.setBrush(knob)
        painter.drawEllipse(QRectF(knob_x, track.top() + 3.0, 16.0, 16.0))

        painter.setPen(text_color)
        font = self.font()
        painter.setFont(font)
        text_rect = QRectF(51.0, 0.0, max(1.0, self.width() - 52.0), float(self.height()))
        flags = int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        if self._wraplength:
            flags |= int(Qt.TextFlag.TextWordWrap)
        painter.drawText(text_rect, flags, self.text())


class VerticalScrolledFrame(QScrollArea):
    """Qt scroll area exposing a `content` widget like the former helper."""

    def __init__(self, parent: QWidget | None = None, *, padding: int = 0) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(padding, padding, padding, padding)
        self.content_layout.setSpacing(10)
        self.setWidget(self.content)

    def refresh_theme(self) -> None:
        self.viewport().update()


class SmoothScrolledText(QTextEdit):
    """Compatibility name for the Qt native smooth-scrolling text editor."""

    def refresh_theme(self) -> None:
        self.viewport().update()


class CelestialSphereSelector(QWidget):
    """Interactive equirectangular selector for directly choosing zenith RA/Dec."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        ra_variable: DoubleVar,
        dec_variable: DoubleVar,
        sky_radius_variable: DoubleVar,
        command: Callable[[], None] | None = None,
        release_command: Callable[[], None] | None = None,
        height: int = 230,
    ) -> None:
        super().__init__(parent)
        self.ra_variable = ra_variable
        self.dec_variable = dec_variable
        self.sky_radius_variable = sky_radius_variable
        self.command = command
        self.release_command = release_command
        self._enabled = True
        self._dragging = False
        self._margin_left = 34.0
        self._margin_right = 14.0
        self._margin_top = 18.0
        self._margin_bottom = 30.0
        self.setMinimumHeight(height)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)
        for variable in (ra_variable, dec_variable, sky_radius_variable):
            variable.changed.connect(lambda _value: self.update())

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        self.setEnabled(enabled)
        self.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.update()

    def refresh_theme(self) -> None:
        self.update()

    def _plot_box(self) -> tuple[float, float, float, float]:
        return (
            self._margin_left,
            self._margin_top,
            max(self._margin_left + 180.0, self.width() - self._margin_right),
            max(self._margin_top + 100.0, self.height() - self._margin_bottom),
        )

    def _project(self, ra_hours: float, dec_degrees: float) -> tuple[float, float]:
        x0, y0, x1, y1 = self._plot_box()
        x = x0 + ((24.0 - (ra_hours % 24.0)) / 24.0) * (x1 - x0)
        y = y0 + ((90.0 - dec_degrees) / 180.0) * (y1 - y0)
        return x, y

    def _unproject(self, x: float, y: float) -> tuple[float, float]:
        x0, y0, x1, y1 = self._plot_box()
        x = min(x1, max(x0, x))
        y = min(y1, max(y0, y))
        ra = (24.0 - (x - x0) / max(1.0, x1 - x0) * 24.0) % 24.0
        dec = 90.0 - (y - y0) / max(1.0, y1 - y0) * 180.0
        return ra, min(90.0, max(-90.0, dec))

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._enabled and event.button() == Qt.MouseButton.LeftButton:
            self.setFocus()
            self._dragging = True
            self._set_from_pointer(event.position().x(), event.position().y(), True)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._enabled and self._dragging:
            self._set_from_pointer(event.position().x(), event.position().y(), True)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._enabled and self._dragging and event.button() == Qt.MouseButton.LeftButton:
            self._set_from_pointer(event.position().x(), event.position().y(), False)
            self._dragging = False
            if self.release_command:
                self.release_command()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if not self._enabled:
            return
        mapping = {
            Qt.Key.Key_Left: (-0.25, 0.0), Qt.Key.Key_Right: (0.25, 0.0),
            Qt.Key.Key_Up: (0.0, 1.0), Qt.Key.Key_Down: (0.0, -1.0),
        }
        if event.key() in mapping:
            dr, dd = mapping[event.key()]
            self.ra_variable.set((self.ra_variable.get() + dr) % 24.0)
            self.dec_variable.set(min(90.0, max(-90.0, self.dec_variable.get() + dd)))
            if self.release_command:
                self.release_command()
            elif self.command:
                self.command()
            return
        super().keyPressEvent(event)

    def _set_from_pointer(self, x: float, y: float, notify: bool) -> None:
        ra, dec = self._unproject(x, y)
        self.ra_variable.set(ra)
        self.dec_variable.set(dec)
        if notify and self.command:
            self.command()

    @staticmethod
    def _format_ra(hours: float) -> str:
        total_minutes = int(round((hours % 24.0) * 60.0)) % (24 * 60)
        hour, minute = divmod(total_minutes, 60)
        return f"{hour:02d}h {minute:02d}m"

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        night = night_mode_enabled(self)
        enabled = self._enabled
        surface = QColor(NIGHT_BACKGROUND if night else ("#0b1421" if enabled else "#222831"))
        grid = QColor(NIGHT_BORDER if night else ("#30445a" if enabled else "#444b53"))
        text = QColor((NIGHT_TEXT if enabled else NIGHT_MUTED) if night else ("#b9c8d8" if enabled else "#858b92"))
        equator = QColor("#d40000" if night else "#4d8cad")
        ecliptic = QColor("#b50000" if night else "#a77935")
        footprint = QColor("#ff0000" if night else "#f0bd45")
        fill = QColor("#260000" if night else "#14283d")
        fill.setAlpha(100)
        x0, y0, x1, y1 = self._plot_box()
        rect = QRectF(x0, y0, x1-x0, y1-y0)
        painter.fillRect(rect, surface)
        painter.setPen(QPen(grid, 1))
        painter.drawRect(rect)

        # Coverage fill is approximated by declination bands, matching the old widget.
        self._paint_coverage_fill(painter, fill)
        painter.setPen(QPen(grid, 1))
        font = QFont(self.font()); font.setPointSizeF(max(7.5, font.pointSizeF()-1))
        painter.setFont(font)
        for hour in range(0, 25, 3):
            x, _ = self._project(float(hour % 24), 0.0)
            if hour == 24: x = x0
            painter.drawLine(QPointF(x, y0), QPointF(x, y1))
            painter.setPen(text); painter.drawText(QRectF(x-18, y1+5, 36, 18), int(Qt.AlignmentFlag.AlignHCenter), "24h" if hour == 24 else f"{hour}h")
            painter.setPen(QPen(grid, 1))
        for dec in range(-60, 61, 30):
            _, y = self._project(0.0, float(dec))
            painter.drawLine(QPointF(x0, y), QPointF(x1, y))
            painter.setPen(text); painter.drawText(QRectF(0, y-9, x0-5, 18), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), f"{dec:+d}°" if dec else "0°")
            painter.setPen(QPen(grid, 1))

        _, eq_y = self._project(0.0, 0.0)
        painter.setPen(QPen(equator, 2)); painter.drawLine(QPointF(x0, eq_y), QPointF(x1, eq_y))
        self._paint_ecliptic(painter, ecliptic)
        self._paint_coverage_outline(painter, footprint)

        ra = self.ra_variable.get() % 24.0
        dec = min(90.0, max(-90.0, self.dec_variable.get()))
        x, y = self._project(ra, dec)
        painter.setPen(QPen(QColor(NIGHT_BACKGROUND if night else "white"), 2)); painter.setBrush(footprint)
        painter.drawEllipse(QPointF(x, y), 7, 7)
        painter.setPen(QPen(footprint, 1)); painter.drawLine(QPointF(x-12,y), QPointF(x+12,y)); painter.drawLine(QPointF(x,y-12), QPointF(x,y+12))
        painter.setPen(text); bold = QFont(self.font()); bold.setBold(True); painter.setFont(bold)
        painter.drawText(QRectF(x0+7, y0+6, x1-x0-14, 40), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop), f"Zenith  RA {self._format_ra(ra)}   Dec {dec:+.1f}°\nDisplayed radius {self.sky_radius_variable.get():.0f}°")
        painter.setFont(font)
        painter.drawText(QRectF(x0, y1+8, x1-x0, 20), int(Qt.AlignmentFlag.AlignHCenter), "Right ascension increases to the left — drag to place the zenith")

    def _paint_ecliptic(self, painter: QPainter, colour: QColor) -> None:
        ob = math.radians(23.4393); points=[]
        for degree in range(361):
            lon=math.radians(float(degree)); ra=math.atan2(math.cos(ob)*math.sin(lon), math.cos(lon)); dec=math.asin(math.sin(ob)*math.sin(lon))
            points.append(self._project((math.degrees(ra)%360)/15.0, math.degrees(dec)))
        self._paint_wrapped_polyline(painter, points, colour, 1.0)

    def _paint_coverage_fill(self, painter: QPainter, colour: QColor) -> None:
        radius=min(180.0,max(0.0,self.sky_radius_variable.get())); x0,y0,x1,y1=self._plot_box()
        if radius <= .05: return
        if radius >= 179.95:
            painter.fillRect(QRectF(x0+1,y0+1,x1-x0-2,y1-y0-2), colour); return
        ra0=self.ra_variable.get()%24; dec0=math.radians(self.dec_variable.get()); cr=math.cos(math.radians(radius)); bands=70; bh=180/bands
        for i in range(bands):
            dt=90-i*bh; db=dt-bh; dc=math.radians((dt+db)/2); num=cr-math.sin(dc)*math.sin(dec0); den=math.cos(dc)*math.cos(dec0)
            if abs(den)<1e-10:
                if num>0: continue
                half=12.0
            else:
                threshold=num/den
                if threshold>1: continue
                half=12.0 if threshold<=-1 else math.degrees(math.acos(threshold))/15.0
            _,top=self._project(0,dt); _,bottom=self._project(0,db)
            if half>=11.999:
                painter.fillRect(QRectF(x0,top,x1-x0,bottom-top), colour)
            else:
                start=(ra0-half)%24; end=(ra0+half)%24
                intervals=[(start,end)] if start<=end else [(start,24-1e-7),(0,end)]
                for a,b in intervals:
                    xa,_=self._project(a,0); xb,_=self._project(b,0); painter.fillRect(QRectF(min(xa,xb),top,abs(xa-xb),bottom-top), colour)

    def _paint_coverage_outline(self, painter: QPainter, colour: QColor) -> None:
        radius=min(180.0,max(0.0,self.sky_radius_variable.get())); x0,y0,x1,y1=self._plot_box()
        painter.setPen(QPen(colour, 2.2))
        if radius>=179.5:
            painter.drawRect(QRectF(x0+2,y0+2,x1-x0-4,y1-y0-4)); return
        ra0=math.radians((self.ra_variable.get()%24)*15); dec0=math.radians(self.dec_variable.get()); rho=math.radians(radius); pts=[]
        for d in range(361):
            b=math.radians(d); dec=math.asin(math.sin(dec0)*math.cos(rho)+math.cos(dec0)*math.sin(rho)*math.cos(b)); dra=math.atan2(math.sin(b)*math.sin(rho)*math.cos(dec0), math.cos(rho)-math.sin(dec0)*math.sin(dec)); ra=(ra0+dra)%(2*math.pi); pts.append(self._project(math.degrees(ra)/15,math.degrees(dec)))
        self._paint_wrapped_polyline(painter, pts, colour, 2.2)

    def _paint_wrapped_polyline(self, painter: QPainter, points: list[tuple[float,float]], colour: QColor, width: float) -> None:
        x0,_,x1,_=self._plot_box(); threshold=(x1-x0)*.55; path=QPainterPath(); prev=None; started=False
        painter.setPen(QPen(colour,width))
        for x,y in points:
            if prev is None or abs(x-prev)>threshold:
                if started: painter.drawPath(path)
                path=QPainterPath(QPointF(x,y)); started=True
            else: path.lineTo(QPointF(x,y))
            prev=x
        if started: painter.drawPath(path)
