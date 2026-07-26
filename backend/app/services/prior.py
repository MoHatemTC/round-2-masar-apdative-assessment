"""Starting-prior computation for the adaptive engine — intake-facing adapter.

The actual blend formula (round(0.5*cv + 0.5*self), with self-only / default-3 fallbacks) lives in
`app.services.priors_bridge.blend_intake_signals` — that's the single source of truth the core
adaptive loop also uses to seed its Bayesian posterior. This module does NOT reimplement that
formula; it just calls it and turns the result into a clamped 1-5 integer, which is what the
intake endpoint wants to persist/display before the loop ever runs.
"""
from __future__ import annotations

import math

from app.services.priors_bridge import blend_intake_signals

DEFAULT_PRIOR = 3  # kept for callers/tests that reference the documented default directly
MIN_LEVEL, MAX_LEVEL = 1, 5


def _clamp(level: int) -> int:
    """Keep a level inside the valid 1-5 range regardless of what fed it."""
    return max(MIN_LEVEL, min(MAX_LEVEL, level))


def _round_half_up(value: float) -> int:
    """Ordinary round-half-up (2.5 -> 3), not Python's round() (which rounds .5 to even, so
    round(2.5) == 2). blend_intake_signals rounds to 1 decimal place (fine for a continuous
    posterior peak), but converting THAT down to a whole level still needs half-up rounding to
    stay predictable regardless of parity."""
    return math.floor(value + 0.5)


def compute_prior(self_rating: int | None, cv_estimate: int | None = None) -> int:
    """Compute one competency's starting prior as a clamped 1-5 int.

    Delegates the actual blend/fallback math to `priors_bridge.blend_intake_signals` (which
    returns a float, e.g. 3.5) and rounds that half-up into a whole level.
    """
    blended = blend_intake_signals(self_rating, cv_estimate)
    return _clamp(_round_half_up(blended))


def compute_priors(self_ratings: dict[str, int], cv_estimates: dict[str, int] | None = None) -> dict[str, int]:
    """Compute the starting prior for every competency named in `self_ratings`.

    `cv_estimates` is optional and keyed the same way (competency_id -> 1-5 int). A competency with
    a self-rating but no matching CV estimate falls back to the self-rating alone, per the PRD rule.
    """
    cv_estimates = cv_estimates or {}
    return {
        competency_id: compute_prior(rating, cv_estimates.get(competency_id))
        for competency_id, rating in self_ratings.items()
    }