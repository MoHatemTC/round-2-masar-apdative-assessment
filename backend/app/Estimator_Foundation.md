Bayesian Estimator & Convergence Module

Overview

This module serves as the deterministic mathematical core for the Adaptive Competency Assessment engine. It is responsible for updating the system's belief about a candidate's skill level after every answered question.

Per the architectural requirements, this module is strictly deterministic, stateless, and contains zero LLM or external network dependencies. It operates purely on statistical variance and Bayesian probability arrays.

Files Implemented

As part of the Bayesian Estimator vertical slice, the following files were implemented:

services/estimation.py - The core engine exposing the estimate_level(posterior, score, difficulty) contract.

Calculates Likelihood Weights using a Gaussian penalty based on Expected vs. Actual scores.

Performs the Bayesian update and normalizes the posterior array.

Extracts the current level via argmax and calculates confidence via normalized mathematical variance.

services/priors_bridge.py

Bridges intake data to the estimator.

Blends candidate self-ratings and CV estimates (50/50 split with fallbacks).

Generates the initial 5-element probability array, utilizing a wide spread factor to ensure the system starts peaked at the prior estimate but securely in a "low confidence" state.

../tests/test_estimation_shape.py

Exhaustive unit test suite verifying the mathematical integrity of the module.

Mathematical Approach

Instead of tracking a single integer for a candidate's level, the system tracks a 5-way probability distribution over levels {1, 2, 3, 4, 5}.

Expected Score: Calculated dynamically as $E_L = \max(0, \min(5, 3 + (L - Difficulty) \times 1.5))$

Likelihood: Determines how close the candidate's actual score was to the expected score using a Gaussian curve: $W_L = e^{-\frac{(Score - E_L)^2}{2}}$

Level Derivation: The estimated level is simply the 1-indexed position of the highest probability in the array (argmax(posterior)).

Confidence Derivation: Calculated by measuring the statistical variance (spread) of the array. The maximum variance on a 5-level scale is 4.0. Confidence is returned as $1.0 - (\frac{Var}{4.0})$, ensuring confidence trends upward as the distribution tightens.

How to Run Tests

The test suite aggressively tests normalization boundaries, argmax logic, and convergence direction. Run the tests from the backend/ directory:

python -m pytest tests/test_estimation_shape.py -v


Test Coverage:

test_posterior_normalization: Ensures arrays never drift from a perfect 1.0 sum, even in extreme edge cases.

test_level_extraction_argmax: Proves scores correctly shift the peak probability.

test_confidence_strictly_increases_on_stable_answers: Proves that consistent answers mathematically force the confidence metric upward toward the 0.90 convergence target.

test_priors_bridge_shape: Verifies the wide-spread initialization.

test_blend_intake_signals: Verifies the 50/50 logic and fallbacks.