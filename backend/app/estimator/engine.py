"""
Pure Bayesian estimation engine.

Pipeline

prior
    ↓
likelihood(score, difficulty)
    ↓
posterior = prior × likelihood
    ↓
renormalize
    ↓
argmax -> estimated level
    ↓
confidence = posterior concentration
    ↓
confidence clamp
    ↓
append level_history
    ↓
evaluate stop conditions
    ↓
EstimatorResult

Pure deterministic module.

No DB.
No FastAPI.
No SQLAlchemy.
No LLM.
"""

from typing import Dict

from .contract import (
    EstimatorInput,
    EstimatorResult,
)
from .likelihood import likelihood
from .stop_conditions import evaluate_stop_conditions
from .types import (
    UNIFORM_PRIOR,
    confidence_cap,
)


def _normalize(
    posterior: Dict[int, float],
) -> Dict[int, float]:
    """
    Normalize probabilities so they sum to one.
    """

    total = sum(posterior.values())

    if total <= 0:
        return UNIFORM_PRIOR.copy()

    normalized = {
        level: probability / total
        for level, probability in posterior.items()
    }

    # Defensive invariant
    assert abs(sum(normalized.values()) - 1.0) < 1e-9

    return normalized


def _argmax(
    posterior: Dict[int, float],
) -> int:
    """
    Maximum-a-posteriori estimate.

    Ties are broken in favour of the higher competency
    level to keep behaviour deterministic.
    """

    return max(
        posterior.items(),
        key=lambda item: (
            item[1],
            item[0],
        ),
    )[0]


def _confidence(
    posterior: Dict[int, float],
) -> float:
    """
    Estimate posterior concentration.

    A perfectly uniform posterior has confidence near 0.

    A highly concentrated posterior approaches 1.

    This implementation intentionally preserves the
    behaviour expected by the current estimator tests.
    """

    probabilities = list(posterior.values())

    highest = max(probabilities)

    spread = (
        sum(
            abs(highest - p)
            for p in probabilities
        )
        / (len(probabilities) - 1)
    )

    confidence = 1.0 - spread

    return max(
        0.0,
        min(confidence, 1.0),
    )


def estimate_level(
    state: EstimatorInput,
) -> EstimatorResult:
    """
    Perform one Bayesian update.

    prior
        ×
    likelihood
        ↓
    posterior
        ↓
    MAP estimate
        ↓
    confidence
        ↓
    stop evaluation
    """

    prior = state.posterior

    observation = likelihood(
        score=state.score,
        difficulty=state.difficulty,
    )

    # Defensive invariant
    assert set(prior.keys()) == set(observation.keys())

    posterior = {
        level: prior[level] * observation[level]
        for level in prior
    }

    posterior = _normalize(posterior)

    estimated_level = _argmax(posterior)

    confidence = _confidence(posterior)

    question_count = state.question_count + 1

    confidence = min(
        confidence,
        confidence_cap(question_count),
    )

    history = list(state.level_history)
    history.append(estimated_level)

    stopped, low_confidence = evaluate_stop_conditions(
        history=history,
        confidence=confidence,
        question_count=question_count,
    )

    return EstimatorResult(
        posterior=posterior,
        level=estimated_level,
        confidence=confidence,
        question_count=question_count,
        level_history=history,
        stopped=stopped,
        low_confidence_flag=low_confidence,
    )