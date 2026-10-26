"""Standalone equatorial / horizontal coordinate-converter tool."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ioaa_trainer.tool_api import SkyTool


class CoordinateConverterTool(SkyTool):
    tool_id = "coordinate_converter"
    sort_order = 2
    title = "Coordinate Converter"
    description = (
        "Guided RA/Dec ↔ Alt/Az conversion with latitude, local sidereal "
        "time and hour-angle relationships."
    )


TOOL_CLASS = CoordinateConverterTool


def create_widget():
    """Create the embeddable tool view used by the main launcher."""
    from ioaa_trainer.coordinate_converter_ui import CoordinateConverterApplication

    return CoordinateConverterApplication()


def run_tool() -> int:
    from ioaa_trainer.coordinate_converter_ui import run_coordinate_converter

    return run_coordinate_converter()


if __name__ == "__main__":
    raise SystemExit(run_tool())
