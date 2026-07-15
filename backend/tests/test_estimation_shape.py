"""
Unit tests for the deterministic Bayesian Estimator and Priors Bridge.
Run with: pytest backend/tests/test_estimation_shape.py
"""
import math
from app.services.estimation import estimate_level
from app.services.priors_bridge import get_initial_posterior, blend_intake_signals

def test_posterior_normalization():
    """
    Assert that updating always results in a normalized probability distribution (sum == 1.0)
    across standard and extreme boundary cases.
    """
    initial = [0.2, 0.2, 0.2, 0.2, 0.2]
    
    # Standard case
    res = estimate_level(initial, score=4.5, difficulty=3)
    assert math.isclose(sum(res["posterior"]), 1.0, rel_tol=1e-5), "Posterior must sum to 1.0"

    # Extreme boundary case: Perfect 0 on Difficulty 1
    res_extreme = estimate_level(initial, score=0.0, difficulty=1)
    assert math.isclose(sum(res_extreme["posterior"]), 1.0, rel_tol=1e-5), "Boundary posterior must sum to 1.0"

def test_level_extraction_argmax():
    """
    Assert that the estimator correctly pulls the 'level' via argmax.
    """
    initial = [0.2, 0.2, 0.2, 0.2, 0.2]
    
    # Perfect score on the hardest difficulty should immediately shift the peak to Level 5
    res_high = estimate_level(initial, score=5.0, difficulty=5)
    assert res_high["level"] == 5, "Perfect score on Diff 5 should extract Level 5"

    # Complete failure on low difficulty should drop the peak to Level 1
    res_low = estimate_level(initial, score=0.0, difficulty=2)
    assert res_low["level"] == 1, "Zero score on Diff 2 should extract Level 1"

def test_confidence_strictly_increases_on_stable_answers():
    """
    Assert that sequential, identical performances force the distribution to tighten,
    causing the confidence metric to strictly increase over time.
    """
    initial = [0.2, 0.2, 0.2, 0.2, 0.2] # Flat, zero-confidence starting state
    
    # Turn 1
    res1 = estimate_level(initial, score=4.0, difficulty=4)
    conf1 = res1["confidence"]
    
    # Turn 2: Candidate repeats exact performance
    res2 = estimate_level(res1["posterior"], score=4.0, difficulty=4)
    conf2 = res2["confidence"]
    
    # Turn 3: Candidate repeats again
    res3 = estimate_level(res2["posterior"], score=4.0, difficulty=4)
    conf3 = res3["confidence"]
    
    # The system should become increasingly sure they belong at this level
    assert conf2 > conf1, "Confidence must increase on second consistent signal"
    assert conf3 > conf2, "Confidence must increase on third consistent signal"

def test_priors_bridge_shape():
    """
    Assert that the prior initialization creates a normalized distribution 
    peaked exactly at the target estimate.
    """
    # Start at level 3
    prior_3 = get_initial_posterior(3.0)
    assert math.isclose(sum(prior_3), 1.0, rel_tol=1e-5)
    # The highest probability (argmax) should be at index 2 (Level 3)
    assert prior_3.index(max(prior_3)) == 2

    # Start at level 5
    prior_5 = get_initial_posterior(5.0)
    # The highest probability (argmax) should be at index 4 (Level 5)
    assert prior_5.index(max(prior_5)) == 4

def test_blend_intake_signals():
    """
    Assert the 50/50 blending logic and fallbacks match the PRD spec.
    """
    # Standard 50/50 blend
    assert blend_intake_signals(self_rating=4, cv_estimate=2) == 3.0
    
    # Fallback to single signal
    assert blend_intake_signals(self_rating=4, cv_estimate=None) == 4.0
    assert blend_intake_signals(self_rating=None, cv_estimate=2) == 2.0
    
    # Default fallback
    assert blend_intake_signals(self_rating=None, cv_estimate=None) == 3.0