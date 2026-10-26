"""Offline civil time zone lookup and local-time conversion."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from timezonefinder import timezone_at


def zone_for_coordinates(latitude: float, longitude: float) -> ZoneInfo:
    name = timezone_at(lat=latitude, lng=longitude)
    if not name:
        raise ValueError("No time zone found for these coordinates.")
    return ZoneInfo(name)


def local_to_utc(value: datetime, zone: ZoneInfo) -> datetime:
    """Reject nonexistent and ambiguous clock times at daylight-saving changes."""
    first = value.replace(tzinfo=zone, fold=0)
    second = value.replace(tzinfo=zone, fold=1)
    if first.utcoffset() != second.utcoffset():
        first_valid = first.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == value
        second_valid = second.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == value
        if first_valid and second_valid:
            raise ValueError("This local time occurs twice. Choose another time or use UTC.")
        if not first_valid and not second_valid:
            raise ValueError("This local time does not exist. Choose another time or use UTC.")
    return first.astimezone(timezone.utc)
