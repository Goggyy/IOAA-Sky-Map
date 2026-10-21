"""Matplotlib rendering shared by blind exercises and the analysis window."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Iterable
from zoneinfo import ZoneInfo

import numpy as np
from matplotlib.figure import Figure

from .astronomy import format_local_sidereal_time
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
    show_solar_system_objects: bool = False
    show_solar_system_labels: bool = False
    show_zenith_label: bool = False
    limiting_magnitude: float | None = None
    star_marker_scale: float | None = None

    @classmethod
    def blind(cls) -> "RenderOptions":
        return cls()


AnswerOverlay = Callable[["SkyMapRenderer", SkyMapModel], None]


class SkyMapRenderer:
    # The default study chart is paper-style: black marks on white.
    NORMAL_PALETTE = {
        "BACKGROUND": "#ffffff",
        "FOREGROUND": "#000000",
        "MUTED": "#4f4f4f",
        "HORIZON": "#555555",
        "HORIZONTAL_GRID": "#d2d2d2",
        "COORDINATE_GRID": "#aaaaaa",
        "CONSTELLATION": "#526681",
        "ECLIPTIC": "#9a5a00",
        "CELESTIAL_EQUATOR": "#006c94",
        "GALACTIC_EQUATOR": "#7f3c8d",
        "STAR_LABEL": "#1f1f1f",
        "ANSWER": "#c43a1a",
        "SOLAR_SYSTEM": "#9a5a00",
        "MOON": "#5d6872",
        "SUN": "#a86800",
    }
    INVERTED_PALETTE = {
        "BACKGROUND": "#030711",
        "FOREGROUND": "#edf4ff",
        "MUTED": "#8fa4be",
        "HORIZON": "#6b7f96",
        "HORIZONTAL_GRID": "#26394d",
        "COORDINATE_GRID": "#40556c",
        "CONSTELLATION": "#7898bb",
        "ECLIPTIC": "#e6ad53",
        "CELESTIAL_EQUATOR": "#5fb5dd",
        "GALACTIC_EQUATOR": "#c486d8",
        "STAR_LABEL": "#e8eef7",
        "ANSWER": "#ffcf4a",
        "SOLAR_SYSTEM": "#f4bf5f",
        "MOON": "#d9e2ee",
        "SUN": "#ffd66b",
    }

    NIGHT_PALETTE = {
        "BACKGROUND": "#030000",
        "FOREGROUND": "#ff0000",
        "MUTED": "#a80000",
        "HORIZON": "#8a0000",
        "HORIZONTAL_GRID": "#330000",
        "COORDINATE_GRID": "#4a0000",
        "CONSTELLATION": "#b50000",
        "ECLIPTIC": "#d40000",
        "CELESTIAL_EQUATOR": "#f00000",
        "GALACTIC_EQUATOR": "#9c0000",
        "STAR_LABEL": "#ff0000",
        "ANSWER": "#ff0000",
        "SOLAR_SYSTEM": "#d40000",
        "MOON": "#b50000",
        "SUN": "#ff0000",
    }

    # Class-level defaults preserve compatibility with existing exercise code.
    BACKGROUND = NORMAL_PALETTE["BACKGROUND"]
    FOREGROUND = NORMAL_PALETTE["FOREGROUND"]
    MUTED = NORMAL_PALETTE["MUTED"]
    HORIZON = NORMAL_PALETTE["HORIZON"]
    HORIZONTAL_GRID = NORMAL_PALETTE["HORIZONTAL_GRID"]
    COORDINATE_GRID = NORMAL_PALETTE["COORDINATE_GRID"]
    CONSTELLATION = NORMAL_PALETTE["CONSTELLATION"]
    ECLIPTIC = NORMAL_PALETTE["ECLIPTIC"]
    CELESTIAL_EQUATOR = NORMAL_PALETTE["CELESTIAL_EQUATOR"]
    GALACTIC_EQUATOR = NORMAL_PALETTE["GALACTIC_EQUATOR"]
    STAR_LABEL = NORMAL_PALETTE["STAR_LABEL"]
    ANSWER = NORMAL_PALETTE["ANSWER"]
    SOLAR_SYSTEM = NORMAL_PALETTE["SOLAR_SYSTEM"]
    MOON = NORMAL_PALETTE["MOON"]
    SUN = NORMAL_PALETTE["SUN"]

    def __init__(self, figure: Figure) -> None:
        self.figure = figure
        self.axes = figure.add_subplot(111, projection="polar")
        self._sky_radius_degrees = 90.0
        self.night_mode = False
        self._apply_palette(False)

    def set_night_mode(self, enabled: bool) -> None:
        """Use a black-and-red palette that preserves dark adaptation."""
        self.night_mode = bool(enabled)
        self._apply_palette(False)

    def _apply_palette(self, inverted: bool) -> None:
        if self.night_mode:
            palette = self.NIGHT_PALETTE
        else:
            palette = self.INVERTED_PALETTE if inverted else self.NORMAL_PALETTE
        for name, value in palette.items():
            setattr(self, name, value)

    def draw(
        self,
        model: SkyMapModel,
        options: RenderOptions,
        answer_overlay: AnswerOverlay | None = None,
    ) -> None:
        self._apply_palette(bool(model.settings.inverted_colors))
        self._sky_radius_degrees = float(model.settings.sky_radius_degrees)

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
        # Matplotlib cannot display a polar axis with identical radial
        # limits. Keep a tiny visual radius at the 0° endpoint while all
        # catalogue filtering still uses the exact selected coverage.
        ax.set_ylim(0.0, max(0.25, self._sky_radius_degrees))
        ax.spines["polar"].set_color(self.HORIZON)
        ax.spines["polar"].set_linewidth(0.9)

        self._configure_horizontal_axes(options)
        self._draw_physical_horizon()

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
        marker_scale = (
            model.settings.star_marker_scale
            if options.star_marker_scale is None
            else float(options.star_marker_scale)
        )
        star_radius = 90.0 - model.stars.altitude
        visible_star_mask = (
            (model.stars.magnitude <= display_limit)
            & (star_radius >= 0.0)
            & (star_radius <= self._sky_radius_degrees)
        )
        visible_magnitudes = model.stars.magnitude[visible_star_mask]
        marker_sizes = np.clip(
            max(0.15, float(marker_scale))
            * 1.15
            * (display_limit - visible_magnitudes + 0.65) ** 2,
            0.45,
            82.0,
        )
        ax.scatter(
            np.deg2rad(model.stars.azimuth[visible_star_mask]),
            star_radius[visible_star_mask],
            s=marker_sizes,
            color=self.FOREGROUND,
            linewidths=0,
            alpha=0.95,
            zorder=4,
        )

        if options.show_solar_system_objects or options.show_solar_system_labels:
            self._draw_solar_system_objects(
                model,
                show_labels=options.show_solar_system_labels,
            )

        if options.show_zenith_label:
            ax.annotate(
                "Zenith",
                xy=(0.0, 0.0),
                xytext=(5, 5),
                textcoords="offset points",
                color=self.MUTED,
                fontsize=7.5,
                rotation=0,
                zorder=7,
            )

        if options.show_constellation_names:
            for point in model.constellation_labels:
                radius = 90.0 - point.altitude
                if not 0.0 <= radius <= self._sky_radius_degrees:
                    continue
                ax.text(
                    math.radians(point.azimuth),
                    radius,
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
                radius = 90.0 - point.altitude
                if not 0.0 <= radius <= self._sky_radius_degrees:
                    continue
                ax.annotate(
                    point.text,
                    xy=(math.radians(point.azimuth), radius),
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
                    f"UTC {utc_time:%Y-%m-%d %H:%M:%S}  |  "
                    f"LST {format_local_sidereal_time(model.settings)}"
                ),
                color=self.FOREGROUND,
                fontsize=10.5,
                pad=20,
            )

        self.figure.tight_layout(pad=1.0)

    def _draw_physical_horizon(self) -> None:
        """Draw the true horizon when the chart extends below it."""
        if self._sky_radius_degrees <= 90.0:
            return
        theta = np.linspace(0.0, 2.0 * np.pi, 721)
        self.axes.plot(
            theta,
            np.full_like(theta, 90.0),
            color=self.HORIZON,
            linewidth=0.9,
            alpha=0.9,
            zorder=0,
        )

    def _draw_solar_system_objects(
        self,
        model: SkyMapModel,
        *,
        show_labels: bool,
    ) -> None:
        """Draw Sun, Moon, and planets within the selected chart coverage."""
        marker_by_name = {
            "Sun": ("*", 120.0, self.SUN),
            "Moon": ("o", 58.0, self.MOON),
        }
        for item in model.solar_system_objects:
            radius = 90.0 - item.altitude
            if not 0.0 <= radius <= self._sky_radius_degrees:
                continue
            marker, size, color = marker_by_name.get(
                item.name,
                ("D", 32.0, self.SOLAR_SYSTEM),
            )
            self.axes.scatter(
                [math.radians(item.azimuth)],
                [radius],
                s=[size],
                marker=marker,
                color=color,
                edgecolors=self.BACKGROUND,
                linewidths=0.65,
                zorder=7,
            )
            if show_labels:
                self.axes.annotate(
                    item.name,
                    xy=(math.radians(item.azimuth), radius),
                    xytext=(5, 5),
                    textcoords="offset points",
                    color=color,
                    fontsize=7.5,
                    fontweight="bold",
                    rotation=0,
                    zorder=8,
                    bbox={
                        "facecolor": self.BACKGROUND,
                        "edgecolor": "none",
                        "alpha": 0.68,
                        "pad": 1.0,
                    },
                )

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
            candidate_radii = np.arange(15.0, 181.0, 15.0)
            radii = [
                float(radius)
                for radius in candidate_radii
                if radius <= self._sky_radius_degrees + 1e-9
            ]
            ax.set_yticks(radii)
            ax.set_yticklabels([f"{90.0 - radius:.0f}°" for radius in radii])
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

    def draw_target_circle(
        self,
        altitude: float,
        azimuth: float,
        *,
        diameter_points: float = 82.0,
        color: str | None = None,
        linewidth: float = 2.2,
        alpha: float = 1.0,
        zorder: int = 9,
    ) -> None:
        """Draw a screen-space circle around a question target."""
        self.axes.scatter(
            [math.radians(azimuth)],
            [90.0 - altitude],
            s=[float(diameter_points) ** 2],
            facecolors="none",
            edgecolors=color or self.ANSWER,
            linewidths=linewidth,
            alpha=alpha,
            zorder=zorder,
        )

    def draw_target_point(
        self,
        altitude: float,
        azimuth: float,
        *,
        color: str | None = None,
        size: float = 72.0,
        zorder: int = 11,
    ) -> None:
        """Emphasise one exact star or point after an answer is revealed."""
        self.axes.scatter(
            [math.radians(azimuth)],
            [90.0 - altitude],
            s=[size],
            color=color or self.ANSWER,
            edgecolors=self.BACKGROUND,
            linewidths=0.8,
            zorder=zorder,
        )

    def draw_upright_label(
        self,
        altitude: float,
        azimuth: float,
        text: str,
        *,
        color: str | None = None,
        fontsize: float = 9.0,
        offset_points: tuple[float, float] = (7.0, 7.0),
        zorder: int = 12,
    ) -> None:
        """Add a horizontal label clipped to the circular sky-map area."""
        self.axes.annotate(
            text,
            xy=(math.radians(azimuth), 90.0 - altitude),
            xytext=offset_points,
            textcoords="offset points",
            color=color or self.ANSWER,
            fontsize=fontsize,
            fontweight="bold",
            rotation=0,
            ha="left",
            va="bottom",
            zorder=zorder,
            clip_on=True,
            bbox={
                "facecolor": self.BACKGROUND,
                "edgecolor": "none",
                "alpha": 0.76,
                "pad": 1.5,
            },
        )

    def draw_boundary_label(
        self,
        azimuth: float,
        text: str,
        *,
        color: str | None = None,
        fontsize: float = 9.0,
        radial_gap_degrees: float = 4.0,
        zorder: int = 13,
    ) -> None:
        """Place an upright label just outside the circular sky-map boundary."""
        radius = self._sky_radius_degrees + max(1.0, float(radial_gap_degrees))
        self.axes.text(
            math.radians(azimuth),
            radius,
            text,
            color=color or self.MUTED,
            fontsize=fontsize,
            fontweight="bold",
            ha="center",
            va="center",
            rotation=0,
            zorder=zorder,
            clip_on=False,
        )

    def draw_cardinal_labels(
        self,
        *,
        color: str | None = None,
        zorder: int = 13,
    ) -> None:
        """Label N, E, S, and W just outside the circular sky map."""
        label_color = color or self.MUTED
        for azimuth, label in ((0.0, "N"), (90.0, "E"), (180.0, "S"), (270.0, "W")):
            self.draw_boundary_label(
                azimuth,
                label,
                color=label_color,
                fontsize=10.0,
                radial_gap_degrees=4.0,
                zorder=zorder,
            )

    def draw_local_meridian(
        self,
        *,
        color: str | None = None,
        linewidth: float = 1.8,
        alpha: float = 0.95,
        zorder: int = 8,
    ) -> None:
        """Draw the north-zenith-south local meridian across the chart."""
        line_color = color or self.ANSWER
        radius = np.linspace(0.0, self._sky_radius_degrees, 361)
        for azimuth in (0.0, 180.0):
            self.axes.plot(
                np.full_like(radius, math.radians(azimuth)),
                radius,
                color=line_color,
                linewidth=linewidth,
                alpha=alpha,
                zorder=zorder,
            )

    def draw_answer_note(self, text: str, *, zorder: int = 14) -> None:
        """Compatibility hook for old exercises; answers now live in the side panel.

        Earlier versions drew red answer summaries in the square corners around the
        polar chart.  Those notes could sit outside the circular sky map and obscure
        the interface, so the renderer deliberately no longer paints them.
        """
        del text, zorder

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

    def visible_segments(
        self,
        altitude: np.ndarray,
        azimuth: np.ndarray,
    ) -> Iterable[tuple[np.ndarray, np.ndarray]]:
        altitude = np.asarray(altitude, dtype=float)
        azimuth = np.asarray(azimuth, dtype=float)
        radius = 90.0 - altitude
        valid = (
            np.isfinite(altitude)
            & np.isfinite(azimuth)
            & (radius >= 0.0)
            & (radius <= self._sky_radius_degrees)
        )

        start: int | None = None
        for index, is_valid in enumerate(valid):
            if is_valid and start is None:
                start = index
            at_end = index == len(valid) - 1
            if start is not None and ((not is_valid) or at_end):
                stop = index if not is_valid else index + 1
                if stop - start >= 2:
                    theta = np.unwrap(np.deg2rad(azimuth[start:stop]))
                    segment_radius = radius[start:stop]
                    yield theta, segment_radius
                start = None
