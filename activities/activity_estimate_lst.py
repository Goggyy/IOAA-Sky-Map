"""Exercise 8: estimate local sidereal time from the local meridian."""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import astropy.units as u
from astropy.coordinates import AltAz, EarthLocation, ICRS, SkyCoord
from astropy.time import Time

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ioaa_trainer.activity_api import QuestionUnavailable, SkyActivity
from ioaa_trainer.activity_ui import run_activity
from ioaa_trainer.astronomy import format_local_sidereal_time, local_sidereal_time_hours
from ioaa_trainer.models import ActivityQuestion, SkyMapModel
from ioaa_trainer.rendering import SkyMapRenderer


def _wrap_hours(hours: float) -> float:
    """Wrap an hour difference to the interval [-12, +12)."""
    return (float(hours) + 12.0) % 24.0 - 12.0


def _format_ra(hours: float) -> str:
    total_minutes = int(round((float(hours) % 24.0) * 60.0)) % (24 * 60)
    h, m = divmod(total_minutes, 60)
    return f"{h:02d}h {m:02d}m"


class EstimateLSTActivity(SkyActivity):
    activity_id = "estimate_lst"
    title = "Exercise 8 — Estimate the LST"
    description = (
        "Estimate local sidereal time from the star field. The local meridian is "
        "drawn on the question chart; the solution gives the true LST and nearby "
        "bright reference stars with their right ascensions."
    )
    maximum_reference_hour_angle = 2.5
    minimum_reference_altitude = 3.0
    maximum_reference_count = 3
    relevance_window_hours = 0.65

    def create_question(
        self,
        model: SkyMapModel,
        rng: random.Random,
    ) -> ActivityQuestion:
        del rng
        lst_hours = local_sidereal_time_hours(model.settings)
        references = self._reference_stars(model, lst_hours)
        if not references:
            raise QuestionUnavailable("no named bright reference star lies near the upper meridian")

        reference_text = "; ".join(
            f"{item['name']} (RA {item['ra_text']})" for item in references
        )
        reference_label = (
            "Useful upper-meridian reference"
            if len(references) == 1
            else "Useful upper-meridian references"
        )
        return ActivityQuestion(
            prompt=(
                "Estimate the local sidereal time (LST) from this sky map. The local "
                "meridian is drawn in. Use stars or familiar patterns near the meridian "
                "whose right ascensions you know."
            ),
            answer_text=(
                f"Actual apparent LST: {format_local_sidereal_time(model.settings)}. "
                f"{reference_label}: {reference_text}. An object on the "
                "upper meridian has RA approximately equal to the LST; objects close to "
                "it give a correspondingly close estimate."
            ),
            payload={
                "lst_hours": lst_hours,
                "lst_text": format_local_sidereal_time(model.settings),
                "references": references,
            },
        )

    def _reference_stars(
        self,
        model: SkyMapModel,
        lst_hours: float,
    ) -> list[dict[str, float | str]]:
        if not model.named_stars:
            return []

        observation_time = Time(model.settings.observation_datetime)
        location = EarthLocation.from_geodetic(
            lon=float(model.settings.longitude) * u.deg,
            lat=float(model.settings.latitude) * u.deg,
            height=0 * u.m,
        )
        frame = AltAz(obstime=observation_time, location=location, pressure=0 * u.hPa)

        candidates: list[dict[str, float | str]] = []
        for point in model.named_stars:
            if float(point.altitude) < self.minimum_reference_altitude:
                continue
            horizontal = SkyCoord(
                alt=float(point.altitude) * u.deg,
                az=float(point.azimuth) * u.deg,
                frame=frame,
            )
            equatorial = horizontal.transform_to(ICRS())
            ra_hours = float(equatorial.ra.hour % 24.0)
            hour_angle = _wrap_hours(lst_hours - ra_hours)
            if abs(hour_angle) > self.maximum_reference_hour_angle:
                continue
            candidates.append(
                {
                    "name": point.text,
                    "ra_hours": ra_hours,
                    "ra_text": _format_ra(ra_hours),
                    "hour_angle": hour_angle,
                    "altitude": float(point.altitude),
                    "azimuth": float(point.azimuth),
                    "magnitude": float(point.magnitude) if point.magnitude is not None else 99.0,
                }
            )

        candidates.sort(
            key=lambda item: (
                abs(float(item["hour_angle"])),
                float(item["magnitude"]),
                -float(item["altitude"]),
            )
        )
        if not candidates:
            return []

        # Always give the single best meridian reference. Add a second or third
        # only when they are genuinely competitive with it, rather than filling
        # an arbitrary quota of three stars.
        selected = [candidates[0]]
        best_distance = abs(float(candidates[0]["hour_angle"]))
        for candidate in candidates[1:]:
            if len(selected) >= self.maximum_reference_count:
                break
            distance = abs(float(candidate["hour_angle"]))
            if distance - best_distance > self.relevance_window_hours:
                continue
            selected.append(candidate)
        return selected

    def draw_question(
        self,
        renderer: SkyMapRenderer,
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        del model, question
        renderer.draw_local_meridian(
            color=renderer.MUTED,
            linewidth=1.8,
            alpha=0.9,
            zorder=7,
        )
        renderer.draw_boundary_label(
            180.0,
            "Local meridian",
            color=renderer.MUTED,
            fontsize=8.5,
            radial_gap_degrees=6.0,
            zorder=8,
        )

    def draw_answer(
        self,
        renderer: SkyMapRenderer,
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        del model
        renderer.draw_local_meridian(
            color=renderer.ANSWER,
            linewidth=2.4,
            alpha=1.0,
            zorder=10,
        )
        for item in question.payload["references"]:
            altitude = float(item["altitude"])
            azimuth = float(item["azimuth"])
            renderer.draw_target_point(
                altitude,
                azimuth,
                color=renderer.ANSWER,
                size=62.0,
                zorder=11,
            )
            renderer.draw_upright_label(
                altitude,
                azimuth,
                f"{item['name']} — RA {item['ra_text']}",
                color=renderer.ANSWER,
                fontsize=8.3,
                offset_points=(7.0, 6.0),
                zorder=12,
            )


ACTIVITY_CLASS = EstimateLSTActivity


if __name__ == "__main__":
    raise SystemExit(run_activity(ACTIVITY_CLASS()))
