"""
Priors Bridge for the Adaptive Assessment Engine.

This module initializes the starting Bayesian belief state (the prior) based on 
the candidate's blended intake data (self-rating and CV estimates).
"""
from __future__ import annotations
import math

def get_initial_posterior(prior_estimate: float) -> list[float]:
    """
    Generate a 5-way probability distribution peaked at the `prior_estimate` 
    but with a wide spread to simulate a "low confidence" starting state.
    
    Args:
        prior_estimate: float between 1.0 and 5.0 (e.g., blended CV/self-rating).
        
    Returns:
        list[float]: A normalized 5-element array representing probabilities for levels 1-5.
    """
    import math # Ensure math is imported at the top of your file
    
    # Bound the estimate to the valid 1.0 - 5.0 scale
    safe_estimate = max(1.0, min(5.0, float(prior_estimate)))
    
    # To create a genuinely "low confidence" flat start that doesn't incorrectly
    # over-index on the edges, we mix a uniform distribution (flat) with a slight peak.
    base_uniform_weight = 1.0
    peak_weight_multiplier = 0.2
    
    # 1. Calculate raw weights based on distance from the prior estimate
    raw_weights = []
    for i in range(5):
        level = i + 1
        # Slight bump at the estimated level using standard Gaussian
        bump = math.exp(-((level - safe_estimate) ** 2) / 1.0)
        # Mix flat distribution with the bump
        weight = base_uniform_weight + (peak_weight_multiplier * bump)
        raw_weights.append(weight)
        
    # 2. Normalize so the initial prior sums exactly to 1.0
    total_weight = sum(raw_weights)
    
    if total_weight == 0:
        return [0.2, 0.2, 0.2, 0.2, 0.2]
        
    return [w / total_weight for w in raw_weights]

def blend_intake_signals(self_rating: int | None, cv_estimate: int | None) -> float:
    """
    Calculate the starting integer/float prior from available candidate data.
    Follows the architectural requirement to blend 50/50, fallback to self-rating alone, 
    or default to 3 if neither exists.
    
    Args:
        self_rating: The 1-5 candidate self-rating (or None).
        cv_estimate: The 1-5 LLM-estimated level from the CV (or None).
        
    Returns:
        float: The starting estimate to feed into the initial posterior.
    """
    if self_rating is not None and cv_estimate is not None:
        return round(0.5 * cv_estimate + 0.5 * self_rating, 1)
    
    if self_rating is not None:
        return float(self_rating)
        
    if cv_estimate is not None:
        return float(cv_estimate)
        
    # Default fallback per documentation
    return 3.0