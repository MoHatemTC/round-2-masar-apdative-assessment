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
    # Bound the estimate to the valid 1.0 - 5.0 scale
    safe_estimate = max(1.0, min(5.0, float(prior_estimate)))
    
    # A larger spread factor flattens the curve, increasing variance (lowering confidence).
    # Using 2.0 creates a wide base, ensuring the engine starts with healthy uncertainty.
    spread_factor = 2.0 
    
    # 1. Calculate raw weights based on distance from the prior estimate
    raw_weights = []
    for i in range(5):
        level = i + 1
        # Gaussian distribution formula modified for a wide spread
        weight = math.exp(-((level - safe_estimate) ** 2) / spread_factor)
        raw_weights.append(weight)
        
    # 2. Normalize so the initial prior sums exactly to 1.0
    total_weight = sum(raw_weights)
    
    if total_weight == 0:
        return [0.2, 0.2, 0.2, 0.2, 0.2]
        
    return [round(w / total_weight, 4) for w in raw_weights]

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