"""
prove — Formal prediction verification for Nomos.

Each prediction maps a claim from Chapters 2-4 to an executable test.
Run with: python -m src.nomos.prove.runner
"""

from .predictions import ALL_PREDICTIONS, PredictionResult
from .runner import run_all

__all__ = [
    "PredictionResult",
    "ALL_PREDICTIONS",
    "run_all",
]
