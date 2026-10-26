"""Legacy direct launcher for the combined constellation exercise."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from activities.activity_constellation import ConstellationActivity
from ioaa_trainer.activity_ui import run_activity


class ZodiacConstellationActivity(ConstellationActivity):
    """Backward-compatible zodiac-only direct entry point."""

    activity_id = "zodiac_constellation"
    title = "Find Zodiac"
    def __init__(self) -> None:
        self.set_option("constellation_set", "zodiac")


LEGACY_ACTIVITY_CLASS = ZodiacConstellationActivity


if __name__ == "__main__":
    raise SystemExit(run_activity(LEGACY_ACTIVITY_CLASS()))
