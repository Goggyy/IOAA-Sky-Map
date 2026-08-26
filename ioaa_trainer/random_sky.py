"""Random observer/time generation for blind sky questions."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .models import MapSettings


@dataclass(frozen=True)
class RandomSkyConfig:
    start: datetime = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end: datetime = datetime(2035, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    limiting_magnitude: float = 6.5


class RandomSkyGenerator:
    """Generate random locations, UTC times, and chart orientations."""

    def __init__(self, config: RandomSkyConfig | None = None) -> None:
        self.config = config or RandomSkyConfig()
        if self.config.end <= self.config.start:
            raise ValueError("Random sky end time must be after start time.")

    def generate(self, rng: random.Random) -> MapSettings:
        # Uniform latitude in degrees requires uniform sin(latitude), not a
        # uniform latitude angle, otherwise polar regions are over-sampled.
        latitude = math.degrees(math.asin(rng.uniform(-1.0, 1.0)))
        longitude = rng.uniform(-180.0, 180.0)

        duration_seconds = int((self.config.end - self.config.start).total_seconds())
        observation_datetime = self.config.start + timedelta(
            seconds=rng.randrange(duration_seconds + 1)
        )
        map_rotation_degrees = rng.uniform(0.0, 360.0)
        return MapSettings(
            latitude=latitude,
            longitude=longitude,
            observation_datetime=observation_datetime,
            limiting_magnitude=self.config.limiting_magnitude,
            map_rotation_degrees=map_rotation_degrees,
        )
