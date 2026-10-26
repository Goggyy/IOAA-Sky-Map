"""Exercise 3: locate a randomly selected visible constellation."""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ioaa_trainer.activity_api import ActivityOption, QuestionUnavailable, SkyActivity
from ioaa_trainer.activity_ui import run_activity
from ioaa_trainer.models import ActivityQuestion, SkyMapModel
from ioaa_trainer.reference_data import ZODIACAL_CONSTELLATION_ABBREVIATIONS
from ioaa_trainer.rendering import SkyMapRenderer


@dataclass(frozen=True)
class ConstellationSet:
    """One selectable pool of constellation abbreviations."""

    key: str
    label: str
    abbreviations: frozenset[str] | None = None


# Add future groups here; the exercise selector is built from this registry.
CONSTELLATION_SETS = (
    ConstellationSet("all", "All"),
    ConstellationSet(
        "zodiac",
        "Zodiac",
        frozenset(ZODIACAL_CONSTELLATION_ABBREVIATIONS),
    ),
    ConstellationSet(
        "northern",
        "Northern Constellations",
        frozenset({
            "UMa", "UMi", "Cas", "Cep", "Dra", "Boo", "CVn", "CrB",
            "Com", "LMi", "Cam", "Lyn", "Her", "Lac",
        }),
    ),
    ConstellationSet(
        "southern",
        "Southern Constellations",
        frozenset({
            "Cru", "Cen", "Car", "Vel", "Pup", "Dor", "Tuc", "Eri",
            "Mus", "TrA", "Ara", "Nor", "Pav", "Gru", "Hyi", "Oct",
        }),
    ),
    ConstellationSet(
        "winter",
        "Winter Sky",
        frozenset({
            "Ori", "Tau", "Gem", "CMa", "CMi", "Aur", "Per", "Lep",
            "Mon", "Eri", "Col", "Pup", "Cnc", "Cet",
        }),
    ),
    ConstellationSet(
        "summer",
        "Summer Sky",
        frozenset({
            "Cyg", "Lyr", "Aql", "Her", "Oph", "Ser", "Sct", "Sge",
            "Vul", "Del", "Sgr", "Sco", "CrA", "Cap", "Aqr", "Peg",
            "And", "Tri", "Psc",
        }),
    ),
)
CONSTELLATION_SET_BY_KEY = {item.key: item for item in CONSTELLATION_SETS}


class ConstellationActivity(SkyActivity):
    activity_id = "constellation"
    title = "3 · Find Constellation"
    description = (
        "A constellation with a useful part of its line diagram above the horizon is "
        "selected at random. Locate it using only the blind star map."
    )
    minimum_visible_edges = 3
    activity_options = (
        ActivityOption(
            "constellation_set",
            "Set",
            tuple((item.key, item.label) for item in CONSTELLATION_SETS),
            "all",
        ),
    )

    def create_question(
        self,
        model: SkyMapModel,
        rng: random.Random,
    ) -> ActivityQuestion:
        selected_set = CONSTELLATION_SET_BY_KEY[
            self.selected_option("constellation_set")
        ]
        counts = model.visible_constellation_edge_counts()
        candidates = sorted(
            abbreviation
            for abbreviation, count in counts.items()
            if count >= self.minimum_visible_edges
            and (
                selected_set.abbreviations is None
                or abbreviation in selected_set.abbreviations
            )
        )
        if not candidates:
            raise QuestionUnavailable(
                f"no {selected_set.label.lower()} constellation has enough visible line segments"
            )

        abbreviation = rng.choice(candidates)
        name = model.constellation_names.get(abbreviation, abbreviation)
        return ActivityQuestion(
            prompt=f"Locate {name}.",
            answer_text=f"The highlighted line diagram shows {name} ({abbreviation}).",
            payload={
                "abbreviation": abbreviation,
                "name": name,
                "constellation_set": selected_set.key,
            },
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
