"""Conversions between UTC, MJD, and local sidereal time input forms."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

SIDEREAL_RATE = 1.00273790935
UNIX_EPOCH_MJD = 40587.0


def parse_clock_hours(text: str) -> float:
    """Parse decimal hours or HH:MM[:SS] into the range 0 <= h < 24."""
    value = text.strip()
    if not value:
        raise ValueError("A sidereal time is required.")
    if ":" not in value:
        try:
            hours = float(value)
        except ValueError as error:
            raise ValueError("Use decimal hours or HH:MM:SS for LST.") from error
    else:
        parts = value.split(":")
        if len(parts) not in {2, 3}:
            raise ValueError("Use HH:MM or HH:MM:SS for LST.")
        try:
            hours_part = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2]) if len(parts) == 3 else 0.0
        except ValueError as error:
            raise ValueError("Use numeric HH:MM:SS values for LST.") from error
        if not 0.0 <= minutes < 60.0 or not 0.0 <= seconds < 60.0:
            raise ValueError("LST minutes and seconds must be below 60.")
        hours = hours_part + minutes / 60.0 + seconds / 3600.0
    if not 0.0 <= hours < 24.0:
        raise ValueError("LST must be between 00:00:00 and 23:59:59.")
    return hours


def format_clock_hours(hours: float) -> str:
    """Format decimal hours as HH:MM:SS."""
    total_seconds = int(round((float(hours) % 24.0) * 3600.0)) % (24 * 3600)
    hour, remainder = divmod(total_seconds, 3600)
    minute, second = divmod(remainder, 60)
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def datetime_from_mjd(mjd: float) -> datetime:
    """Convert a UTC Modified Julian Date to an aware datetime."""
    try:
        value = float(mjd)
    except (TypeError, ValueError) as error:
        raise ValueError("MJD must be a number.") from error
    if not 0.0 <= value <= 200000.0:
        raise ValueError("MJD is outside the supported range 0 to 200000.")
    try:
        from astropy.time import Time

        return Time(value, format="mjd", scale="utc").to_datetime(
            timezone=timezone.utc
        )
    except ImportError:
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        return epoch + timedelta(days=value - UNIX_EPOCH_MJD)


def mjd_from_datetime(value: datetime) -> float:
    """Convert an aware datetime to UTC Modified Julian Date."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    utc = value.astimezone(timezone.utc)
    try:
        from astropy.time import Time

        return float(Time(utc).utc.mjd)
    except ImportError:
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        return UNIX_EPOCH_MJD + (utc - epoch).total_seconds() / 86400.0


def local_sidereal_time_hours(value: datetime, longitude_degrees: float) -> float:
    """Return apparent LST when Astropy is available, otherwise mean LST.

    The fallback is sufficiently accurate for input validation and keeps this
    utility independently testable. Normal application runs use Astropy.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    try:
        from astropy import units as u
        from astropy.time import Time

        angle = Time(value).sidereal_time(
            "apparent",
            longitude=float(longitude_degrees) * u.deg,
        )
        return float(angle.hour % 24.0)
    except ImportError:
        jd = mjd_from_datetime(value) + 2400000.5
        t = (jd - 2451545.0) / 36525.0
        gmst_degrees = (
            280.46061837
            + 360.98564736629 * (jd - 2451545.0)
            + 0.000387933 * t * t
            - t * t * t / 38710000.0
        )
        return ((gmst_degrees + float(longitude_degrees)) / 15.0) % 24.0


def datetime_for_local_sidereal_time(
    utc_date: str | date,
    lst_hours: float,
    longitude_degrees: float,
) -> datetime:
    """Find the UTC instant on a date that has the requested apparent LST."""
    if isinstance(utc_date, str):
        try:
            parsed_date = datetime.strptime(utc_date.strip(), "%Y-%m-%d").date()
        except ValueError as error:
            raise ValueError("LST reference date must use YYYY-MM-DD.") from error
    else:
        parsed_date = utc_date

    target = float(lst_hours) % 24.0
    start = datetime.combine(parsed_date, datetime.min.time(), tzinfo=timezone.utc)
    start_lst = local_sidereal_time_hours(start, longitude_degrees)
    positive_sidereal_delta = (target - start_lst) % 24.0
    candidate = start + timedelta(hours=positive_sidereal_delta / SIDEREAL_RATE)

    for _ in range(6):
        current = local_sidereal_time_hours(candidate, longitude_degrees)
        signed_error = ((target - current + 12.0) % 24.0) - 12.0
        candidate += timedelta(hours=signed_error / SIDEREAL_RATE)
        if abs(signed_error) < 1e-8:
            break
    return candidate.astimezone(timezone.utc)
