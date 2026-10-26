"""Minimal interface implemented by each training exercise file."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .models import ActivityQuestion, SkyMapModel

if TYPE_CHECKING:
    from .rendering import SkyMapRenderer


class QuestionUnavailable(RuntimeError):
    """Ask the framework to generate another random sky for this exercise."""


@dataclass(frozen=True)
class ActivityOption:
    """One reusable dropdown declared by an activity."""

    key: str
    label: str
    choices: tuple[tuple[str, str], ...]
    default: str


class SkyActivity(ABC):
    """Base class for one independently runnable training exercise."""

    activity_id = "activity"
    title = "Sky exercise"
    description = ""
    activity_options: tuple[ActivityOption, ...] = ()

    def set_option(self, option_key: str, value: str) -> None:
        """Set one declared activity option after validating its value."""
        definition = next(
            (option for option in self.activity_options if option.key == option_key),
            None,
        )
        if definition is None:
            raise ValueError(f"Unknown activity option: {option_key}")
        valid_values = {choice_key for choice_key, _label in definition.choices}
        if value not in valid_values:
            raise ValueError(f"Unknown value for {option_key}: {value}")
        values = dict(getattr(self, "_activity_option_values", {}))
        values[option_key] = value
        self._activity_option_values = values

    def selected_option(self, option_key: str) -> str:
        """Return an option value, falling back to its declared default."""
        definition = next(
            (option for option in self.activity_options if option.key == option_key),
            None,
        )
        if definition is None:
            raise ValueError(f"Unknown activity option: {option_key}")
        return getattr(self, "_activity_option_values", {}).get(
            option_key,
            definition.default,
        )

    def hidden_star_hips(self, question: ActivityQuestion) -> frozenset[int]:
        """HIP identifiers omitted from the blind question chart."""
        del question
        return frozenset()

    @abstractmethod
    def create_question(
        self,
        model: SkyMapModel,
        rng: random.Random,
    ) -> ActivityQuestion:
        """Build a prompt after the random sky has been calculated."""

    def draw_question(
        self,
        renderer: "SkyMapRenderer",
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        """Draw an optional question marker over the otherwise blind map.

        Exercises 1–4 inherit this no-op implementation. Exercises such as
        "name the constellation" can override it to draw a circle before the
        answer is revealed.
        """

    @abstractmethod
    def draw_answer(
        self,
        renderer: "SkyMapRenderer",
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        """Draw only this exercise's answer over the blind star map."""
