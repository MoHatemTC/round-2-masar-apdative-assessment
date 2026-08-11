"""
Unit tests for the deterministic Bayesian Estimator and Priors Bridge.
Run with: pytest backend/tests/test_estimation_shape.py
"""
import math
from app.estimator.contract import EstimatorInput
from app.estimator.types import Difficulty
from app.services.estimation import estimate_level
from app.services.priors_bridge import get_initial_posterior, blend_intake_signals

def test_posterior_normalization():
    """
    Assert that updating always results in a normalized probability distribution (sum == 1.0)
    across standard and extreme boundary cases.
    """
    initial_list = [0.2, 0.2, 0.2, 0.2, 0.2]
    initial_dict = {i+1: p for i, p in enumerate(initial_list)}
    
    # Standard case
    state1 = EstimatorInput(posterior=initial_dict, score=4.5, difficulty=Difficulty.MEDIUM, question_count=0)
    res = estimate_level(state1)
    assert math.isclose(sum(res.posterior.values()), 1.0, rel_tol=1e-5), "Posterior must sum to 1.0"

    # Extreme boundary case: Perfect 0 on Difficulty 1
    state2 = EstimatorInput(posterior=initial_dict, score=0.0, difficulty=Difficulty.EASY, question_count=0)
    res_extreme = estimate_level(state2)
    assert math.isclose(sum(res_extreme.posterior.values()), 1.0, rel_tol=1e-5), "Boundary posterior must sum to 1.0"

def test_level_extraction_argmax():
    """
    Assert that the estimator correctly pulls the 'level' via argmax.
    """
    initial_list = [0.2, 0.2, 0.2, 0.2, 0.2]
    initial_dict = {i+1: p for i, p in enumerate(initial_list)}
    
    # Perfect score on the hardest difficulty should immediately shift the peak to Level 5
    state1 = EstimatorInput(posterior=initial_dict, score=5.0, difficulty=Difficulty.HARD, question_count=0)
    res_high = estimate_level(state1)
    assert res_high.level == 5, "Perfect score on Diff 5 should extract Level 5"

    # Complete failure on low difficulty should drop the peak to Level 1
    state2 = EstimatorInput(posterior=initial_dict, score=0.0, difficulty=Difficulty.EASY, question_count=0)
    res_low = estimate_level(state2)
    assert res_low.level == 1, "Zero score on Diff 2 should extract Level 1"

def test_confidence_strictly_increases_on_stable_answers():
    """
    Assert that sequential, identical performances force the distribution to tighten,
    causing the confidence metric to strictly increase over time.
    """
    initial_list = [0.2, 0.2, 0.2, 0.2, 0.2] # Flat, zero-confidence starting state
    initial_dict = {i+1: p for i, p in enumerate(initial_list)}
    
    # Turn 1
    state1 = EstimatorInput(posterior=initial_dict, score=4.0, difficulty=Difficulty.HARD, question_count=0)
    res1 = estimate_level(state1)
    conf1 = res1.confidence
    
    # Turn 2: Candidate repeats exact performance
    state2 = EstimatorInput(posterior=res1.posterior, score=4.0, difficulty=Difficulty.HARD, question_count=1)
    res2 = estimate_level(state2)
    conf2 = res2.confidence
    
    # Turn 3: Candidate repeats again
    state3 = EstimatorInput(posterior=res2.posterior, score=4.0, difficulty=Difficulty.HARD, question_count=2)
    res3 = estimate_level(state3)
    conf3 = res3.confidence
    
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

def test_prior_confidence_edges_not_overconfident():
    """
    Assert that edge priors (e.g. 5.0) do not start with higher confidence 
    than centered priors (e.g. 3.0), and that both start genuinely flat (~0.5).
    """
    def calc_conf(prior):
        mean = sum((i+1)*p for i, p in enumerate(prior))
        var = sum(p * ((i+1 - mean)**2) for i, p in enumerate(prior))
        return 1.0 - (var / 4.0)

    conf_3 = calc_conf(get_initial_posterior(3.0))
    conf_5 = calc_conf(get_initial_posterior(5.0))
    
    # Both should be relatively flat (confidence around 0.5)
    assert conf_3 < 0.6, "Centered prior is too confident"
    assert conf_5 < 0.6, "Edge prior is too confident"
    
    # Edge should NOT be strictly more confident than center due to array cutoff
    assert conf_5 <= conf_3, f"Edge prior ({conf_5}) is more confident than center ({conf_3})"
    
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