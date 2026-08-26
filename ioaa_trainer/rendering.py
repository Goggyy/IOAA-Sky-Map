"""Matplotlib rendering shared by blind activities and the analysis window."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Iterable
from zoneinfo import ZoneInfo

import numpy as np
from matplotlib.figure import Figure

from .models import Curve, SkyMapModel


@dataclass(frozen=True)
class RenderOptions:
    """Switches controlling which chart layers are visible."""

    show_direction_labels: bool = False
    show_altitude_grid: bool = False
    show_title: bool = False
    show_ecliptic: bool = False
    show_celestial_equator: bool = False
    show_galactic_equator: bool = False
    show_constellation_names: bool = False
    show_constellation_lines: bool = False
    show_star_names: bool = False
    show_coordinate_grid: bool = False
    limiting_magnitude: float | None = None

    @classmethod
    def blind(cls) -> "RenderOptions":
        return cls()


AnswerOverlay = Callable[["SkyMapRenderer", SkyMapModel], None]


class SkyMapRenderer:
    BACKGROUND = "#030711"
    FOREGROUND = "#edf4ff"
    MUTED = "#8fa4be"
    HORIZON = "#6b7f96"
    HORIZONTAL_GRID = "#26394d"
    COORDINATE_GRID = "#40556c"
    CONSTELLATION = "#7898bb"
    ECLIPTIC = "#e6ad53"
    CELESTIAL_EQUATOR = "#5fb5dd"
    GALACTIC_EQUATOR = "#c486d8"
    STAR_LABEL = "#e8eef7"
    ANSWER = "#ffcf4a"

    def __init__(self, figure: Figure) -> None:
        self.figure = figure
        self.axes = figure.add_subplot(111, projection="polar")

    def draw(
        self,
        model: SkyMapModel,
        options: RenderOptions,
        answer_overlay: AnswerOverlay | None = None,
    ) -> None:
        ax = self.axes
        ax.clear()
        ax.set_axis_on()
        self.figure.set_facecolor(self.BACKGROUND)
        ax.set_facecolor(self.BACKGROUND)
        ax.set_theta_zero_location(
            "N",
            offset=float(model.settings.map_rotation_degrees),
        )
        ax.set_theta_direction(-1)
        ax.set_ylim(0.0, 90.0)
        ax.spines["polar"].set_color(self.HORIZON)
        ax.spines["polar"].set_linewidth(0.9)

        self._configure_horizontal_axes(options)

        if options.show_coordinate_grid:
            for curve in model.coordinate_grid:
                self.draw_curve(
                    curve,
                    color=self.COORDINATE_GRID,
                    linewidth=0.48,
                    alpha=0.62,
                    zorder=1,
                )

        if options.show_constellation_lines:
            self.draw_all_constellations(
                model,
                color=self.CONSTELLATION,
                linewidth=0.7,
                alpha=0.58,
                zorder=2,
            )

        if options.show_ecliptic:
            self.draw_curve(
                model.ecliptic,
                color=self.ECLIPTIC,
                linewidth=1.25,
                alpha=0.95,
                zorder=3,
            )
        if options.show_celestial_equator:
            self.draw_curve(
                model.celestial_equator,
                color=self.CELESTIAL_EQUATOR,
                linewidth=1.2,
                alpha=0.95,
                zorder=3,
            )
        if options.show_galactic_equator:
            self.draw_curve(
                model.galactic_equator,
                color=self.GALACTIC_EQUATOR,
                linewidth=1.2,
                alpha=0.95,
                zorder=3,
            )

        display_limit = (
            model.settings.limiting_magnitude
            if options.limiting_magnitude is None
            else min(
                float(options.limiting_magnitude),
                model.settings.limiting_magnitude,
            )
        )
        visible_star_mask = model.stars.magnitude <= display_limit
        visible_magnitudes = model.stars.magnitude[visible_star_mask]
        marker_sizes = np.clip(
            1.15
            * (
                display_limit
                - visible_magnitudes
                + 0.65
            )
            ** 2,
            0.45,
            82.0,
        )
        ax.scatter(
            np.deg2rad(model.stars.azimuth[visible_star_mask]),
            90.0 - model.stars.altitude[visible_star_mask],
            s=marker_sizes,
            color=self.FOREGROUND,
            linewidths=0,
            alpha=0.95,
            zorder=4,
        )

        if options.show_constellation_names:
            for point in model.constellation_labels:
                ax.text(
                    math.radians(point.azimuth),
                    90.0 - point.altitude,
                    point.text,
                    color=self.CONSTELLATION,
                    fontsize=7.0,
                    alpha=0.92,
                    ha="center",
                    va="center",
                    rotation=0,
                    zorder=5,
                    bbox={
                        "facecolor": self.BACKGROUND,
                        "edgecolor": "none",
                        "alpha": 0.54,
                        "pad": 0.6,
                    },
                )

        if options.show_star_names:
            for point in model.named_stars:
                if point.magnitude is not None and point.magnitude > display_limit:
                    continue
                ax.annotate(
                    point.text,
                    xy=(math.radians(point.azimuth), 90.0 - point.altitude),
                    xytext=(4, 3),
                    textcoords="offset points",
                    color=self.STAR_LABEL,
                    fontsize=7.3,
                    alpha=0.96,
                    rotation=0,
                    zorder=6,
                )

        if answer_overlay is not None:
            answer_overlay(self, model)

        if options.show_title:
            observation = model.settings.observation_datetime
            utc_time = observation.astimezone(ZoneInfo("UTC"))
            ax.set_title(
                (
                    f"Sky analysis — {model.settings.latitude:.4f}°, "
                    f"{model.settings.longitude:.4f}°\n"
                    f"UTC {utc_time:%Y-%m-%d %H:%M:%S}"
                ),
                color=self.FOREGROUND,
                fontsize=10.5,
                pad=20,
            )

        self.figure.tight_layout(pad=1.0)

    def _configure_horizontal_axes(self, options: RenderOptions) -> None:
        ax = self.axes
        if options.show_direction_labels:
            ax.set_xticks(np.deg2rad(np.arange(0, 360, 45)))
            ax.set_xticklabels(["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
            ax.tick_params(axis="x", colors=self.MUTED, labelsize=8)
            for label in ax.get_xticklabels():
                label.set_rotation(0)
        else:
            ax.set_xticks([])

        if options.show_altitude_grid:
            ax.set_yticks([15, 30, 45, 60, 75, 90])
            ax.set_yticklabels(["75°", "60°", "45°", "30°", "15°", "0°"])
            ax.set_rlabel_position(22.5)
            ax.tick_params(axis="y", colors=self.MUTED, labelsize=8)
            for label in ax.get_yticklabels():
                label.set_rotation(0)
            ax.grid(True, color=self.HORIZONTAL_GRID, alpha=0.5, linewidth=0.55)
        else:
            ax.set_yticks([])
            ax.grid(False)

    def draw_curve(
        self,
        curve: Curve,
        *,
        color: str,
        linewidth: float,
        alpha: float,
        zorder: int,
    ) -> None:
        for theta, radius in self.visible_segments(curve.altitude, curve.azimuth):
            self.axes.plot(
                theta,
                radius,
                color=color,
                linewidth=linewidth,
                alpha=alpha,
                zorder=zorder,
            )

    def draw_all_constellations(
        self,
        model: SkyMapModel,
        *,
        color: str,
        linewidth: float,
        alpha: float,
        zorder: int,
    ) -> None:
        for edge in model.constellation_edges:
            self._draw_constellation_edge(
                edge.azimuth_1,
                edge.altitude_1,
                edge.azimuth_2,
                edge.altitude_2,
                color=color,
                linewidth=linewidth,
                alpha=alpha,
                zorder=zorder,
            )

    def draw_constellation(
        self,
        model: SkyMapModel,
        abbreviation: str,
        *,
        color: str | None = None,
        linewidth: float = 2.1,
        alpha: float = 1.0,
        zorder: int = 10,
    ) -> None:
        for edge in model.constellation_edges:
            if edge.abbreviation != abbreviation:
                continue
            self._draw_constellation_edge(
                edge.azimuth_1,
                edge.altitude_1,
                edge.azimuth_2,
                edge.altitude_2,
                color=color or self.ANSWER,
                linewidth=linewidth,
                alpha=alpha,
                zorder=zorder,
            )

    def _draw_constellation_edge(
        self,
        azimuth_1: float,
        altitude_1: float,
        azimuth_2: float,
        altitude_2: float,
        *,
        color: str,
        linewidth: float,
        alpha: float,
        zorder: int,
    ) -> None:
        theta = np.unwrap(np.deg2rad([azimuth_1, azimuth_2]))
        radius = [90.0 - altitude_1, 90.0 - altitude_2]
        self.axes.plot(
            theta,
            radius,
            color=color,
            linewidth=linewidth,
            alpha=alpha,
            zorder=zorder,
        )

    @staticmethod
    def visible_segments(
        altitude: np.ndarray,
        azimuth: np.ndarray,
    ) -> Iterable[tuple[np.ndarray, np.ndarray]]:
        altitude = np.asarray(altitude, dtype=float)
        azimuth = np.asarray(azimuth, dtype=float)
        valid = np.isfinite(altitude) & np.isfinite(azimuth) & (altitude >= 0.0)

        start: int | None = None
        for index, is_valid in enumerate(valid):
            if is_valid and start is None:
                start = index
            at_end = index == len(valid) - 1
            if start is not None and ((not is_valid) or at_end):
                stop = index if not is_valid else index + 1
                if stop - start >= 2:
                    theta = np.unwrap(np.deg2rad(azimuth[start:stop]))
                    radius = 90.0 - altitude[start:stop]
                    yield theta, radius
                start = None
