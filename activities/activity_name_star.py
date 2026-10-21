"""Exercise 6: name a circled bright star and give its Bayer designation."""

from __future__ import annotations

import random
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ioaa_trainer.activity_api import QuestionUnavailable, SkyActivity
from ioaa_trainer.activity_ui import run_activity
from ioaa_trainer.models import ActivityQuestion, SkyMapModel
from ioaa_trainer.reference_data import BRIGHTEST_STAR_BY_HIP
from ioaa_trainer.rendering import SkyMapRenderer


class NameStarActivity(SkyActivity):
    activity_id = "name_star"
    title = "Exercise 6 — Name the Star"
    description = (
        "A circle marks one of approximately the 20 brightest night-sky stars. "
        "Give both its IAU-approved proper name and Bayer designation."
    )
    minimum_target_altitude = 8.0

    def create_question(
        self,
        model: SkyMapModel,
        rng: random.Random,
    ) -> ActivityQuestion:
        visible_by_hip = {
            int(hip): (float(altitude), float(azimuth), float(magnitude))
            for hip, altitude, azimuth, magnitude in zip(
                model.stars.hip,
                model.stars.altitude,
                model.stars.azimuth,
                model.stars.magnitude,
            )
        }

        candidates = [
            identity
            for hip, identity in BRIGHTEST_STAR_BY_HIP.items()
            if hip in visible_by_hip
            and visible_by_hip[hip][0] >= self.minimum_target_altitude
        ]
        if not candidates:
            raise QuestionUnavailable("none of the bright-star targets is high enough")

        identity = rng.choice(sorted(candidates, key=lambda star: star.iau_name))
        altitude, azimuth, magnitude = visible_by_hip[identity.hip]
        return ActivityQuestion(
            prompt=(
                "Name the circled star. Give its IAU-approved name and its "
                "Bayer designation."
            ),
            answer_text=f"Answer: {identity.answer}.",
            payload={
                "hip": identity.hip,
                "iau_name": identity.iau_name,
                "bayer_full": identity.bayer_full,
                "bayer_short": identity.bayer_short,
                "altitude": altitude,
                "azimuth": azimuth,
                "magnitude": magnitude,
            },
        )

    def draw_question(
        self,
        renderer: SkyMapRenderer,
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        renderer.draw_target_circle(
            float(question.payload["altitude"]),
            float(question.payload["azimuth"]),
            diameter_points=46.0,
            color=renderer.ANSWER,
            linewidth=2.1,
            zorder=9,
        )

    def draw_answer(
        self,
        renderer: SkyMapRenderer,
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        altitude = float(question.payload["altitude"])
        azimuth = float(question.payload["azimuth"])
        renderer.draw_target_point(
            altitude,
            azimuth,
            color=renderer.ANSWER,
            size=86.0,
            zorder=11,
        )
        renderer.draw_upright_label(
            altitude,
            azimuth,
            (
                f"{question.payload['iau_name']}\n"
                f"{question.payload['bayer_full']} "
                f"({question.payload['bayer_short']})"
            ),
            color=renderer.ANSWER,
            fontsize=9.2,
            offset_points=(9.0, 8.0),
            zorder=12,
        )


ACTIVITY_CLASS = NameStarActivity


if __name__ == "__main__":
    raise SystemExit(run_activity(ACTIVITY_CLASS()))
