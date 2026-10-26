"""Exercise 8: identify bright stars removed from an otherwise normal sky."""

from __future__ import annotations

import math
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


class MissingStarsActivity(SkyActivity):
    activity_id = "missing_stars"
    title = "8 · Missing Stars"
    description = "Identify bright stars removed from the chart."
    minimum_target_altitude = 8.0
    bright_balance_magnitude = 2.5
    activity_options = (
        ActivityOption(
            "missing_count",
            "Missing",
            tuple((str(count), str(count)) for count in range(1, 8)),
            "3",
        ),
        ActivityOption(
            "star_set",
            "Set",
            STAR_SET_CHOICES,
            "top_60",
        ),
    )

    def create_question(
        self,
        model: SkyMapModel,
        rng: random.Random,
    ) -> ActivityQuestion:
        missing_count = int(self.selected_option("missing_count"))
        star_set = self.selected_option("star_set")
        pool = STAR_SETS[star_set]

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
            (identity, *visible_by_hip[identity.hip])
            for identity in pool
            if identity.hip in visible_by_hip
            and visible_by_hip[identity.hip][0] >= self.minimum_target_altitude
        ]
        if len(candidates) < missing_count:
            raise QuestionUnavailable(
                f"only {len(candidates)} eligible stars are visible"
            )

        selected = self._balanced_sample(candidates, missing_count, rng)
        selected.sort(key=lambda item: item[3])
        targets = [
            {
                "hip": identity.hip,
                "name": identity.name,
                "bayer_full": identity.bayer_full,
                "bayer_short": identity.bayer_short,
                "altitude": altitude,
                "azimuth": azimuth,
                "magnitude": magnitude,
            }
            for identity, altitude, azimuth, magnitude in selected
        ]
        noun = "star" if missing_count == 1 else "stars"
        answer_lines = [
            f"{index}. {target['name']} — {target['bayer_short']}"
            for index, target in enumerate(targets, 1)
        ]
        return ActivityQuestion(
            prompt=f"Identify the {missing_count} missing {noun}.",
            answer_text="Missing:\n" + "\n".join(answer_lines),
            payload={
                "targets": targets,
                "star_set": star_set,
                "hidden_star_hips": tuple(target["hip"] for target in targets),
            },
        )

    def _balanced_sample(self, candidates, count: int, rng: random.Random):
        """Keep hard questions from becoming an all-faint random draw."""
        if count == 1:
            return [rng.choice(candidates)]

        bright = [
            candidate
            for candidate in candidates
            if candidate[3] <= self.bright_balance_magnitude
        ]
        faint = [
            candidate
            for candidate in candidates
            if candidate[3] > self.bright_balance_magnitude
        ]
        bright_count = min(len(bright), math.ceil(count / 2))
        selected = rng.sample(bright, bright_count)
        remaining_count = count - len(selected)
        if remaining_count:
            remaining = faint + [item for item in bright if item not in selected]
            selected.extend(rng.sample(remaining, remaining_count))
        return selected

    def hidden_star_hips(self, question: ActivityQuestion) -> frozenset[int]:
        return frozenset(int(hip) for hip in question.payload["hidden_star_hips"])

    def draw_answer(
        self,
        renderer: SkyMapRenderer,
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        del model
        for index, target in enumerate(question.payload["targets"], 1):
            altitude = float(target["altitude"])
            azimuth = float(target["azimuth"])
            renderer.draw_target_circle(
                altitude,
                azimuth,
                diameter_points=24.0,
                color=renderer.ANSWER,
                linewidth=1.8,
                zorder=10,
            )
            renderer.draw_upright_label(
                altitude,
                azimuth,
                str(index),
                color=renderer.ANSWER,
                fontsize=9.5,
                offset_points=(8.0, 7.0),
                zorder=12,
            )


ACTIVITY_CLASS = MissingStarsActivity


if __name__ == "__main__":
    raise SystemExit(run_activity(ACTIVITY_CLASS()))
