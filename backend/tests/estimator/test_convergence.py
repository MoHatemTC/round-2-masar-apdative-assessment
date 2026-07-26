"""
Synthetic convergence tests for the Bayesian estimator.

Required scenarios:

1. Strong candidate
   → converges to high level in ~4-5 questions.

2. Weak candidate
   → converges to low level.

3. Erratic candidate
   → reaches question cap and raises low-confidence flag.
"""

from app.estimator.contract import EstimatorInput
from app.estimator.engine import estimate_level
from app.estimator.types import Difficulty, UNIFORM_PRIOR


def run_sequence(sequence):
    """
    Runs a sequence of (score, difficulty) observations
    through the estimator.
    """

    posterior = UNIFORM_PRIOR.copy()

    history = []

    question_count = 0

    result = None

    for score, difficulty in sequence:

        state = EstimatorInput(
            posterior=posterior,
            score=score,
            difficulty=difficulty,
            question_count=question_count,
            level_history=history,
        )

        result = estimate_level(state)

        posterior = result.posterior
        history = result.level_history
        question_count = result.question_count

        if result.stopped:
            break

    return result


def test_strong_candidate_converges_high():
    """
    Strong candidate should converge
    to level 4-5 within roughly 4-5 questions.
    """

    sequence = [
        (5, Difficulty.HARD),
        (5, Difficulty.HARD),
        (4, Difficulty.HARD),
        (5, Difficulty.MEDIUM),
        (5, Difficulty.HARD),
    ]

    result = run_sequence(sequence)

    assert result is not None

    assert result.level >= 4

    assert result.question_count <= 5

    assert result.stopped is True

    assert result.low_confidence_flag is False


def test_weak_candidate_converges_low():
    """
    Weak candidate should converge
    near level 1.
    """

    sequence = [
        (0, Difficulty.EASY),
        (1, Difficulty.EASY),
        (0, Difficulty.MEDIUM),
        (1, Difficulty.EASY),
        (0, Difficulty.EASY),
    ]

    result = run_sequence(sequence)

    assert result is not None

    assert result.level == 1

    assert result.stopped is True

    assert result.low_confidence_flag is False


def test_erratic_candidate_hits_question_cap():
    """
    Candidate never stabilizes,
    therefore reaches the 10-question cap.
    """

    sequence = [
        (5, Difficulty.HARD),
        (0, Difficulty.EASY),
        (5, Difficulty.HARD),
        (1, Difficulty.EASY),
        (4, Difficulty.HARD),
        (2, Difficulty.MEDIUM),
        (5, Difficulty.HARD),
        (0, Difficulty.EASY),
        (4, Difficulty.MEDIUM),
        (2, Difficulty.MEDIUM),
    ]

    result = run_sequence(sequence)

    assert result is not None

    assert result.question_count == 10

    assert result.stopped is True

    assert result.low_confidence_flag is True


def test_history_matches_question_count():
    """
    Every answered question should
    produce exactly one estimated level.
    """

    sequence = [
        (4, Difficulty.MEDIUM),
        (4, Difficulty.MEDIUM),
        (4, Difficulty.MEDIUM),
    ]

    result = run_sequence(sequence)

    assert len(result.level_history) == result.question_count


def test_posterior_remains_normalized():
    """
    Posterior probabilities should
    always sum to one.
    """

    sequence = [
        (3, Difficulty.MEDIUM),
        (4, Difficulty.HARD),
        (2, Difficulty.EASY),
    ]

    result = run_sequence(sequence)

    assert abs(sum(result.posterior.values()) - 1.0) < 1e-9