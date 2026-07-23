"""
Frozen estimator contract.

This is the ONLY interface other lanes should depend on.

Sherif should be able to import these dataclasses without
knowing anything about the estimator implementation.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from .types import Difficulty


@dataclass(frozen=True)
class EstimatorInput:
    """
    State before processing the next answered question.
    """

    # Current posterior over levels {1..5}
    posterior: Dict[int, float]

    # Question result (0..5)
    score: int

    # Question difficulty
    difficulty: Difficulty

    # Number of questions already processed
    question_count: int

    # Previous estimated levels
    level_history: List[int] = field(default_factory=list)


@dataclass(frozen=True)
class EstimatorResult:
    """
    Updated estimator state returned by estimate_level().
    """

    # Updated posterior distribution
    posterior: Dict[int, float]

    # Estimated level (MAP)
    level: int

    # Confidence after clamping
    confidence: float

    # Updated question count
    question_count: int

    # Complete level history
    level_history: List[int]

    # Whether the assessment should stop
    stopped: bool

    # Raised only when the question cap is reached
    # before sufficient confidence.
    low_confidence_flag: bool