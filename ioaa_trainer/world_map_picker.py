"""Compact, offline world map for choosing observer coordinates."""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QWidget


def _land_polygons() -> list[list[tuple[float, float]]]:
    source = Path(__file__).with_name("ne_110m_land.geojson")
    features = json.loads(source.read_text(encoding="utf-8"))["features"]
    polygons = []
    for feature in features:
        geometry = feature["geometry"]
        groups = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        for group in groups:
            polygons.extend([[(float(x), float(y)) for x, y in ring] for ring in group[:1]])
    return polygons


LAND_POLYGONS = _land_polygons()


class WorldMapPicker(QWidget):
    coordinateSelected = pyqtSignal(float, float)

    def __init__(self, *, expanded: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.latitude = 0.0
        self.longitude = 0.0
        self.setMinimumHeight(360 if expanded else 145)
        self.setMinimumWidth(560 if expanded else 250)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setToolTip("Click to select latitude and longitude")

    def set_coordinates(self, latitude: float, longitude: float) -> None:
        self.latitude, self.longitude = latitude, longitude
        self.update()

    def _rect(self):
        margin = 7.0
        return self.rect().adjusted(int(margin), int(margin), -int(margin), -int(margin))

    def _point(self, longitude: float, latitude: float) -> QPointF:
        rect = self._rect()
        return QPointF(rect.left() + (longitude + 180.0) / 360.0 * rect.width(), rect.top() + (90.0 - latitude) / 180.0 * rect.height())

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self._rect()
        painter.fillRect(rect, QColor("#18304a"))
        painter.save()
        painter.setClipRect(rect)
        painter.setPen(QPen(QColor("#7fa0b0"), 0.5))
        painter.setBrush(QColor("#9bb3a2"))
        for polygon in LAND_POLYGONS:
            if len(polygon) < 3:
                continue
            path = QPainterPath(self._point(*polygon[0]))
            for longitude, latitude in polygon[1:]:
                path.lineTo(self._point(longitude, latitude))
            path.closeSubpath()
            painter.drawPath(path)
        point = self._point(self.longitude, self.latitude)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.setBrush(QColor("#f04e37"))
        painter.drawEllipse(point, 5, 5)
        painter.restore()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._rect().contains(event.position().toPoint()):
            rect = self._rect()
            longitude = max(-180.0, min(180.0, (event.position().x() - rect.left()) / rect.width() * 360.0 - 180.0))
            latitude = max(-90.0, min(90.0, 90.0 - (event.position().y() - rect.top()) / rect.height() * 180.0))
            self.set_coordinates(latitude, longitude)
            self.coordinateSelected.emit(latitude, longitude)
        super().mousePressEvent(event)


class ExpandedWorldMap(QDialog):
    def __init__(self, latitude: float, longitude: float, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Choose location")
        self.resize(800, 450)
        layout = QVBoxLayout(self)
        self.map = WorldMapPicker(expanded=True)
        self.map.set_coordinates(latitude, longitude)
        layout.addWidget(self.map)
