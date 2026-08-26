"""Activity 1: identify the celestial equator on a blind sky map."""

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
    title = "Activity 1 — Celestial Equator"
    description = (
        "Use the stellar pattern in a randomly generated, unlabeled sky to identify "
        "the celestial equator."
    )

    def create_question(
        self,
        model: SkyMapModel,
        rng: random.Random,
    ) -> ActivityQuestion:
        del model, rng
        return ActivityQuestion(
            prompt="Draw in the celestial equator.",
            answer_text="The highlighted line is the celestial equator (declination 0°).",
        )

    def draw_answer(
        self,
        renderer: SkyMapRenderer,
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        del question
        renderer.draw_curve(
            model.celestial_equator,
            color=renderer.ANSWER,
            linewidth=2.4,
            alpha=1.0,
            zorder=10,
        )


ACTIVITY_CLASS = CelestialEquatorActivity


if __name__ == "__main__":
    raise SystemExit(run_activity(ACTIVITY_CLASS()))
