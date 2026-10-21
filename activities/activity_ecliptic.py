"""Exercise 2: identify the ecliptic and its zodiacal constellations."""

from __future__ import annotations

import random
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ioaa_trainer.activity_api import SkyActivity
from ioaa_trainer.activity_ui import run_activity
from ioaa_trainer.models import ActivityQuestion, SkyMapModel
from ioaa_trainer.reference_data import ZODIACAL_CONSTELLATION_ABBREVIATIONS
from ioaa_trainer.rendering import SkyMapRenderer
from ioaa_trainer.targeting import constellation_target_region


class EclipticActivity(SkyActivity):
    activity_id = "ecliptic"
    title = "Exercise 2 — Ecliptic"
    description = (
        "Use the stellar pattern in a randomly generated, unlabeled sky to identify "
        "the ecliptic. The answer also identifies the visible zodiacal constellations."
    )

    def create_question(
        self,
        model: SkyMapModel,
        rng: random.Random,
    ) -> ActivityQuestion:
        del model, rng
        return ActivityQuestion(
            prompt="Draw in the ecliptic.",
            answer_text=(
                "The highlighted line is the ecliptic. The visible line diagrams and "
                "names show the zodiacal constellations through which it passes."
            ),
        )

    def draw_answer(
        self,
        renderer: SkyMapRenderer,
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        del question
        for abbreviation in sorted(ZODIACAL_CONSTELLATION_ABBREVIATIONS):
            renderer.draw_constellation(
                model,
                abbreviation,
                color=renderer.CONSTELLATION,
                linewidth=1.35,
                alpha=0.95,
                zorder=9,
            )

        for abbreviation in sorted(ZODIACAL_CONSTELLATION_ABBREVIATIONS):
            region = constellation_target_region(model, abbreviation)
            if region is None:
                continue
            renderer.draw_upright_label(
                region.altitude,
                region.azimuth,
                model.constellation_names.get(abbreviation, abbreviation),
                color=renderer.CONSTELLATION,
                fontsize=8.0,
                offset_points=(4.0, 4.0),
                zorder=11,
            )

        renderer.draw_curve(
            model.ecliptic,
            color=renderer.ANSWER,
            linewidth=2.5,
            alpha=1.0,
            zorder=12,
        )


ACTIVITY_CLASS = EclipticActivity


if __name__ == "__main__":
    raise SystemExit(run_activity(ACTIVITY_CLASS()))
