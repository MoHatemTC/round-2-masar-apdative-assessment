"""
Shared types and constants for the Bayesian estimator.

This module is intentionally framework-free.
It must not import FastAPI, SQLAlchemy, Supabase, or any DB code.
"""

from enum import Enum, IntEnum
from typing import Dict


class Level(IntEnum):
    """Candidate competency level."""

    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


class Difficulty(str, Enum):
    """
    Difficulty labels used by the question bank.
    The numeric mapping lives in ingestion/difficulty_map.py.
    """

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


LEVELS = (
    Level.ONE,
    Level.TWO,
    Level.THREE,
    Level.FOUR,
    Level.FIVE,
)


# Confidence cap by answered-question count.
# Anything above 3 questions uses the default cap.
CONFIDENCE_CLAMP: Dict[int, float] = {
    1: 0.50,
    2: 0.70,
    3: 0.85,
}


DEFAULT_CONFIDENCE_CAP = 0.97


def confidence_cap(question_count: int) -> float:
    """
    Returns the maximum confidence allowed for the
    current number of answered questions.

    Q1 -> 0.50
    Q2 -> 0.70
    Q3 -> 0.85
    Q4+ -> 0.97
    """

    return CONFIDENCE_CLAMP.get(
        question_count,
        DEFAULT_CONFIDENCE_CAP,
    )


# Uniform prior used for the first question.
UNIFORM_PRIOR: Dict[int, float] = {
    1: 0.20,
    2: 0.20,
    3: 0.20,
    4: 0.20,
    5: 0.20,
}