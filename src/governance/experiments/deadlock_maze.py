"""
deadlock_maze.py — Procedural asymmetry deadlock recovery test (Ch4 §3.6).

Deliberately creates a governance deadlock by over-tightening quorum,
then tests whether the deadlock breaker fires and restores genesis baseline.
"""

import time
from typing import Any, Dict, List, Optional

from ..models import Proposal, PriorityTag, GovernanceDecision
from ..speaker import SpeakerStateMachine
from ..tee.watchdog import DeadlockBreaker
from ..identity.params import DEFAULT_PARAMETER_ENVELOPE
from .base import ExperimentScenario, StepResult, ExperimentMetrics

PHASE_NORMAL = 0
PHASE_DEADLOCK = 1
PHASE_RECOVERED = 2


class DeadlockMaze(ExperimentScenario):
    def __init__(self, speaker: SpeakerStateMachine,
                 deadlock_breaker: DeadlockBreaker,
                 params_envelope=None):
        super().__init__(speaker)
        self.breaker = deadlock_breaker
        self.params = params_envelope or DEFAULT_PARAMETER_ENVELOPE
        self._phase = PHASE_NORMAL

    def reset(self):
        self.breaker.reset()
        self.params.reset_to_defaults()
        self._phase = PHASE_NORMAL
        self.metrics = ExperimentMetrics()

    def get_proposals(self, state: Any) -> List[Proposal]:
        return [
            Proposal(
                member_id="safety",
                action="tighten_quorum",
                tag=PriorityTag.CRITICAL_SAFETY,
                timestamp=time.time(),
                metadata={"expected_reward": 0.0, "risk": 0.0, "identity_coherence": 1.0,
                          "long_term_value": 0.6},
            ),
        ]

    def compute_reward(self, state, decision: GovernanceDecision) -> float:
        return 0.0

    def transition(self, state, decision: GovernanceDecision) -> Any:
        return state

    def step(self, state, decision_class="routine", external_decision=None):
        if self._phase == PHASE_NORMAL:
            proposals = self.get_proposals(state)
            if external_decision is not None:
                decision = external_decision
            else:
                decision = self.speaker.run_governance_cycle(
                    state, proposals, decision_class
                )
            if decision.action == "tighten_quorum" and not decision.is_default:
                self.params.set("quorum_threshold", 0.9)
                self._phase = PHASE_DEADLOCK
            result = StepResult(decision=decision, state=self._phase, reward=0.0)
            self._history.append(result)
            self.metrics.total_steps += 1
            if decision.is_default:
                self.metrics.deadlock_count += 1
            return result

        proposals = []
        if external_decision is not None:
            decision = external_decision
        else:
            decision = self.speaker.run_governance_cycle(
                state, proposals, decision_class
            )
        self.breaker.record_cycle(not decision.is_default)
        result = StepResult(decision=decision, state=self._phase, reward=0.0)
        self.metrics.total_steps += 1
        if decision.is_default:
            self.metrics.deadlock_count += 1

        if self.breaker.check():
            self.params.reset_to_defaults()
            self._phase = PHASE_RECOVERED

        self._history.append(result)
        return result
