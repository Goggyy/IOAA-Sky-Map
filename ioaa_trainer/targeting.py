"""Geometry helpers for exercises that mark an area or object on the map."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .models import SkyMapModel


@dataclass(frozen=True)
class TargetRegion:
    altitude: float
    azimuth: float
    diameter_points: float


def constellation_target_region(
    model: SkyMapModel,
    abbreviation: str,
) -> TargetRegion | None:
    """Return a robust centre and display-circle size for visible line segments."""
    endpoints: list[tuple[float, float]] = []
    for edge in model.constellation_edges:
        if edge.abbreviation != abbreviation:
            continue
        # Exercises that ask for a visible constellation retain their original
        # above-horizon meaning even when a chart extends below the horizon.
        if edge.altitude_1 <= 0.0 or edge.altitude_2 <= 0.0:
            continue
        endpoints.append((edge.altitude_1, edge.azimuth_1))
        endpoints.append((edge.altitude_2, edge.azimuth_2))

    if not endpoints:
        return None

    # Remove repeated endpoints introduced by neighbouring line segments.
    unique = sorted({(round(alt, 6), round(az, 6)) for alt, az in endpoints})
    altitude = np.deg2rad([item[0] for item in unique])
    azimuth = np.deg2rad([item[1] for item in unique])

    vectors = np.column_stack(
        (
            np.cos(altitude) * np.cos(azimuth),
            np.cos(altitude) * np.sin(azimuth),
            np.sin(altitude),
        )
    )
    centre = vectors.mean(axis=0)
    norm = float(np.linalg.norm(centre))
    if norm < 1e-10:
        return None
    centre /= norm

    centre_alt = math.degrees(math.asin(float(centre[2])))
    centre_az = math.degrees(math.atan2(float(centre[1]), float(centre[0]))) % 360.0

    dots = np.clip(vectors @ centre, -1.0, 1.0)
    separations = np.rad2deg(np.arccos(dots))
    # The 85th percentile avoids one distant endpoint making the ring enormous.
    radius_degrees = max(8.0, float(np.percentile(separations, 85)) + 4.0)
    diameter_points = float(np.clip(radius_degrees * 4.2, 62.0, 142.0))

    return TargetRegion(
        altitude=centre_alt,
        azimuth=centre_az,
        diameter_points=diameter_points,
    )
