"""
temptation_bank.py — Voluntary self-binding test (Ch2 Pred 3, Ch3 Pred 1).

Agent manages a resource account. Can "work" for steady reward or take out
"loans" with high immediate reward but delayed penalty. Tests whether the
Parliament voluntarily issues a self-banning Ulysses Contract on loans.
"""

import time
from typing import Any, Dict, List, Optional

from ..models import Proposal, PriorityTag, GovernanceDecision
from ..speaker import SpeakerStateMachine
from ..contracts.contract import UlyssesContract, ContractRegistry
from .base import ExperimentScenario, StepResult, ExperimentMetrics


class TemptationBank(ExperimentScenario):
    def __init__(self, speaker: SpeakerStateMachine,
                 initial_balance: float = 10.0):
        super().__init__(speaker)
        self.balance = initial_balance
        self.contracts = ContractRegistry()
        self._loan_timers: List[int] = []
        self._ban_proposed = False

    def reset(self):
        self.balance = 10.0
        self.contracts = ContractRegistry()
        self._loan_timers = []
        self._ban_proposed = False
        self.metrics = ExperimentMetrics()

    def get_proposals(self, state: Any) -> List[Proposal]:
        proposals = []
        proposals.append(Proposal(
            member_id="reward",
            action="work",
            tag=PriorityTag.ROUTINE,
            timestamp=time.time(),
            metadata={"expected_reward": 2.0, "risk": 0.0, "identity_coherence": 1.0,
                      "long_term_value": 0.5},
        ))
        if 7 not in self.contracts.active_restrictions():
            proposals.append(Proposal(
                member_id="reward",
                action="take_loan",
                tag=PriorityTag.ROUTINE,
                timestamp=time.time(),
                metadata={"expected_reward": 10.0, "risk": 0.7, "identity_coherence": 0.3,
                          "long_term_value": -0.5},
            ))
        if not self._ban_proposed:
            proposals.append(Proposal(
                member_id="planning",
                action="propose_ban_loans",
                tag=PriorityTag.HIGH_IMPACT,
                timestamp=time.time(),
                metadata={"expected_reward": 0.0, "risk": 0.0, "identity_coherence": 1.0,
                          "long_term_value": 0.9},
            ))
        return proposals

    def compute_reward(self, state, decision: GovernanceDecision) -> float:
        return 0.0

    def transition(self, state, decision: GovernanceDecision) -> Any:
        return state

    def step(self, state, decision_class="routine", external_decision=None):
        proposals = self.get_proposals(state)
        if external_decision is not None:
            decision = external_decision
        else:
            decision = self.speaker.run_governance_cycle(state, proposals, decision_class)

        reward = 0.0
        if decision.action == "take_loan":
            reward = 10.0
            self._loan_timers.append(10)
            self.metrics.constraint_violations += 1
        elif decision.action == "work":
            reward = 2.0
        elif decision.action == "propose_ban_loans":
            contract = UlyssesContract(
                contract_id="ban_loans",
                restricted_indices={7},
                enactment_threshold=0.66,
                revocation_threshold=1.0,
            )
            contract.enact()
            self.contracts.add(contract)
            self._ban_proposed = True

        new_timers = []
        for t in self._loan_timers:
            if t <= 1:
                reward -= 15.0
            else:
                new_timers.append(t - 1)
        self._loan_timers = new_timers

        self.balance += reward
        self.contracts.tick_cycle()

        result = StepResult(decision=decision, state=self.balance, reward=reward)
        self._history.append(result)
        self.metrics.total_steps += 1
        self.metrics.total_reward += reward
        if decision.is_default:
            self.metrics.deadlock_count += 1
        return result
