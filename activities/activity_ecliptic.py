"""Activity 2: identify the ecliptic on a blind sky map."""

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


class EclipticActivity(SkyActivity):
    activity_id = "ecliptic"
    title = "Activity 2 — Ecliptic"
    description = (
        "Use the stellar pattern in a randomly generated, unlabeled sky to identify "
        "the ecliptic."
    )

    def create_question(
        self,
        model: SkyMapModel,
        rng: random.Random,
    ) -> ActivityQuestion:
        del model, rng
        return ActivityQuestion(
            prompt="Draw in the ecliptic.",
            answer_text="The highlighted line is the ecliptic for the generated observation date.",
        )

    def draw_answer(
        self,
        renderer: SkyMapRenderer,
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        del question
        renderer.draw_curve(
            model.ecliptic,
            color=renderer.ANSWER,
            linewidth=2.4,
            alpha=1.0,
            zorder=10,
        )


ACTIVITY_CLASS = EclipticActivity


if __name__ == "__main__":
    raise SystemExit(run_activity(ACTIVITY_CLASS()))
