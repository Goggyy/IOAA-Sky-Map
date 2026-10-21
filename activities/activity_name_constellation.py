"""Exercise 5: name the constellation whose general area is circled."""

from __future__ import annotations

import random
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ioaa_trainer.activity_api import QuestionUnavailable, SkyActivity
from ioaa_trainer.activity_ui import run_activity
from ioaa_trainer.models import ActivityQuestion, SkyMapModel
from ioaa_trainer.rendering import SkyMapRenderer
from ioaa_trainer.targeting import constellation_target_region


class NameConstellationActivity(SkyActivity):
    activity_id = "name_constellation"
    title = "Exercise 5 — Name the Constellation"
    description = (
        "A circle marks the general area of a visible constellation. Identify the "
        "constellation from the surrounding star pattern."
    )
    minimum_visible_edges = 3
    minimum_target_altitude = 10.0

    def create_question(
        self,
        model: SkyMapModel,
        rng: random.Random,
    ) -> ActivityQuestion:
        counts = model.visible_constellation_edge_counts()
        candidates: list[tuple[str, float, float, float]] = []

        for abbreviation, count in counts.items():
            if count < self.minimum_visible_edges:
                continue
            region = constellation_target_region(model, abbreviation)
            if region is None or region.altitude < self.minimum_target_altitude:
                continue
            candidates.append(
                (
                    abbreviation,
                    region.altitude,
                    region.azimuth,
                    region.diameter_points,
                )
            )

        if not candidates:
            raise QuestionUnavailable("no suitable constellation target is clearly visible")

        abbreviation, altitude, azimuth, diameter = rng.choice(sorted(candidates))
        name = model.constellation_names.get(abbreviation, abbreviation)
        return ActivityQuestion(
            prompt="Name the constellation in the circled area.",
            answer_text=f"The circled constellation is {name} ({abbreviation}).",
            payload={
                "abbreviation": abbreviation,
                "name": name,
                "altitude": altitude,
                "azimuth": azimuth,
                "diameter_points": diameter,
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
            diameter_points=float(question.payload["diameter_points"]),
            color=renderer.ANSWER,
            linewidth=2.2,
            zorder=9,
        )

    def draw_answer(
        self,
        renderer: SkyMapRenderer,
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        abbreviation = str(question.payload["abbreviation"])
        renderer.draw_constellation(
            model,
            abbreviation,
            color=renderer.ANSWER,
            linewidth=2.5,
            alpha=1.0,
            zorder=10,
        )
        renderer.draw_upright_label(
            float(question.payload["altitude"]),
            float(question.payload["azimuth"]),
            str(question.payload["name"]),
            color=renderer.ANSWER,
            fontsize=10.0,
            offset_points=(8.0, 8.0),
            zorder=12,
        )


ACTIVITY_CLASS = NameConstellationActivity


if __name__ == "__main__":
    raise SystemExit(run_activity(ACTIVITY_CLASS()))
