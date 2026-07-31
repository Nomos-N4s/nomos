"""
Agent action model and backend protocol.

The action chosen by an agent is expressed as an :class:`AgentAction` —
a frozen dataclass mirroring the style of :class:`~..models.Action`.
This keeps the core governance package free of third-party SDK imports:
the PydanticAI-specific schema lives inside the adapter and converts
to :class:`AgentAction` at the boundary.

Real-world analogy:
    ``AgentAction`` is the pilot's filed flight plan. The Parliament
    (air traffic control) reviews it; the plane cannot take off until
    the filed plan is approved.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

# The context dict keys consumed by prompt builders. Kept as module
# constants so the adapter, scenarios, and tests share one vocabulary.
OBSERVATION_KEY = "observation"
ACTION_DESCRIPTIONS_KEY = "action_descriptions"


@dataclass(frozen=True)
class AgentAction:
    """A single decision produced by an agent backend.

    Attributes:
        action_index: Index of the chosen action in the scenario's
            action enumeration (must be a non-negative integer).
        confidence: The agent's stated confidence in the choice,
            in ``[0.0, 1.0]``.
        rationale: Free-text justification, used for audit and for
            LLM-as-judge evaluation later in the pipeline.
    """

    action_index: int
    confidence: float
    rationale: str

    def __post_init__(self) -> None:
        if self.action_index < 0:
            raise ValueError(f"action_index must be >= 0, got {self.action_index}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")

    def __repr__(self) -> str:
        return f"<AgentAction {self.action_index} conf={self.confidence:.2f}>"


class AgentBackend(ABC):
    """Abstract protocol for an agent decision engine.

    Subclasses turn the current scenario state into a single
    :class:`AgentAction`. The harness feeds the resulting action into
    the Speaker (governed arm) or straight into the environment
    (ungoverned arm).

    Attributes:
        backend_id: Stable identifier recorded in traces and metrics
            (e.g. ``"stub"``, ``"pydanticai:openrouter:...``).
    """

    backend_id: str = "agent"

    @abstractmethod
    def select_action(self, context: dict[str, Any]) -> AgentAction:
        """Choose an action for the given context.

        Args:
            context: A dictionary describing the current state. The
                adapter contract only requires ``OBSERVATION_KEY``
                (the textual state render) and
                ``ACTION_DESCRIPTIONS_KEY`` (list of action strings);
                scenarios may add extra keys.

        Returns:
            The chosen :class:`AgentAction`.
        """
