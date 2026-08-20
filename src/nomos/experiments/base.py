"""
Abstract scenario base class for all governance experiments.

Each scenario defines:
- A ``reset()`` for initialising the world state
- A ``get_proposals()`` method that generates proposals from the current state
- An optional ``compute_reward()`` and ``transition()`` for simple scenarios
- Or a ``_run_step()`` override for full step-level control

The ``step()`` method ties these together, running a full governance cycle
via the Speaker and recording metrics automatically.

Real-world analogy:
    A flight simulator for a pilot (the governance system). Each scenario
    (engine failure, crosswind landing, bird strike) tests different
    aspects of the pilot's decision-making in a controlled environment.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, ClassVar

from ..models import GovernanceDecision, Proposal
from ..speaker import SpeakerStateMachine


@dataclass
class StepResult:
    """The result of a single governance experiment step.

    Attributes:
        decision: The :class:`~..models.GovernanceDecision` produced.
        state: The next world state (depends on the scenario).
        reward: The reward earned this step.
        metrics_delta: Additional metrics to update (e.g. violations).
        log_entries: Human-readable log lines for this step.
    """

    decision: GovernanceDecision
    state: Any
    reward: float = 0.0
    metrics_delta: dict[str, Any] = field(default_factory=dict)
    log_entries: list[str] = field(default_factory=list)


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
        governance_latencies: Time spent inside the governance cycles a
            step ran (seconds), excluding proposal generation, reward,
            and environment transition. One entry per step that ran at
            least one cycle, so a run whose decisions all come from an
            external baseline records none.
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

    Subclasses must implement ``reset`` and ``get_proposals``.
    Override either:

    - ``_run_step(state, ...)`` for full step-level control, or
    - The optional hooks ``compute_reward()`` + ``transition()``
      for simple scenarios (the default ``_run_step`` calls those).

    The ``step()`` method is the public API and must not be overridden
    — it provides centralized bookkeeping (history, metrics).

    Args:
        speaker: The :class:`~..speaker.SpeakerStateMachine` instance
            that runs the governance cycle.
    """

    #: Action names a fixed rule-based filter forbids in this scenario.
    #:
    #: This is the blocklist the benchmark runner hands to
    #: :class:`~..benchmarks.baselines.StaticMasking`, the ablation arm that
    #: asks whether a fixed rule can match the Parliament's adaptive vetoing.
    #: Only actions whose harm is a property of the *action* belong here. An
    #: action that is harmful in some world states and benign in others cannot
    #: be expressed by a name-level filter, so it must not be listed.
    #:
    #: An empty blocklist therefore means the static-masking ablation is not
    #: expressible for this scenario. It is not a default to be left unset:
    #: with nothing blocked ``StaticMasking`` degenerates into
    #: :class:`~..benchmarks.baselines.MonolithicRL`, so the runner skips the
    #: arm instead of publishing the same numbers under a second name.
    STATIC_BLOCKLIST: ClassVar[frozenset[str]] = frozenset()

    def __init__(self, speaker: SpeakerStateMachine):
        self.speaker = speaker
        self.metrics = ExperimentMetrics()
        self._history: list[StepResult] = []
        self._latency_window_open: bool = False

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

    # ------------------------------------------------------------------
    # Required abstraction — override this OR both hooks below
    # ------------------------------------------------------------------

    def _run_step(
        self,
        state: Any,
        *,
        decision_class: str = "routine",
        external_decision: GovernanceDecision | None = None,
    ) -> StepResult:
        """Execute one step of the scenario.

        Override this for full step-level control (e.g. DeadlockMaze's
        phase transitions, GridWorld's poison timers).

        The default implementation delegates to ``compute_reward()``
        and ``transition()`` for simple scenarios.
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
        return StepResult(decision=decision, state=next_state, reward=reward)

    # ------------------------------------------------------------------
    # Optional hooks — override these if your scenario is simple
    # ------------------------------------------------------------------

    def compute_reward(self, state: Any, decision: GovernanceDecision) -> float:
        """Compute the reward for a given decision.

        Only called when ``_run_step()`` is not overridden.

        Args:
            state: The current world state (before transition).
            decision: The decision produced by the governance cycle.

        Returns:
            The reward value for this step.
        """
        return 0.0

    def transition(self, state: Any, decision: GovernanceDecision) -> Any:
        """Update the world state based on a decision.

        Only called when ``_run_step()`` is not overridden.

        Args:
            state: The current world state.
            decision: The decision to apply.

        Returns:
            The next world state.
        """
        return state

    def contract_snapshot(self) -> list[dict[str, Any]]:
        """Per-step snapshot of the scenario's Ulysses Contracts.

        Override in scenarios that manage a
        :class:`~..contracts.contract.ContractRegistry` so audit traces
        can record the contract lifecycle (PROPOSED → ENACTED → ACTIVE /
        BREACHED) aligned with steps. The default reports no contracts.

        Returns:
            One dict per registered contract with ``contract_id``,
            ``state``, ``restricted_indices``, and ``timelock_blocks``.
        """
        return []

    # ------------------------------------------------------------------
    # Public API — do not override
    # ------------------------------------------------------------------

    @contextmanager
    def governance_latency_window(self) -> Iterator[None]:
        """Record the governance-cycle time spent inside the block.

        The figure is read off the Speaker's own counters rather than
        timed around the block, so it covers the governance cycles
        alone and not the surrounding scenario work. One entry is
        appended to ``metrics.governance_latencies`` if at least one
        cycle ran inside the block, and none otherwise.

        Re-entrant: a nested window is a no-op, so a caller that runs
        the cycle itself and hands the result to :meth:`step` as
        ``external_decision`` opens one window around both and still
        gets exactly one entry for the step.

        Yields:
            ``None``. The entry, if any, is appended on exit.
        """
        if self._latency_window_open:
            yield
            return

        cycles_before = self.speaker.cycle_count
        seconds_before = self.speaker.cycle_seconds_total
        self._latency_window_open = True
        try:
            yield
        finally:
            self._latency_window_open = False
            if self.speaker.cycle_count > cycles_before:
                self.metrics.governance_latencies.append(
                    self.speaker.cycle_seconds_total - seconds_before
                )

    def step(
        self,
        state: Any,
        *,
        decision_class: str = "routine",
        external_decision: GovernanceDecision | None = None,
    ) -> StepResult:
        """Run a single governance experiment step.

        Centralized bookkeeping: appends to history, updates metrics.
        Delegates to ``_run_step()`` for scenario-specific logic.

        The step runs inside :meth:`governance_latency_window`, so a
        step whose cycle runs in ``_run_step()`` records its latency
        here and a step that runs no cycle at all (``external_decision``
        supplied by a baseline) records none. A caller that runs the
        cycle itself opens the window earlier and is credited there.

        Args:
            state: The current world state.
            decision_class: Classification for the governance cycle
                (see :class:`~..speaker.SpeakerStateMachine`).
            external_decision: Optional pre-computed decision (for
                baseline comparisons like MonolithicRL).

        Returns:
            A :class:`StepResult` with the decision, next state, and reward.
        """
        with self.governance_latency_window():
            result = self._run_step(
                state,
                decision_class=decision_class,
                external_decision=external_decision,
            )

        self._history.append(result)
        self.metrics.total_steps += 1
        self.metrics.total_reward += result.reward
        if result.decision.is_default:
            self.metrics.deadlock_count += 1
        if result.decision.vetoed_by:
            self.metrics.veto_count += len(result.decision.vetoed_by)
        for key, value in result.metrics_delta.items():
            setattr(self.metrics, key, getattr(self.metrics, key, 0) + value)

        return result

    @property
    def history(self) -> list[StepResult]:
        """The full step history as an immutable list."""
        return list(self._history)
