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
# The mapping must span the entire [0, 5] score range so that extreme scores
# (0 and 5) are equally sharp evidence for their respective levels (1 and 5).
#
# History of fixes:
#   v1  {1:1, 2:2, 3:3, 4:4, 5:5} — identity mapping.  Score 0 landed 1.0
#       away from level 1, but score 5 landed 0.0 away from level 5.
#       Bottom-of-scale bias: failing was weaker evidence than acing.
#
#   v2  {1:0, 2:1, 3:2, 4:3, 5:4} — shifted by (level-1).  Fixed the bottom
#       but introduced top-of-scale bias: score 5 now landed 1.0 away from
#       level 5 (expected 4), while score 0 landed 0.0 from level 1.
#       Result: a zero was always stronger evidence than a five, pulling
#       erratic candidates toward level 1 with false confidence.
#
#   v3  {1:0, 2:1.25, 3:2.5, 4:3.75, 5:5.0} — evenly spaced across [0, 5].
#       Score 0 ↔ level 1 and score 5 ↔ level 5 are now perfectly symmetric
#       (distance = 0.0 in both cases).  This is the current (correct) mapping.
_EXPECTED_SCORE = {
    1: 0.0,
    2: 1.25,
    3: 2.5,
    4: 3.75,
    5: 5.0,
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