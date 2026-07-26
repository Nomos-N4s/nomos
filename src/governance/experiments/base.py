"""
base.py — Abstract scenario base class for all governance experiments.

Each scenario implements setup, step, and metrics collection.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..models import GovernanceDecision, Proposal
from ..speaker import SpeakerStateMachine


@dataclass
class StepResult:
    decision: GovernanceDecision
    state: Any
    reward: float = 0.0


@dataclass
class ExperimentMetrics:
    total_steps: int = 0
    total_reward: float = 0.0
    constraint_violations: int = 0
    deadlock_count: int = 0
    contract_revocations: int = 0
    veto_count: int = 0
    falsification_count: int = 0
    identity_drift: List[float] = field(default_factory=list)
    governance_latencies: List[float] = field(default_factory=list)


class ExperimentScenario(ABC):
    def __init__(self, speaker: SpeakerStateMachine):
        self.speaker = speaker
        self.metrics = ExperimentMetrics()
        self._history: List[StepResult] = []

    @abstractmethod
    def reset(self):
        ...

    @abstractmethod
    def get_proposals(self, state: Any) -> List[Proposal]:
        ...

    @abstractmethod
    def compute_reward(self, state: Any, decision: GovernanceDecision) -> float:
        ...

    @abstractmethod
    def transition(self, state: Any, decision: GovernanceDecision) -> Any:
        ...

    def step(self, state: Any, decision_class: str = "routine",
             external_decision: Optional[GovernanceDecision] = None) -> StepResult:
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
    def history(self) -> List[StepResult]:
        return list(self._history)
