"""
prove — Formal prediction verification for the Governance Layer.

Each prediction maps a claim from Chapters 2-4 to an executable test.
Run with: python -m src.governance.prove.runner
"""

from .predictions import PredictionResult, ALL_PREDICTIONS
from .runner import run_all

__all__ = [
    "PredictionResult",
    "ALL_PREDICTIONS",
    "run_all",
]
