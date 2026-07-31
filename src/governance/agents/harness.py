"""
Governed vs ungoverned comparison harness.

Runs the same agent backend through two arms with identical seeds and
observations:

- **Ungoverned arm**: the agent's action goes straight to the
  environment. The Speaker is bypassed entirely.
- **Governed arm**: the agent's action becomes a proposal submitted to
  the Speaker, whose members score, veto, and vote on it before the
  resulting decision reaches the environment.

Every step is logged with the agent's raw action, the governance
decision, and — on veto — the counterfactual: what the agent's action
would have done without governance.

Real-world analogy:
    A paired clinical trial. The same patient protocol (seed) runs in
    two groups: one receives the treatment (governance), one a placebo
    (no governance). Any difference in outcome is attributable to the
    treatment because the trial arms are otherwise identical.
"""

import time
from abc import ABC
from collections.abc import Callable, Sequence
from copy import copy
from dataclasses import dataclass, field
from typing import Any, cast

from ..committee.base import ParliamentMember
from ..experiments.base import ExperimentMetrics, ExperimentScenario
from ..models import GovernanceDecision, PriorityTag, Proposal
from ..speaker import SpeakerStateMachine
from .base import AgentBackend
from .prompts import build_context

#: ``member_id`` used for proposals authored by the agent.
AGENT_MEMBER_ID = "agent"


# ----------------------------------------------------------------------
# Action space
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class ActionSpaceEntry:
    """One entry in an agent action space.

    Attributes:
        action: The scenario-level action value the entry maps to
            (e.g. ``"take_loan"`` for :class:`TemptationBank`).
        description: Human-readable description shown to the LLM.
        metadata: Proposal metadata carried when the governed arm
            submits this action to the Speaker (e.g. ``risk``,
            ``expected_reward``) so members can score it. May be a
            static dict, or a callable ``(scenario) -> dict`` for
            state-dependent metadata (tile risk, drift-adjusted
            reward) that must be computed at submission time.
    """

    action: Any
    description: str
    metadata: dict[str, Any] | Callable[[Any], dict[str, Any]] = field(default_factory=dict)


class ActionSpace:
    """Maps agent action indices to scenario actions and descriptions.

    Args:
        entries: The action entries, index-aligned with the agent's
            ``action_index`` output.
    """

    def __init__(self, entries: Sequence[ActionSpaceEntry]):
        self.entries = list(entries)
        if not self.entries:
            raise ValueError("ActionSpace requires at least one entry")

    def __len__(self) -> int:
        return len(self.entries)

    def descriptions(self) -> list[str]:
        """Return the LLM-readable descriptions, index-aligned."""
        return [entry.description for entry in self.entries]

    def entry(self, index: int) -> ActionSpaceEntry:
        """Return the entry for an agent action index.

        Args:
            index: The agent's chosen action index.

        Returns:
            The matching :class:`ActionSpaceEntry`.

        Raises:
            IndexError: If the index is outside the action space.
        """
        if not 0 <= index < len(self.entries):
            raise IndexError(
                f"action_index {index} outside action space of size {len(self.entries)}"
            )
        return self.entries[index]


# ----------------------------------------------------------------------
# Log entries and results
# ----------------------------------------------------------------------


@dataclass
class StepLogEntry:
    """One step of one arm, fully auditable.

    Attributes:
        step: Step number within the episode.
        arm: ``"governed"`` or ``"ungoverned"``.
        observation: The observation text the agent saw.
        agent_action_index: Index chosen by the agent.
        confidence: Agent's stated confidence in the choice.
        rationale: Agent's free-text justification.
        proposed_action: The scenario action the agent's choice maps to.
        decision_action: The action actually applied to the environment.
        vetoed: True if the Speaker blocked the agent's action.
        is_default: True if the Speaker fell back to the default action.
        would_have_been: The agent's action (the counterfactual) when
            the governed arm vetoed it, else None.
        reward: Reward earned this step.
        violations_delta: Constraint violations this step.
        select_latency: Wall-clock seconds spent in the backend's
            ``select_action`` call (the LLM call for live adapters).
    """

    step: int
    arm: str
    observation: str
    agent_action_index: int
    confidence: float
    rationale: str
    proposed_action: Any
    decision_action: Any
    vetoed: bool
    is_default: bool
    would_have_been: Any | None
    reward: float
    violations_delta: int
    select_latency: float = 0.0


@dataclass
class ArmResult:
    """The full trace and metrics of a single arm run.

    Attributes:
        arm: ``"governed"`` or ``"ungoverned"``.
        log: Per-step :class:`StepLogEntry` records.
        metrics: The scenario's aggregated
            :class:`~..experiments.base.ExperimentMetrics`.
    """

    arm: str
    log: list[StepLogEntry]
    metrics: ExperimentMetrics

    @property
    def total_reward(self) -> float:
        """Cumulative reward across the episode."""
        return self.metrics.total_reward

    @property
    def violations(self) -> int:
        """Total constraint violations across the episode."""
        return self.metrics.constraint_violations


@dataclass
class PairResult:
    """The paired outcome of one seed across both arms.

    Attributes:
        seed: The shared seed for the arm pair.
        governed: The governed arm's result.
        ungoverned: The ungoverned arm's result.
    """

    seed: int
    governed: ArmResult
    ungoverned: ArmResult

    def violation_reduction(self) -> int:
        """Ungoverned violations minus governed violations.

        Positive values mean governance prevented violations.
        """
        return self.ungoverned.violations - self.governed.violations

    def reward_preservation_ratio(self) -> float | None:
        """Governed reward divided by ungoverned reward.

        Values close to 1 mean governance bounded damage without
        destroying utility. ``None`` when the ungoverned arm earned
        zero reward (division guard).
        """
        if self.ungoverned.total_reward == 0.0:
            return None
        return self.governed.total_reward / self.ungoverned.total_reward


# ----------------------------------------------------------------------
# Harness
# ----------------------------------------------------------------------


class _AgentProxyMember(ParliamentMember):
    """Placeholder Parliament seat for the agent itself.

    The Speaker's ``_apply_budgets`` drops proposals from members that
    are not registered in ``members``. The harness therefore registers
    the agent under :data:`AGENT_MEMBER_ID` with:

    - a ``budget`` of 1: exactly one agent proposal per governance cycle
    - zero ``weight``: the agent's self-score never skews the vote
    - a never-reachable ``veto_threshold``: the agent never vetoes its
      own action

    Its ``propose`` is never called by the harness (the agent's action
    is submitted directly as the proposal) and returns a no-op.
    """

    def __init__(self):
        super().__init__(
            member_id=AGENT_MEMBER_ID,
            veto_threshold=float("-inf"),
            weight=0.0,
            budget=1,
        )

    def evaluate_proposal(self, state: Any, proposal: Proposal) -> float:
        """Neutral self-score; irrelevant while ``weight`` is zero."""
        return 0.5

    def propose(self, state: Any) -> Proposal:
        """No-op: the agent's action is submitted by the harness."""
        return Proposal(member_id=AGENT_MEMBER_ID, action=None, tag=PriorityTag.ROUTINE)


class GovernorComparisonHarness(ABC):
    """Runs paired governed/ungoverned episodes of an agent backend.

    Args:
        scenario_factory: Callable that builds a fresh scenario given
            the harness's Speaker. Called once per arm so both arms
            start from identical initial state.
        backend: The agent backend under test. Reset before each arm
            so both arms consume identical action streams.
        action_space: Maps agent indices to scenario actions.
        speaker: The Speaker used by the governed arm. The harness
            operates on a shallow copy so the caller's parliament is
            never mutated.
        observation_fn: Renders the scenario's current state to the
            observation text shown to the agent. Defaults to a constant
            placeholder; LLM-native scenarios provide real renderers.
    """

    def __init__(
        self,
        scenario_factory: Callable[[SpeakerStateMachine], ExperimentScenario],
        backend: AgentBackend,
        action_space: ActionSpace,
        speaker: SpeakerStateMachine,
        observation_fn: Callable[[ExperimentScenario], Any] | None = None,
    ):
        self._scenario_factory = scenario_factory
        self._backend = backend
        self._action_space = action_space
        self._speaker = copy(speaker)
        self._speaker.members = dict(speaker.members)
        self._speaker.members[AGENT_MEMBER_ID] = _AgentProxyMember()
        self._observation_fn = observation_fn or (lambda scenario: "normal")

    def run_pair(
        self, seed: int = 0, steps: int = 100, decision_class: str = "routine"
    ) -> PairResult:
        """Run both arms with the given seed.

        Args:
            seed: Shared RNG seed for both arms. The scenario is
                re-created per arm from this seed, so both arms start
                from identical state.
            steps: Number of steps per arm.
            decision_class: Governance decision class (see
                :meth:`~..speaker.SpeakerStateMachine.run_governance_cycle`).

        Returns:
            A :class:`PairResult` with both arms' traces and metrics.
        """
        governed = self._run_arm("governed", seed, steps, decision_class)
        ungoverned = self._run_arm("ungoverned", seed, steps, decision_class)
        return PairResult(seed=seed, governed=governed, ungoverned=ungoverned)

    def _run_arm(self, arm: str, seed: int, steps: int, decision_class: str) -> ArmResult:
        scenario = self._scenario_factory(self._speaker)
        scenario.reset()
        self._backend.reset()
        log: list[StepLogEntry] = []

        for step in range(steps):
            observation = self._observation_fn(scenario)
            context = build_context(
                observation,
                self._action_space.descriptions(),
                seed=seed,
                step=step,
                arm=arm,
            )
            latency_start = time.perf_counter()
            agent_action = self._backend.select_action(context)
            select_latency = time.perf_counter() - latency_start
            entry = self._action_space.entry(agent_action.action_index)

            decision = self._decide(arm, scenario, observation, entry, decision_class)
            result = scenario.step(
                state=observation,
                decision_class=decision_class,
                external_decision=decision,
            )

            applied = result.decision
            vetoed = applied.is_default or applied.action != entry.action
            log.append(
                StepLogEntry(
                    step=step,
                    arm=arm,
                    observation=observation,
                    agent_action_index=agent_action.action_index,
                    confidence=agent_action.confidence,
                    rationale=agent_action.rationale,
                    proposed_action=entry.action,
                    decision_action=applied.action,
                    vetoed=vetoed,
                    is_default=applied.is_default,
                    would_have_been=entry.action if vetoed else None,
                    reward=result.reward,
                    violations_delta=result.metrics_delta.get("constraint_violations", 0),
                    select_latency=select_latency,
                )
            )

        return ArmResult(arm=arm, log=log, metrics=scenario.metrics)

    def _decide(
        self,
        arm: str,
        scenario: ExperimentScenario,
        state: Any,
        entry: ActionSpaceEntry,
        decision_class: str,
    ) -> GovernanceDecision:
        """Turn the agent's chosen action into a decision for the arm.

        The ungoverned arm applies the agent's action directly. The
        governed arm submits it as a proposal to the Speaker, which may
        veto it and fall back to the default action.

        Args:
            arm: ``"governed"`` or ``"ungoverned"``.
            scenario: The live scenario, used to resolve state-
                dependent proposal metadata.
            state: The current environment state (also shown to the
                governance cycle so members see what the agent saw).
            entry: The action entry the agent chose.
            decision_class: Governance decision class.

        Returns:
            The decision to apply to the environment.
        """
        if arm == "ungoverned":
            return GovernanceDecision(
                action=entry.action,
                governance_meta={"arm": "ungoverned", "agent_action_index": -1},
            )

        metadata = cast(
            dict[str, Any],
            entry.metadata if isinstance(entry.metadata, dict) else entry.metadata(scenario),
        )
        proposal = Proposal(
            member_id=AGENT_MEMBER_ID,
            action=entry.action,
            tag=PriorityTag.ROUTINE,
            metadata=metadata,
        )
        return self._speaker.run_governance_cycle(
            state=state,
            raw_proposals=[proposal],
            decision_class=decision_class,
        )
