"""Data models shared by the IOAA sky-training application."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np


@dataclass(frozen=True)
class MapSettings:
    """Observer and rendering settings for one generated sky."""

    latitude: float
    longitude: float
    observation_datetime: datetime
    limiting_magnitude: float = 6.5
    map_rotation_degrees: float = 0.0


@dataclass(frozen=True)
class StarLayer:
    hip: np.ndarray
    altitude: np.ndarray
    azimuth: np.ndarray
    magnitude: np.ndarray


@dataclass(frozen=True)
class LabelPoint:
    text: str
    altitude: float
    azimuth: float
    magnitude: float | None = None


@dataclass(frozen=True)
class ConstellationEdge:
    abbreviation: str
    altitude_1: float
    azimuth_1: float
    altitude_2: float
    azimuth_2: float


@dataclass(frozen=True)
class Curve:
    altitude: np.ndarray
    azimuth: np.ndarray


@dataclass(frozen=True)
class SkyMapModel:
    settings: MapSettings
    stars: StarLayer
    named_stars: tuple[LabelPoint, ...]
    constellation_edges: tuple[ConstellationEdge, ...]
    constellation_labels: tuple[LabelPoint, ...]
    constellation_names: dict[str, str]
    ecliptic: Curve
    celestial_equator: Curve
    galactic_equator: Curve
    coordinate_grid: tuple[Curve, ...]

    def visible_constellation_edge_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for edge in self.constellation_edges:
            counts[edge.abbreviation] = counts.get(edge.abbreviation, 0) + 1
        return counts


@dataclass(frozen=True)
class ActivityQuestion:
    """A prompt plus activity-specific answer data."""

    prompt: str
    answer_text: str
    payload: Any = None


@dataclass(frozen=True)
class QuestionBundle:
    """Everything needed to display and analyse one random question."""

    seed: int
    model: SkyMapModel
    question: ActivityQuestion
