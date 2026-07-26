import pytest

from app.estimator.engine import _confidence


def test_uniform_posterior_has_low_confidence():
    posterior = {
        1: 0.2,
        2: 0.2,
        3: 0.2,
        4: 0.2,
        5: 0.2,
    }

    assert _confidence(posterior) == pytest.approx(0.0)


def test_confidence_increases_for_concentrated_posterior():
    weak = {
        1: 0.30,
        2: 0.25,
        3: 0.20,
        4: 0.15,
        5: 0.10,
    }

    strong = {
        1: 0.02,
        2: 0.03,
        3: 0.90,
        4: 0.03,
        5: 0.02,
    }

    assert _confidence(strong) > _confidence(weak)


def test_fully_concentrated_posterior_has_max_confidence():
    posterior = {
        1: 0.0,
        2: 0.0,
        3: 1.0,
        4: 0.0,
        5: 0.0,
    }

    assert _confidence(posterior) == pytest.approx(1.0)