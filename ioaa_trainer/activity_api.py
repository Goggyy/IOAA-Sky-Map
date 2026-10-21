"""Minimal interface implemented by each training exercise file."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .models import ActivityQuestion, SkyMapModel

if TYPE_CHECKING:
    from .rendering import SkyMapRenderer


class QuestionUnavailable(RuntimeError):
    """Ask the framework to generate another random sky for this exercise."""


class SkyActivity(ABC):
    """Base class for one independently runnable training exercise."""

    activity_id = "activity"
    title = "Sky exercise"
    description = ""

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
