"""
Difficulty mapping for Question Bank ingestion.

Single source of truth.

Assignment requirements:

    easy   -> 2
    medium -> 3
    hard   -> 4

This module is intentionally pure.
No DB.
No FastAPI.
"""

from typing import Dict


# ---------------------------------------------------------------------
# Canonical mapping
# ---------------------------------------------------------------------

DIFFICULTY_MAP: Dict[str, int] = {
    "easy": 2,
    "medium": 3,
    "hard": 4,
}


# ---------------------------------------------------------------------
# Reverse mapping
# ---------------------------------------------------------------------

REVERSE_DIFFICULTY_MAP: Dict[int, str] = {
    value: key
    for key, value in DIFFICULTY_MAP.items()
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def to_level(difficulty: str) -> int:
    """
    Convert a difficulty string into its numeric level.

    Raises:
        ValueError: if difficulty is unknown.
    """

    try:
        return DIFFICULTY_MAP[difficulty.lower()]
    except KeyError as exc:
        raise ValueError(
            f"Unknown difficulty '{difficulty}'. "
            "Expected one of: easy, medium, hard."
        ) from exc


def to_difficulty(level: int) -> str:
    """
    Convert a numeric level back to its difficulty string.

    Raises:
        ValueError: if level is invalid.
    """

    try:
        return REVERSE_DIFFICULTY_MAP[level]
    except KeyError as exc:
        raise ValueError(
            f"Unknown difficulty level '{level}'. "
            "Expected one of: 2, 3, 4."
        ) from exc