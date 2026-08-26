"""Minimal interface implemented by each training activity file."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .models import ActivityQuestion, SkyMapModel

if TYPE_CHECKING:
    from .rendering import SkyMapRenderer


class QuestionUnavailable(RuntimeError):
    """Ask the framework to generate another random sky for this activity."""


class SkyActivity(ABC):
    """Base class for one independently runnable training activity."""

    activity_id = "activity"
    title = "Sky activity"
    description = ""

    @abstractmethod
    def create_question(
        self,
        model: SkyMapModel,
        rng: random.Random,
    ) -> ActivityQuestion:
        """Build a prompt after the random sky has been calculated."""

    @abstractmethod
    def draw_answer(
        self,
        renderer: "SkyMapRenderer",
        model: SkyMapModel,
        question: ActivityQuestion,
    ) -> None:
        """Draw only this activity's answer over the blind star map."""
