"""Persistent settings controlling random skies used by all exercises."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .time_utils import (
    datetime_for_local_sidereal_time,
    datetime_from_mjd,
    parse_clock_hours,
)

SETTINGS_DIRECTORY = Path.home() / ".ioaa_sky_trainer"
SETTINGS_FILE = SETTINGS_DIRECTORY / "generation_settings.json"


@dataclass(frozen=True)
class GenerationSettings:
    """User-selectable constraints and view settings for exercise skies.

    Fixed UTC, LST, and MJD values are all supported. For an LST constraint,
    the saved UTC date and the generated/fixed longitude determine the UTC
    instant used for the map.
    """

    settings_version: int = 3
    include_solar_system_objects: bool = False
    coordinate_mode: str = "random"
    fixed_latitude: float = -36.8485
    fixed_longitude: float = 174.7633
    time_mode: str = "random"
    fixed_utc_datetime: str = "2026-08-04T00:00:00+00:00"
    fixed_lst_date: str = "2026-08-04"
    fixed_lst_time: str = "12:00:00"
    fixed_mjd: float = 61256.0
    inverted_colors: bool = False
    night_mode: bool = True
    sky_radius_degrees: float = 90.0
    faintest_visible_magnitude: float = 6.5
    star_marker_scale: float = 1.0
    enable_map_rotation: bool = True

    def validated(self) -> "GenerationSettings":
        coordinate_mode = self.coordinate_mode
        time_mode = "fixed_utc" if self.time_mode == "fixed" else self.time_mode
        if coordinate_mode not in {"random", "fixed"}:
            raise ValueError("Coordinate mode must be 'random' or 'fixed'.")
        if time_mode not in {"random", "fixed_utc", "fixed_lst", "fixed_mjd"}:
            raise ValueError(
                "Time mode must be random, fixed UTC, fixed LST, or fixed MJD."
            )
        if not -90.0 <= float(self.fixed_latitude) <= 90.0:
            raise ValueError("Latitude must be between -90 and +90 degrees.")
        if not -180.0 <= float(self.fixed_longitude) <= 180.0:
            raise ValueError("Longitude must be between -180 and +180 degrees.")
        if not 0.0 <= float(self.sky_radius_degrees) <= 180.0:
            raise ValueError(
                "Sky coverage must be between 0° and 180° from the zenith."
            )
        if not -1.5 <= float(self.faintest_visible_magnitude) <= 8.0:
            raise ValueError(
                "Faintest visible magnitude must be between -1.5 and 8.0."
            )
        if not 0.45 <= float(self.star_marker_scale) <= 2.0:
            raise ValueError("Star marker scale must be between 0.45 and 2.0.")

        if time_mode == "fixed_utc":
            self.fixed_datetime()
        elif time_mode == "fixed_lst":
            parse_clock_hours(self.fixed_lst_time)
            datetime.strptime(self.fixed_lst_date.strip(), "%Y-%m-%d")
        elif time_mode == "fixed_mjd":
            datetime_from_mjd(self.fixed_mjd)
        return self

    def fixed_datetime(self) -> datetime:
        """Return the stored fixed UTC date/time (legacy-compatible helper)."""
        text = self.fixed_utc_datetime.strip().replace("Z", "+00:00")
        try:
            value = datetime.fromisoformat(text)
        except ValueError as error:
            raise ValueError(
                "Fixed UTC time must be an ISO date/time such as "
                "2026-08-04T22:00:00+00:00."
            ) from error
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def resolved_datetime(self, longitude_degrees: float) -> datetime:
        """Resolve the selected fixed time form into one UTC datetime."""
        time_mode = "fixed_utc" if self.time_mode == "fixed" else self.time_mode
        if time_mode == "fixed_utc":
            return self.fixed_datetime()
        if time_mode == "fixed_mjd":
            return datetime_from_mjd(self.fixed_mjd)
        if time_mode == "fixed_lst":
            return datetime_for_local_sidereal_time(
                self.fixed_lst_date,
                parse_clock_hours(self.fixed_lst_time),
                longitude_degrees,
            )
        raise ValueError("Random time mode does not resolve to a fixed datetime.")

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any]) -> "GenerationSettings":
        allowed = {field_name for field_name in cls.__dataclass_fields__}
        values = {key: value for key, value in mapping.items() if key in allowed}
        if values.get("time_mode") == "fixed":
            values["time_mode"] = "fixed_utc"
        version = int(mapping.get("settings_version", 1))
        # Version 2 changes the exercise default to random map orientation.
        if version < 2:
            values["enable_map_rotation"] = True
        # Version 3 adds the red-only observing interface.
        if version < 3:
            values["night_mode"] = False
        values["settings_version"] = 3
        return cls(**values).validated()


def load_generation_settings(path: Path = SETTINGS_FILE) -> GenerationSettings:
    """Load settings, falling back safely to defaults when unavailable."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Settings file must contain a JSON object.")
        return GenerationSettings.from_mapping(payload)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return GenerationSettings()


def save_generation_settings(
    settings: GenerationSettings,
    path: Path = SETTINGS_FILE,
) -> None:
    validated = settings.validated()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(asdict(validated), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary_path.replace(path)
