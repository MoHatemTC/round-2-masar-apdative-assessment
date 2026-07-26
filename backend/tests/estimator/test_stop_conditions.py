"""
Unit tests for estimator stopping rules.
"""

from app.estimator.stop_conditions import (
    CONFIDENCE_TARGET,
    QUESTION_CAP,
    STABLE_STREAK,
    confidence_reached,
    stable_level,
    question_cap,
    evaluate_stop_conditions,
)


def test_confidence_reached_true():
    assert confidence_reached(0.90) is True
    assert confidence_reached(0.95) is True


def test_confidence_reached_false():
    assert confidence_reached(0.89) is False
    assert confidence_reached(0.50) is False


def test_stable_level_true():
    assert stable_level([3, 3, 3]) is True
    assert stable_level([1, 2, 4, 4, 4]) is True


def test_stable_level_false():
    assert stable_level([]) is False
    assert stable_level([2]) is False
    assert stable_level([2, 2]) is False
    assert stable_level([2, 2, 3]) is False
    assert stable_level([1, 1, 2, 2]) is False


def test_question_cap_true():
    assert question_cap(QUESTION_CAP) is True
    assert question_cap(QUESTION_CAP + 2) is True


def test_question_cap_false():
    assert question_cap(0) is False
    assert question_cap(5) is False
    assert question_cap(QUESTION_CAP - 1) is False


def test_stop_by_confidence():
    stopped, low = evaluate_stop_conditions(
        history=[2, 3],
        confidence=0.92,
        question_count=2,
    )

    assert stopped is True
    assert low is False


def test_stop_by_stable_level():
    stopped, low = evaluate_stop_conditions(
        history=[4, 4, 4],
        confidence=0.72,
        question_count=3,
    )

    assert stopped is True
    assert low is False


def test_stop_by_question_cap():
    stopped, low = evaluate_stop_conditions(
        history=[1, 2, 3, 2, 4, 3, 2, 1, 3, 2],
        confidence=0.67,
        question_count=10,
    )

    assert stopped is True
    assert low is True


def test_continue_assessment():
    stopped, low = evaluate_stop_conditions(
        history=[2, 3],
        confidence=0.74,
        question_count=2,
    )

    assert stopped is False
    assert low is False