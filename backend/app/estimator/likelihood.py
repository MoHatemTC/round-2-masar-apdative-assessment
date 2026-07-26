"""
Likelihood model.

Converts an observed (score, difficulty) pair into a likelihood
distribution over competency levels {1..5}.

Pure deterministic module.

No DB.
No FastAPI.
No LLM.
"""

from typing import Dict

from .types import Difficulty, LEVELS


# Expected score for each level (1-5), rescaled onto the FULL 0-5 score range.
#
# BUGFIX: this used to be an identity mapping ({1: 1.0, ..., 5: 5.0}), which is
# asymmetric — scores span 6 values (0..5) but levels only span 5 (1..5), so a
# perfect score (5, HARD -> adjusted 5.5) landed only 0.5 away from level 5's
# expected value, while a zero score (0, EASY -> adjusted -0.5) landed a full 1.5
# away from level 1's expected value. That asymmetry meant "acing a hard question"
# produced a far sharper, more dominant vote than "failing an easy question"
# produced against it, so one strong early answer could never be overturned by a
# later contradicting one — an inconsistent (erratic) candidate would incorrectly
# look "stable" and converge on noise instead of exhausting the question cap.
# Rescaling to (level - 1) makes both ends of the score range symmetric around
# their nearest level.
_EXPECTED_SCORE = {
    1: 0.0,
    2: 1.0,
    3: 2.0,
    4: 3.0,
    5: 4.0,
}


# Difficulty shifts.
# Hard questions reward higher levels.
#
# BUGFIX: raised from +-0.50 to +-1.00 alongside the sigma change below — at the
# old magnitude, two contradicting answers in a row didn't carry enough combined
# weight to overturn a single earlier answer, so a genuinely inconsistent
# candidate could still "stabilize" (same argmax 3x) well before the question cap.
_DIFFICULTY_OFFSET = {
    Difficulty.EASY: -1.00,
    Difficulty.MEDIUM: 0.00,
    Difficulty.HARD: 1.00,
}


def _similarity(distance: float) -> float:
    """
    Smooth deterministic similarity function.

    Returns values in (0,1].
    """

    # BUGFIX: narrowed from 1.25 to 0.5 — paired with the _EXPECTED_SCORE and
    # _DIFFICULTY_OFFSET changes above, this makes each answer discriminating
    # enough that consistent evidence still converges in ~3-5 questions (verified
    # in tests/estimator/test_convergence.py), while genuinely contradictory
    # evidence can actually move the estimate instead of leaving it pinned on an
    # earlier answer's noise.
    sigma = 0.50

    return 1.0 / (1.0 + (distance / sigma) ** 2)


def likelihood(
    score: int,
    difficulty: Difficulty,
) -> Dict[int, float]:
    """
    Compute:

        P(observation | level)

    Returns a normalized distribution over levels.

    score ∈ [0,5]
    """

    score = max(0, min(score, 5))

    adjusted_score = score + _DIFFICULTY_OFFSET[difficulty]

    values = {}

    total = 0.0

    for level in LEVELS:

        expected = _EXPECTED_SCORE[level.value]

        p = _similarity(abs(adjusted_score - expected))

        values[level.value] = p

        total += p

    return {
        level: value / total
        for level, value in values.items()
    }