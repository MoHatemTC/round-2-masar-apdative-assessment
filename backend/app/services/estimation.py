"""
Estimator service wrapper.

The actual Bayesian estimator lives in app.estimator.

This module exists only so older imports continue to work.
"""

from app.estimator.engine import estimate_level

__all__ = ["estimate_level"]