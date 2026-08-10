"""
Deterministic fake agent backend.

``StubBackend`` replaces the LLM with a scripted or seeded decision
engine. It exists so the full agent benchmark pipeline can run in CI
with no API key, no network access, and no cost — the same role
``baselines.py`` plays for the RL benchmark suite.

Real-world analogy:
    A flight simulator's canned autopilot: it flies the profile
    deterministically, which is exactly what you want when testing
    the control tower, not the pilot.
"""

import random
from collections.abc import Sequence
from typing import Any

from .base import AgentAction, AgentBackend


class StubBackend(AgentBackend):
    """Deterministic agent: scripted action sequence or seeded RNG.

    Args:
        script: Optional explicit sequence of action indices. When
            the script is exhausted, the last entry repeats.
        seed: Optional RNG seed. When no script is given, actions
            are drawn uniformly from ``action_count`` options using
            this seed (default 0 — same seed reproduces the same
            trajectory).
    """

    backend_id = "stub"

    def __init__(self, script: Sequence[int] | None = None, seed: int = 0):
        self._script = list(script) if script is not None else None
        self._seed = seed
        self._rng = random.Random(seed)
        self._calls = 0

    def reset(self) -> None:
        """Restore the stub to its just-constructed state.

        Resets the call counter and re-seeds the RNG so a paired arm
        replays the identical action stream.
        """
        self._rng = random.Random(self._seed)
        self._calls = 0

    def select_action(self, context: dict[str, Any]) -> AgentAction:
        """Return the next scripted (or seeded) action.

        Args:
            context: Unused by the stub; accepted for protocol
                compatibility.

        Returns:
            An :class:`AgentAction` with a fixed rationale so traces
            are stable across runs.
        """
        if self._script is not None:
            index = self._script[min(self._calls, len(self._script) - 1)]
        else:
            index = self._rng.randrange(len(context["action_descriptions"]))
        self._calls += 1
        return AgentAction(action_index=index, confidence=1.0, rationale="stub")
