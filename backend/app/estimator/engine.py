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
confidence calculation
    ↓
CONFIDENCE_CLAMP applied
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

from .stop_conditions import (
    evaluate_stop_conditions,
)

from .types import (
    UNIFORM_PRIOR,
    confidence_cap,
)


def _normalize(
    posterior: Dict[int, float],
) -> Dict[int, float]:
    """
    Normalize posterior probabilities.
    """

    total = sum(posterior.values())

    if total <= 0:
        return UNIFORM_PRIOR.copy()

    normalized = {
        level: probability / total
        for level, probability in posterior.items()
    }

    assert abs(sum(normalized.values()) - 1.0) < 1e-9

    return normalized



def _argmax(
    posterior: Dict[int, float],
) -> int:
    """
    MAP estimate.

    Higher level wins ties.
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
    Posterior concentration confidence.
    """

    probabilities = list(
        posterior.values()
    )

    highest = max(probabilities)

    spread = (
        sum(
            abs(highest - p)
            for p in probabilities
        )
        /
        (len(probabilities) - 1)
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
    Perform one Bayesian estimation update.
    """

    prior = state.posterior


    # -------------------------------
    # Likelihood update
    # -------------------------------

    observation = likelihood(
        score=state.score,
        difficulty=state.difficulty,
    )


    assert set(prior.keys()) == set(
        observation.keys()
    )


    posterior = {
        level: prior[level] * observation[level]
        for level in prior
    }


    posterior = _normalize(
        posterior
    )


    # -------------------------------
    # Estimate level
    # -------------------------------

    estimated_level = _argmax(
        posterior
    )


    # -------------------------------
    # Confidence calculation
    # -------------------------------

    confidence = _confidence(
        posterior
    )


    question_count = (
        state.question_count + 1
    )


    # -------------------------------
    # CONFIDENCE_CLAMP
    #
    # Prevent early lucky answers
    # from reaching stop threshold.
    #
    # Example:
    # Q1 -> max 0.50
    # Q2 -> max 0.70
    # Q3 -> max 0.85
    # Q4+ -> max 0.97
    # -------------------------------

    confidence = min(
        confidence,
        confidence_cap(question_count),
    )


    # -------------------------------
    # History
    # -------------------------------

    history = list(
        state.level_history
    )

    history.append(
        estimated_level
    )


    # IMPORTANT:
    # pass the already clamped confidence
    # into stop evaluation
    stopped, low_confidence = (
        evaluate_stop_conditions(
            history=history,
            confidence=confidence,
            question_count=question_count,
        )
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