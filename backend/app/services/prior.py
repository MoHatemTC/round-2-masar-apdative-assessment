"""Starting-prior computation for the adaptive engine.

Before the adaptive loop asks a single question, each measured competency needs a starting belief
(a 1-5 "prior") to seed its Bayesian posterior. This module is the single place that formula lives,
so the intake routes (which compute it for display / persistence) and the adaptive loop's
`init_session` (which uses it to seed the posterior) never drift apart.

Rule, per the PRD ("Starting prior"):
    prior = round(0.5 * cv_estimate + 0.5 * self_rating)   -- when both are known
    prior = self_rating                                     -- when there's no CV estimate
    prior = 3                                                -- when neither is known

Week 1 scope only ever hits the last two branches (CV estimation is a separate, LLM-backed service
owned by another lane and isn't available at intake time); the blended branch is included so this
module is already correct once that CV estimate exists, without a second implementation appearing
elsewhere.
"""
from __future__ import annotations

import math

DEFAULT_PRIOR = 3
MIN_LEVEL, MAX_LEVEL = 1, 5


def _clamp(level: int) -> int:
    """Keep a level inside the valid 1-5 range regardless of what fed it."""
    return max(MIN_LEVEL, min(MAX_LEVEL, level))


def _round_half_up(value: float) -> int:
    """Ordinary round-half-up (2.5 -> 3), not Python's round() (which rounds .5 to even, so
    round(2.5) == 2). The PRD's blend formula reads as everyday rounding, so this keeps
    prior computation predictable regardless of the operands' parity."""
    return math.floor(value + 0.5)


def compute_prior(self_rating: int | None, cv_estimate: int | None = None) -> int:
    """Compute one competency's starting prior (1-5).

    Args:
        self_rating: the candidate's own 1-5 rating for this competency, or None if not given.
        cv_estimate: an LLM-derived 1-5 estimate from the candidate's CV, or None if there's no CV
            (or no estimate for this competency yet).

    Returns:
        An int in [1, 5]:
          - both present  -> round(0.5*cv_estimate + 0.5*self_rating), clamped
          - self only     -> self_rating, clamped
          - neither       -> DEFAULT_PRIOR (3)
    """
    if self_rating is None and cv_estimate is None:
        return DEFAULT_PRIOR
    if cv_estimate is None:
        return _clamp(int(self_rating))
    if self_rating is None:
        # Not part of the PRD formula (a self-rating is always collected at intake), but fail
        # sensibly rather than raising if this is ever called with only a CV estimate.
        return _clamp(int(cv_estimate))
    blended = _round_half_up(0.5 * cv_estimate + 0.5 * self_rating)
    return _clamp(blended)


def compute_priors(self_ratings: dict[str, int], cv_estimates: dict[str, int] | None = None) -> dict[str, int]:
    """Compute the starting prior for every competency named in `self_ratings`.

    `cv_estimates` is optional and keyed the same way (competency_id -> 1-5 int). A competency with
    a self-rating but no matching CV estimate falls back to the self-rating alone, per the PRD rule.
    Competencies that only appear in `cv_estimates` (no self-rating) are not included — intake
    always collects a self-rating, so this shouldn't happen in practice, but it keeps the return
    keyed exactly to what the candidate answered.
    """
    cv_estimates = cv_estimates or {}
    return {
        competency_id: compute_prior(rating, cv_estimates.get(competency_id))
        for competency_id, rating in self_ratings.items()
    }
