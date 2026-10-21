"""Minimal interface implemented by each independently runnable trainer tool."""

from __future__ import annotations

from abc import ABC


class SkyTool(ABC):
    """Metadata shared by tools discovered automatically by the launcher."""

    tool_id = "tool"
    title = "Sky tool"
    description = ""
