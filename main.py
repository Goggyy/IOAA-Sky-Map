"""Launcher for all automatically discovered IOAA sky-training activities."""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk
from types import ModuleType
from typing import Type

from ioaa_trainer.activity_api import SkyActivity

PROJECT_ROOT = Path(__file__).resolve().parent
ACTIVITIES_DIRECTORY = PROJECT_ROOT / "activities"


@dataclass(frozen=True)
class DiscoveredActivity:
    module: ModuleType
    activity_class: Type[SkyActivity]
    file_path: Path

    @property
    def instance(self) -> SkyActivity:
        return self.activity_class()


def discover_activities() -> list[DiscoveredActivity]:
    activities: list[DiscoveredActivity] = []
    for file_path in sorted(ACTIVITIES_DIRECTORY.glob("activity_*.py")):
        module_name = f"activities.{file_path.stem}"
        module = importlib.import_module(module_name)
        activity_class = getattr(module, "ACTIVITY_CLASS", None)
        if (
            not isinstance(activity_class, type)
            or not issubclass(activity_class, SkyActivity)
        ):
            continue
        activities.append(
            DiscoveredActivity(
                module=module,
                activity_class=activity_class,
                file_path=file_path,
            )
        )
    activities.sort(key=lambda item: item.instance.title)
    return activities


class Launcher(tk.Tk):
    def __init__(self, activities: list[DiscoveredActivity]) -> None:
        super().__init__()
        self.activities = activities
        self.title("IOAA Blind Sky Trainer")
        self.geometry("640x520")
        self.minsize(520, 400)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self, padding=24)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            text="IOAA Blind Sky Trainer",
            font=("TkDefaultFont", 18, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            frame,
            text=(
                "Choose an activity. Each activity opens as an independent program "
                "and generates a random hidden location and UTC time."
            ),
            wraplength=560,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(6, 18))

        activity_frame = ttk.LabelFrame(frame, text="Activities", padding=12)
        activity_frame.grid(row=2, column=0, sticky="nsew")
        activity_frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        if not self.activities:
            ttk.Label(activity_frame, text="No activity modules were found.").grid(
                row=0,
                column=0,
                sticky="w",
            )
        else:
            for row, discovered in enumerate(self.activities):
                activity = discovered.instance
                item = ttk.Frame(activity_frame)
                item.grid(row=row, column=0, sticky="ew", pady=(0 if row == 0 else 10, 0))
                item.columnconfigure(0, weight=1)
                ttk.Label(
                    item,
                    text=activity.title,
                    font=("TkDefaultFont", 11, "bold"),
                ).grid(row=0, column=0, sticky="w")
                ttk.Label(
                    item,
                    text=activity.description,
                    wraplength=430,
                    justify="left",
                ).grid(row=1, column=0, sticky="ew", pady=(2, 0))
                ttk.Button(
                    item,
                    text="Open",
                    command=lambda selected=discovered: self._launch(selected),
                ).grid(row=0, column=1, rowspan=2, sticky="e", padx=(12, 0))

        ttk.Label(
            frame,
            text=(
                "First use requires internet access to cache the Hipparcos catalogue "
                "and constellation line data."
            ),
            wraplength=560,
            justify="left",
        ).grid(row=3, column=0, sticky="ew", pady=(18, 0))

    def _launch(self, discovered: DiscoveredActivity) -> None:
        try:
            subprocess.Popen(
                [sys.executable, str(discovered.file_path)],
                cwd=str(PROJECT_ROOT),
            )
        except OSError as error:
            messagebox.showerror("Could not launch activity", str(error), parent=self)


def dependency_check(activities: list[DiscoveredActivity]) -> int:
    print("Python:", sys.version.split()[0])
    print("Discovered activities:")
    for discovered in activities:
        print(" -", discovered.instance.title, "->", discovered.file_path.name)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="check imports and activity discovery without opening a window",
    )
    args = parser.parse_args()

    activities = discover_activities()
    if args.check:
        return dependency_check(activities)

    app = Launcher(activities)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
