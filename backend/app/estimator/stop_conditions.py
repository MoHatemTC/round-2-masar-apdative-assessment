"""
Stopping rules for the Bayesian estimator.

Pure deterministic module.

No DB.
No FastAPI.
"""

from typing import List, Tuple


CONFIDENCE_TARGET = 0.90

STABLE_STREAK = 3

QUESTION_CAP = 10


def confidence_reached(
    confidence: float,
) -> bool:
    """
    Stop once confidence reaches the target.
    """

    return confidence >= CONFIDENCE_TARGET


def stable_level(
    history: List[int],
) -> bool:
    """
    Stop if the same estimated level has appeared
    three consecutive times.
    """

    if len(history) < STABLE_STREAK:
        return False

    recent = history[-STABLE_STREAK:]

    return len(set(recent)) == 1


def question_cap(
    question_count: int,
) -> bool:
    """
    Stop after the maximum number of questions.
    """

    return question_count >= QUESTION_CAP


def evaluate_stop_conditions(
    *,
    history: List[int],
    confidence: float,
    question_count: int,
) -> Tuple[bool, bool]:
    """
    Returns

        (
            stopped,
            low_confidence_flag,
        )

    Stop priority:

    1. Confidence target

    2. Stable estimate

    3. Question cap
    """

    if confidence_reached(confidence):
        return (
            True,
            False,
        )

    if stable_level(history):
        return (
            True,
            False,
        )

    if question_cap(question_count):
        return (
            True,
            True,
        )

    return (
        False,
        False,
    )