"""Exercise 6: identify a bright star from a supplied Alt/Az coordinate."""

from __future__ import annotations

import random
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ioaa_trainer.activity_api import ActivityOption, QuestionUnavailable, SkyActivity
from ioaa_trainer.activity_ui import run_activity
from ioaa_trainer.models import ActivityQuestion, SkyMapModel
from ioaa_trainer.rendering import SkyMapRenderer
from ioaa_trainer.star_sets import STAR_SETS, STAR_SET_CHOICES


class AltAzStarActivity(SkyActivity):
    activity_id = "altaz_star"
    title = "6 · Name Star from Alt/Az"
    description = (
        "Given an altitude/azimuth coordinate, identify the star and its Bayer designation. "
        "Cardinal directions are shown on the question chart."
    )
    minimum_target_altitude = 5.0
    activity_options = (ActivityOption("star_set", "Set", STAR_SET_CHOICES, "top_60"),)

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
            for identity in STAR_SETS[self.selected_option("star_set")]
            if identity.hip in visible_by_hip
            and visible_by_hip[identity.hip][0] >= self.minimum_target_altitude
        ]
        if not candidates:
            raise QuestionUnavailable("no stars from this set are suitably visible")

        identity = rng.choice(sorted(candidates, key=lambda star: star.name))
        altitude, azimuth, magnitude = visible_by_hip[identity.hip]
        coordinate_text = f"Alt {altitude:.1f}°, Az {azimuth:.1f}°"
        return ActivityQuestion(
            prompt=(
                f"At {coordinate_text}, identify the star (name, if any, and "
                "Bayer designation). Azimuth is measured from north through east."
            ),
            answer_text=(
                f"Answer: {identity.answer}. The star is at {coordinate_text}."
            ),
            payload={
                "hip": identity.hip,
                "iau_name": identity.name,
                "display_label": identity.answer,
                "bayer_full": identity.bayer_full,
                "bayer_short": identity.bayer_short,
                "altitude": altitude,
                "azimuth": azimuth,
                "magnitude": magnitude,
                "coordinate_text": coordinate_text,
            },
        )

    def draw_question(
        self,
        renderer: SkyMapRenderer,
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        del model, question
        renderer.draw_cardinal_labels(color=renderer.MUTED, zorder=9)

    def draw_answer(
        self,
        renderer: SkyMapRenderer,
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        del model
        altitude = float(question.payload["altitude"])
        azimuth = float(question.payload["azimuth"])
        renderer.draw_target_point(
            altitude,
            azimuth,
            color=renderer.ANSWER,
            size=90.0,
            zorder=11,
        )
        renderer.draw_upright_label(
            altitude,
            azimuth,
            str(question.payload["display_label"]),
            color=renderer.ANSWER,
            fontsize=9.2,
            offset_points=(9.0, 8.0),
            zorder=12,
        )
        renderer.draw_answer_note(
            f"{question.payload['coordinate_text']}\n{question.payload['iau_name']} — "
            f"{question.payload['bayer_short']}"
        )


ACTIVITY_CLASS = AltAzStarActivity


if __name__ == "__main__":
    raise SystemExit(run_activity(ACTIVITY_CLASS()))
