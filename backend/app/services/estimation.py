"""
Bayesian Estimator for the Adaptive Assessment Engine.

This module provides pure, deterministic mathematical functions to update the 
system's belief state regarding a candidate's competency level. It relies exclusively 
on statistical variance and Gaussian penalties without any external LLM dependencies.
"""
from __future__ import annotations
import math

def _expected_score(level: int, difficulty: int) -> float:
    """
    Calculate the expected score (0.0 to 5.0) for a candidate at a given level 
    answering a question of a specific difficulty.
    """
    return max(0.0, min(5.0, 3.0 + (level - difficulty) * 1.5))

def _likelihood_weight(expected_score: float, actual_score: float) -> float:
    """
    Calculate the likelihood weight using a standard Gaussian distribution penalty.
    The closer the actual score is to the expected score, the closer the weight is to 1.0.
    """
    return math.exp(-((actual_score - expected_score) ** 2) / 2.0)

def estimate_level(posterior: list[float], score: float, difficulty: int) -> dict:
    """
    DETERMINISTIC Bayesian update. Given the running `posterior` over levels {1..5}, 
    the latest answer `score` (0-5), and the question `difficulty` (1..5), 
    returns the updated belief state, the extracted level, and the confidence metric.
    
    Args:
        posterior: list[float] of length 5, representing probabilities for levels 1-5.
        score: float between 0.0 and 5.0 representing the graded answer score.
        difficulty: int between 1 and 5 representing the question difficulty.
        
    Returns:
        dict containing:
            - 'posterior': list[float], the normalized updated probabilities.
            - 'level': int (1..5), the argmax of the new posterior.
            - 'confidence': float (0.0..1.0), derived from the normalized spread.
    """
    # 1. Calculate Expected Scores and Likelihood Weights for each level (1 to 5)
    likelihoods = []
    for i in range(5):
        level = i + 1
        expected = _expected_score(level, difficulty)
        weight = _likelihood_weight(expected, score)
        likelihoods.append(weight)
        
    # 2. Apply Bayesian Update (Multiply prior by likelihood)
    raw_posterior = [posterior[i] * likelihoods[i] for i in range(5)]
    
    # 3. Normalize the new posterior so it exactly sums to 1.0
    total_probability = sum(raw_posterior)
    if total_probability == 0:
        # Fallback to a flat distribution in extreme mathematical edge cases
        normalized_posterior = [0.2] * 5 
    else:
        normalized_posterior = [p / total_probability for p in raw_posterior]
        
    # 4. Extract the Level (argmax)
    # Find the index of the maximum probability
    max_prob = -1.0
    best_index = 0
    for i, prob in enumerate(normalized_posterior):
        if prob > max_prob:
            max_prob = prob
            best_index = i
            
    # Convert 0-indexed array position to 1-5 level scale
    current_level = best_index + 1
    
    # 5. Calculate Confidence (1 - normalized variance)
    # First find the expected mean (center of mass)
    mean_level = sum((i + 1) * prob for i, prob in enumerate(normalized_posterior))
    
    # Then calculate the statistical variance
    variance = sum(prob * (((i + 1) - mean_level) ** 2) for i, prob in enumerate(normalized_posterior))
    
    # Max variance for a 5-level scale is 4.0. Confidence is the inverse of the normalized variance.
    confidence = max(0.0, min(1.0, 1.0 - (variance / 4.0)))
    
    return {
        "posterior": normalized_posterior,
        "level": current_level,
        "confidence": round(confidence, 4)
    }