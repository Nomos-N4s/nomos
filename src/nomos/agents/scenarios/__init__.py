"""
LLM-native scenarios for the agent validation benchmark.

Each scenario re-expresses an RL experiment with a textual observation
renderer and an LLM-readable action space, so a real language-model
agent exercises the same governance mechanisms by reasoning rather
than table lookup:

- :class:`~.grid_world_llm.GridWorldLLM` — poison discovery by
  exploration (Safety veto, Ch2 P1 / Ch3 P2)
- :class:`~.temptation_bank_llm.TemptationBankLLM` — voluntary Ulysses
  self-binding chosen at runtime (contract, Ch2 P3 / Ch3 P1)
- :class:`~.drift_lab_llm.DriftLabLLM` — value re-negotiation pressure
  (Integrity veto, Ch4 P9)
- :class:`~.deadlock_maze_llm.DeadlockMazeLLM` — conflicting standing
  orders (deadlock breaker liveness, Ch4 P12)

Every scenario pairs with :class:`~..harness.GovernorComparisonHarness`
via ``action_space()`` and ``render_observation()``.

Real-world analogy:
    Four flight-deck exercises for the same pilot: terrain hazards,
    temptation, ethics pressure, and procedural gridlock.
"""

from .base import LLMScenario
from .deadlock_maze_llm import DeadlockMazeLLM
from .drift_lab_llm import DriftLabLLM
from .grid_world_llm import GridWorldLLM
from .temptation_bank_llm import TemptationBankLLM

__all__ = [
    "LLMScenario",
    "GridWorldLLM",
    "TemptationBankLLM",
    "DriftLabLLM",
    "DeadlockMazeLLM",
]
