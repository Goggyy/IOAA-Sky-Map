"""Random or constrained observer/time generation for training questions."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .generation_settings import GenerationSettings
from .models import MapSettings


@dataclass(frozen=True)
class RandomSkyConfig:
    start: datetime = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end: datetime = datetime(2035, 12, 31, 23, 59, 59, tzinfo=timezone.utc)


class RandomSkyGenerator:
    """Generate locations, UTC times, and chart orientations.

    Coordinates and time can independently be random or fixed through the
    persistent generation settings selected on the launcher.
    """

    def __init__(
        self,
        config: RandomSkyConfig | None = None,
        generation_settings: GenerationSettings | None = None,
    ) -> None:
        self.config = config or RandomSkyConfig()
        self.generation_settings = (
            generation_settings or GenerationSettings()
        ).validated()
        if self.config.end <= self.config.start:
            raise ValueError("Random sky end time must be after start time.")

    def generate(self, rng: random.Random) -> MapSettings:
        generation = self.generation_settings

        if generation.coordinate_mode == "fixed":
            latitude = float(generation.fixed_latitude)
            longitude = float(generation.fixed_longitude)
        else:
            # Uniform latitude in degrees requires uniform sin(latitude), not a
            # uniform latitude angle, otherwise polar regions are over-sampled.
            latitude = math.degrees(math.asin(rng.uniform(-1.0, 1.0)))
            longitude = rng.uniform(-180.0, 180.0)

        if generation.time_mode != "random":
            observation_datetime = generation.resolved_datetime(longitude)
        else:
            duration_seconds = int(
                (self.config.end - self.config.start).total_seconds()
            )
            observation_datetime = self.config.start + timedelta(
                seconds=rng.randrange(duration_seconds + 1)
            )

        map_rotation_degrees = (
            rng.uniform(0.0, 360.0) if generation.enable_map_rotation else 0.0
        )
        return MapSettings(
            latitude=latitude,
            longitude=longitude,
            observation_datetime=observation_datetime,
            limiting_magnitude=float(generation.faintest_visible_magnitude),
            map_rotation_degrees=map_rotation_degrees,
            include_solar_system_objects=(
                generation.include_solar_system_objects
            ),
            inverted_colors=bool(generation.inverted_colors),
            sky_radius_degrees=float(generation.sky_radius_degrees),
            star_marker_scale=float(generation.star_marker_scale),
        )
