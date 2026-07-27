"""
Abstract scenario base class for all governance experiments.

Each scenario defines:
- A `reset()` for initialising the world state
- A `get_proposals()` method that generates proposals from the current state
- A `compute_reward()` function for the scenario's reward signal
- A `transition()` function for updating world state

The `step()` method ties these together, running a full governance cycle
via the Speaker and recording metrics automatically.

Real-world analogy:
    A flight simulator for a pilot (the governance system). Each scenario
    (engine failure, crosswind landing, bird strike) tests different
    aspects of the pilot's decision-making in a controlled environment.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..models import GovernanceDecision, Proposal
from ..speaker import SpeakerStateMachine


@dataclass
class StepResult:
    """The result of a single governance experiment step.

    Attributes:
        decision: The :class:`~..models.GovernanceDecision` produced.
        state: The next world state (depends on the scenario).
        reward: The reward earned this step.
    """

    decision: GovernanceDecision
    state: Any
    reward: float = 0.0


@dataclass
class ExperimentMetrics:
    """Aggregated metrics across an entire experiment run.

    Attributes:
        total_steps: Number of steps executed.
        total_reward: Cumulative reward (raw, not discounted).
        constraint_violations: Number of actions that violated constraints.
        deadlock_count: Number of default (no-decision) outcomes.
        contract_revocations: Number of Ulysses Contracts revoked.
        veto_count: Total number of vetoes applied.
        falsification_count: Number of formal-predicate falsifications.
        identity_drift: Per-step cosine distance from the identity vector.
        governance_latencies: Per-step governance cycle duration (seconds).
    """

    total_steps: int = 0
    total_reward: float = 0.0
    constraint_violations: int = 0
    deadlock_count: int = 0
    contract_revocations: int = 0
    veto_count: int = 0
    falsification_count: int = 0
    identity_drift: list[float] = field(default_factory=list)
    governance_latencies: list[float] = field(default_factory=list)


class ExperimentScenario(ABC):
    """Abstract base for a governance experiment scenario.

    Subclasses must implement ``reset``, ``get_proposals``,
    ``compute_reward``, and ``transition``. The ``step`` method
    is provided and orchestrates the full governance cycle.

    Args:
        speaker: The :class:`~..speaker.SpeakerStateMachine` instance
            that runs the governance cycle.
    """

    def __init__(self, speaker: SpeakerStateMachine):
        self.speaker = speaker
        self.metrics = ExperimentMetrics()
        self._history: list[StepResult] = []

    @abstractmethod
    def reset(self):
        """Reset the scenario to its initial state."""

    @abstractmethod
    def get_proposals(self, state: Any) -> list[Proposal]:
        """Generate proposals based on the current world state.

        Args:
            state: The current scenario state.

        Returns:
            A list of :class:`~..models.Proposal` instances for the
            governance cycle to process.
        """

    @abstractmethod
    def compute_reward(self, state: Any, decision: GovernanceDecision) -> float:
        """Compute the reward for a given decision.

        Args:
            state: The current world state (before transition).
            decision: The decision produced by the governance cycle.

        Returns:
            The reward value for this step.
        """

    @abstractmethod
    def transition(self, state: Any, decision: GovernanceDecision) -> Any:
        """Update the world state based on a decision.

        Args:
            state: The current world state.
            decision: The decision to apply.

        Returns:
            The next world state.
        """

    def step(
        self,
        state: Any,
        decision_class: str = "routine",
        external_decision: GovernanceDecision | None = None,
    ) -> StepResult:
        """Run a single governance experiment step.

        Args:
            state: The current world state.
            decision_class: Classification for the governance cycle
                (see :class:`~..speaker.SpeakerStateMachine`).
            external_decision: Optional pre-computed decision (for
                baseline comparisons like MonolithicRL).

        Returns:
            A :class:`StepResult` with the decision, next state, and reward.
        """
        proposals = self.get_proposals(state)
        if external_decision is not None:
            decision = external_decision
        else:
            decision = self.speaker.run_governance_cycle(
                state=state,
                raw_proposals=proposals,
                decision_class=decision_class,
            )
        reward = self.compute_reward(state, decision)
        next_state = self.transition(state, decision)

        result = StepResult(decision=decision, state=next_state, reward=reward)
        self._history.append(result)

        self.metrics.total_steps += 1
        self.metrics.total_reward += reward
        if decision.is_default:
            self.metrics.deadlock_count += 1
        if decision.vetoed_by:
            self.metrics.veto_count += len(decision.vetoed_by)

        return result

    @property
    def history(self) -> list[StepResult]:
        """The full step history as an immutable list."""
        return list(self._history)
