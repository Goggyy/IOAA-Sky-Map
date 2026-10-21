"""Standalone analytical sky-map generator tool."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ioaa_trainer.tool_api import SkyTool


class SkyMapGeneratorTool(SkyTool):
    tool_id = "sky_map_generator"
    sort_order = 1
    title = "Sky Map Generator"
    description = (
        "Generate and analyse a sky using UTC, LST, MJD, or a directly chosen "
        "zenith, with reference layers and PNG export."
    )


TOOL_CLASS = SkyMapGeneratorTool


def run_tool() -> int:
    # Import lazily so the launcher can discover tool metadata without loading
    # the astronomy and Matplotlib stack until the user opens the tool.
    from ioaa_trainer.generator_ui import run_generator

    return run_generator()


if __name__ == "__main__":
    raise SystemExit(run_tool())
