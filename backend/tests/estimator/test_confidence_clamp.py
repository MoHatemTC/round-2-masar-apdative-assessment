"""
Unit tests for confidence clamp logic.
"""

import pytest

from app.estimator.types import (
    CONFIDENCE_CLAMP,
    DEFAULT_CONFIDENCE_CAP,
    confidence_cap,
)


@pytest.mark.parametrize(
    "questions,expected",
    [
        (1, 0.50),
        (2, 0.70),
        (3, 0.85),
        (4, 0.97),
        (5, 0.97),
        (8, 0.97),
        (10, 0.97),
        (25, 0.97),
    ],
)
def test_confidence_cap_values(
    questions,
    expected,
):
    assert confidence_cap(questions) == expected


def test_confidence_table_contents():
    assert CONFIDENCE_CLAMP == {
        1: 0.50,
        2: 0.70,
        3: 0.85,
    }


def test_default_cap():
    assert DEFAULT_CONFIDENCE_CAP == 0.97


def test_cap_never_exceeds_default():
    for q in range(4, 20):
        assert confidence_cap(q) == DEFAULT_CONFIDENCE_CAP