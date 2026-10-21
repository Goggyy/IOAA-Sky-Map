"""Pure coordinate conversions used by the interactive coordinate-converter tool.

The horizontal convention matches the rest of the trainer: altitude is positive
above the horizon and azimuth is measured from north through east.  Right
ascension and local sidereal time are measured in hours; hour angle is signed
and positive west of the meridian.
"""

from __future__ import annotations

import math
import re


def normalize_hours(hours: float) -> float:
    """Wrap an hour value into the interval [0, 24)."""
    return float(hours) % 24.0


def signed_hour_angle(hours: float) -> float:
    """Wrap an hour angle into [-12, +12)."""
    value = (float(hours) + 12.0) % 24.0 - 12.0
    # Avoid displaying negative zero after round-off.
    return 0.0 if abs(value) < 5e-13 else value


def horizontal_from_equatorial(
    latitude_degrees: float,
    declination_degrees: float,
    hour_angle_hours: float,
) -> tuple[float, float]:
    """Convert Dec/hour angle to altitude/azimuth for a terrestrial latitude.

    Azimuth follows the navigation/IOAA convention used by this program:
    north = 0 deg, east = 90 deg, south = 180 deg, west = 270 deg.
    """
    latitude = _latitude(latitude_degrees)
    declination = _declination(declination_degrees)
    hour_angle = signed_hour_angle(hour_angle_hours) * 15.0

    phi = math.radians(latitude)
    dec = math.radians(declination)
    ha = math.radians(hour_angle)

    sin_alt = (
        math.sin(phi) * math.sin(dec)
        + math.cos(phi) * math.cos(dec) * math.cos(ha)
    )
    sin_alt = _clamp_unit(sin_alt)
    altitude = math.asin(sin_alt)

    # These are cos(alt)*sin(A) and cos(alt)*cos(A), so atan2 remains
    # numerically stable even close to the horizon.
    east_component = -math.cos(dec) * math.sin(ha)
    north_component = (
        math.sin(dec) * math.cos(phi)
        - math.cos(dec) * math.cos(ha) * math.sin(phi)
    )
    if math.hypot(east_component, north_component) < 1e-12:
        # At the zenith/nadir every azimuth represents the same direction.
        azimuth = 0.0
    else:
        azimuth = math.atan2(east_component, north_component)

    return math.degrees(altitude), math.degrees(azimuth) % 360.0


def equatorial_from_horizontal(
    latitude_degrees: float,
    altitude_degrees: float,
    azimuth_degrees: float,
) -> tuple[float, float]:
    """Convert altitude/azimuth to declination and signed hour angle."""
    latitude = _latitude(latitude_degrees)
    altitude = _altitude(altitude_degrees)
    azimuth = float(azimuth_degrees) % 360.0

    phi = math.radians(latitude)
    alt = math.radians(altitude)
    az = math.radians(azimuth)

    sin_dec = (
        math.sin(phi) * math.sin(alt)
        + math.cos(phi) * math.cos(alt) * math.cos(az)
    )
    sin_dec = _clamp_unit(sin_dec)
    declination = math.asin(sin_dec)

    # Components proportional to cos(dec)*sin(H) and cos(dec)*cos(H).
    sin_ha_component = -math.cos(alt) * math.sin(az)
    cos_ha_component = (
        math.cos(phi) * math.sin(alt)
        - math.sin(phi) * math.cos(alt) * math.cos(az)
    )
    if math.hypot(sin_ha_component, cos_ha_component) < 1e-12:
        # At a celestial pole the hour angle has no geometrical meaning.
        hour_angle = 0.0
    else:
        hour_angle = math.atan2(sin_ha_component, cos_ha_component)

    return math.degrees(declination), signed_hour_angle(math.degrees(hour_angle) / 15.0)


def hour_angle_from_lst_ra(lst_hours: float, ra_hours: float) -> float:
    """Return signed hour angle H = LST - RA."""
    return signed_hour_angle(float(lst_hours) - float(ra_hours))


def lst_from_ra_hour_angle(ra_hours: float, hour_angle_hours: float) -> float:
    """Return local sidereal time from RA + hour angle."""
    return normalize_hours(float(ra_hours) + float(hour_angle_hours))


def ra_from_lst_hour_angle(lst_hours: float, hour_angle_hours: float) -> float:
    """Return right ascension from LST - hour angle."""
    return normalize_hours(float(lst_hours) - float(hour_angle_hours))


def parse_hours(text: str, *, signed: bool = False) -> float:
    """Parse decimal hours or H:M:S text.

    Unsigned quantities (RA and LST) are required to be in [0, 24] before
    wrapping 24:00:00 to 0 h.  Signed hour angle accepts -12 to +12 hours.
    """
    value = _parse_sexagesimal(text)
    if signed:
        if not -12.0 <= value <= 12.0:
            raise ValueError("Hour angle must be between -12 h and +12 h.")
        return signed_hour_angle(value)
    if not 0.0 <= value <= 24.0:
        raise ValueError("RA/LST must be between 0 h and 24 h.")
    return normalize_hours(value)


def parse_degrees(
    text: str,
    *,
    minimum: float,
    maximum: float,
    label: str,
    wrap_360: bool = False,
) -> float:
    """Parse decimal degrees or D:M:S text with a range check."""
    value = _parse_sexagesimal(text)
    if wrap_360 and math.isclose(value, 360.0, abs_tol=1e-12):
        return 0.0
    if not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum:g}° and {maximum:g}°.")
    return value % 360.0 if wrap_360 else value


def format_hours(hours: float, *, signed: bool = False, precision: int = 1) -> str:
    """Format hours as HH:MM:SS.s (or signed ±HH:MM:SS.s)."""
    if signed:
        value = signed_hour_angle(hours)
        sign = "−" if value < 0 else "+"
        value = abs(value)
        return sign + _format_sexagesimal(value, 12.0, precision)
    return _format_sexagesimal(normalize_hours(hours), 24.0, precision)


def format_degrees(
    degrees: float,
    *,
    signed: bool = True,
    precision: int = 1,
) -> str:
    """Format degrees as ±DD:MM:SS.s or unsigned DDD:MM:SS.s."""
    value = float(degrees)
    if signed:
        sign = "−" if value < 0 else "+"
        return sign + _format_sexagesimal(abs(value), 360.0, precision)
    return _format_sexagesimal(value % 360.0, 360.0, precision)


def _parse_sexagesimal(text: str) -> float:
    raw = text.strip().replace("−", "-")
    if not raw:
        raise ValueError("Enter a value.")

    # Accept familiar forms such as 12:34:56, 12 34 56, 12h34m56s,
    # and 12°34'56\" in addition to plain decimal values.
    cleaned = raw.lower()
    cleaned = cleaned.replace("hours", "h").replace("hour", "h")
    cleaned = cleaned.replace("degrees", "d").replace("degree", "d")
    cleaned = re.sub(r"[hHdD°mM'′sS\"″]", ":", cleaned)
    cleaned = re.sub(r"\s+", ":", cleaned)
    cleaned = re.sub(r":+", ":", cleaned).strip(":")

    if ":" not in cleaned:
        try:
            return float(cleaned)
        except ValueError as error:
            raise ValueError(f"Could not read '{text}' as a number.") from error

    parts = cleaned.split(":")
    if len(parts) > 3 or any(part == "" for part in parts):
        raise ValueError(f"Could not read '{text}' as a sexagesimal value.")
    try:
        first = float(parts[0])
        minutes = float(parts[1]) if len(parts) >= 2 else 0.0
        seconds = float(parts[2]) if len(parts) >= 3 else 0.0
    except ValueError as error:
        raise ValueError(f"Could not read '{text}' as a sexagesimal value.") from error
    if minutes < 0 or minutes >= 60 or seconds < 0 or seconds >= 60:
        raise ValueError("Minutes and seconds must be between 0 and 60.")
    sign = -1.0 if first < 0 or raw.lstrip().startswith(("-", "−")) else 1.0
    return sign * (abs(first) + minutes / 60.0 + seconds / 3600.0)


def _format_sexagesimal(value: float, wrap_at: float, precision: int) -> str:
    factor = 10**precision
    total_seconds = round(float(value) * 3600.0 * factor) / factor
    wrap_seconds = wrap_at * 3600.0
    if total_seconds >= wrap_seconds - 0.5 / factor:
        total_seconds = 0.0
    units = int(total_seconds // 3600.0)
    remainder = total_seconds - units * 3600.0
    minutes = int(remainder // 60.0)
    seconds = remainder - minutes * 60.0
    width = 2 + (1 if precision else 0) + precision
    return f"{units:02d}:{minutes:02d}:{seconds:0{width}.{precision}f}"


def _clamp_unit(value: float) -> float:
    return min(1.0, max(-1.0, float(value)))


def _latitude(value: float) -> float:
    value = float(value)
    if not -90.0 <= value <= 90.0:
        raise ValueError("Latitude must be between -90° and +90°.")
    return value


def _declination(value: float) -> float:
    value = float(value)
    if not -90.0 <= value <= 90.0:
        raise ValueError("Declination must be between -90° and +90°.")
    return value


def _altitude(value: float) -> float:
    value = float(value)
    if not -90.0 <= value <= 90.0:
        raise ValueError("Altitude must be between -90° and +90°.")
    return value
