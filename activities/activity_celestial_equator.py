"""Exercise 1: celestial equator, cardinal directions, pole, and latitude."""

from __future__ import annotations

import random
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ioaa_trainer.activity_api import SkyActivity
from ioaa_trainer.activity_ui import run_activity
from ioaa_trainer.models import ActivityQuestion, SkyMapModel
from ioaa_trainer.rendering import SkyMapRenderer


class CelestialEquatorActivity(SkyActivity):
    activity_id = "celestial_equator"
    title = "1 · Celestial Pole and Related"
    description = (
        "Identify the celestial equator, the four cardinal directions, one celestial "
        "pole, and estimate the observer's latitude from a blind sky map."
    )

    def create_question(
        self,
        model: SkyMapModel,
        rng: random.Random,
    ) -> ActivityQuestion:
        del rng
        latitude = float(model.settings.latitude)
        north_pole = latitude >= 0.0
        pole_name = "North celestial pole"
        pole_short = "NCP"
        pole_azimuth = 0.0
        if not north_pole:
            pole_name = "South celestial pole"
            pole_short = "SCP"
            pole_azimuth = 180.0
        pole_altitude = abs(latitude)
        hemisphere = "N" if latitude >= 0.0 else "S"
        latitude_text = f"{abs(latitude):.1f}° {hemisphere}"
        return ActivityQuestion(
            prompt=(
                "Draw in the celestial equator. Identify north, south, east, and "
                "west; locate one celestial pole; and estimate the observer's latitude."
            ),
            answer_text=(
                "The celestial equator and cardinal directions are labelled. "
                f"The marked pole is the {pole_name} ({pole_short}). "
                f"Observer latitude: {latitude_text}."
            ),
            payload={
                "pole_name": pole_name,
                "pole_short": pole_short,
                "pole_altitude": pole_altitude,
                "pole_azimuth": pole_azimuth,
                "latitude_text": latitude_text,
            },
        )

    def draw_answer(
        self,
        renderer: SkyMapRenderer,
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        renderer.draw_curve(
            model.celestial_equator,
            color=renderer.ANSWER,
            linewidth=2.4,
            alpha=1.0,
            zorder=10,
        )
        renderer.draw_cardinal_labels()

        pole_altitude = float(question.payload["pole_altitude"])
        pole_azimuth = float(question.payload["pole_azimuth"])
        pole_radius = 90.0 - pole_altitude
        sky_radius = float(model.settings.sky_radius_degrees)
        pole_label = (
            f"{question.payload['pole_name']} "
            f"({question.payload['pole_short']})"
        )
        if pole_radius <= sky_radius:
            renderer.draw_target_point(
                pole_altitude,
                pole_azimuth,
                color=renderer.ANSWER,
                size=90.0,
                zorder=12,
            )
            renderer.draw_upright_label(
                pole_altitude,
                pole_azimuth,
                pole_label,
                color=renderer.ANSWER,
                fontsize=9.0,
                offset_points=(8.0, 7.0),
                zorder=13,
            )
        else:
            edge_altitude = 90.0 - max(2.0, sky_radius - 4.0)
            renderer.draw_upright_label(
                edge_altitude,
                pole_azimuth,
                f"{pole_label} — beyond chart edge",
                color=renderer.ANSWER,
                fontsize=8.5,
                offset_points=(5.0, 4.0),
                zorder=13,
            )

        renderer.draw_answer_note(
            "Celestial equator highlighted\n"
            f"Latitude ≈ {question.payload['latitude_text']}\n"
            f"Pole altitude = {pole_altitude:.1f}°"
        )


ACTIVITY_CLASS = CelestialEquatorActivity


if __name__ == "__main__":
    raise SystemExit(run_activity(ACTIVITY_CLASS()))
