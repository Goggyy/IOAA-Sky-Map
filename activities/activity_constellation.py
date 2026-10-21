"""Exercise 3: locate a randomly selected visible constellation."""

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


class ConstellationActivity(SkyActivity):
    activity_id = "constellation"
    title = "Exercise 3 — Locate a Constellation"
    description = (
        "A constellation with a useful part of its line diagram above the horizon is "
        "selected at random. Locate it using only the blind star map."
    )
    minimum_visible_edges = 3

    def create_question(
        self,
        model: SkyMapModel,
        rng: random.Random,
    ) -> ActivityQuestion:
        counts = model.visible_constellation_edge_counts()
        candidates = sorted(
            abbreviation
            for abbreviation, count in counts.items()
            if count >= self.minimum_visible_edges
        )
        if not candidates:
            raise QuestionUnavailable("no constellation has enough visible line segments")

        abbreviation = rng.choice(candidates)
        name = model.constellation_names.get(abbreviation, abbreviation)
        return ActivityQuestion(
            prompt=f"Locate the constellation {name}.",
            answer_text=f"The highlighted line diagram shows {name} ({abbreviation}).",
            payload={"abbreviation": abbreviation, "name": name},
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


ACTIVITY_CLASS = ConstellationActivity


if __name__ == "__main__":
    raise SystemExit(run_activity(ACTIVITY_CLASS()))
