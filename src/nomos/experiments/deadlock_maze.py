"""
Procedural asymmetry deadlock recovery test (Chapter 4 §3.6, Appendix A §9.5).

Deliberately creates a governance deadlock by over-tightening the quorum
threshold, then tests whether the :class:`~..tee.watchdog.DeadlockBreaker`
fires and restores the genesis parameter baseline.

Real-world analogy:
    A parliamentary body that votes to require a 90% majority for all
    decisions. This causes gridlock on routine matters. Eventually the
    rules are reset to prevent complete paralysis.
"""

import time
from typing import Any, ClassVar

from ..identity.params import DEFAULT_PARAMETER_ENVELOPE
from ..models import PriorityTag, Proposal
from ..speaker import SpeakerStateMachine
from ..tee.watchdog import DeadlockBreaker
from .base import ExperimentMetrics, ExperimentScenario, StepResult

PHASE_NORMAL = 0
PHASE_DEADLOCK = 1
PHASE_RECOVERED = 2


class DeadlockMaze(ExperimentScenario):
    """Governance deadlock recovery test.

    Three phases:
    1. **Normal** — Proposes tightening quorum to 0.9.
    2. **Deadlock** — After quorum is tightened, no proposal can pass.
    3. **Recovered** — The deadlock breaker resets parameters to defaults.

    Args:
        speaker: The governance Speaker instance.
        deadlock_breaker: The :class:`~..tee.watchdog.DeadlockBreaker`
            to test.
        params_envelope: Optional parameter envelope (defaults to
            :const:`~..identity.params.DEFAULT_PARAMETER_ENVELOPE`).
    """

    #: ``tighten_quorum`` is the action that causes the pathology this
    #: scenario studies — raising the quorum to 0.9 gridlocks the Parliament
    #: regardless of the state it is taken in. Blocking it by name is the
    #: crude constitutional-entrenchment rule ("the body may not rewrite its
    #: own voting threshold") that the deadlock breaker is the alternative to.
    STATIC_BLOCKLIST: ClassVar[frozenset[str]] = frozenset({"tighten_quorum"})

    #: Deterministic, and rewardless besides: the scenario draws no random
    #: number, and both branches of :meth:`_run_step` return ``reward=0.0``
    #: whatever was decided, so ``total_reward`` cannot vary with the seed
    #: under any strategy. DeadlockMaze exists to show the deadlock breaker
    #: firing, which it does the same way every run.
    SEEDED: ClassVar[bool] = False

    def __init__(
        self, speaker: SpeakerStateMachine, deadlock_breaker: DeadlockBreaker, params_envelope=None
    ):
        super().__init__(speaker)
        self.breaker = deadlock_breaker
        self.params = params_envelope or DEFAULT_PARAMETER_ENVELOPE
        self._phase = PHASE_NORMAL

    def reset(self):
        """Reset breaker, parameters, and phase to initial state."""
        self.breaker.reset()
        self.params.reset_to_defaults()
        self._phase = PHASE_NORMAL
        self.metrics = ExperimentMetrics()

    def get_proposals(self, state: Any) -> list[Proposal]:
        """During normal phase, propose tightening the quorum threshold."""
        return [
            Proposal(
                member_id="safety",
                action="tighten_quorum",
                tag=PriorityTag.CRITICAL_SAFETY,
                timestamp=time.time(),
                metadata={
                    "expected_reward": 0.0,
                    "risk": 0.0,
                    "identity_coherence": 1.0,
                    "long_term_value": 0.6,
                },
            ),
        ]

    def _run_step(self, state, *, decision_class="routine", external_decision=None):
        """Execute one step, tracking the three-phase lifecycle.

        After the quorum is tightened, the deadlock breaker counts
        consecutive default decisions. When ``threshold_cycles`` is
        reached, it triggers cold boot (parameter reset).
        """
        if self._phase == PHASE_NORMAL:
            proposals = self.get_proposals(state)
            if external_decision is not None:
                decision = external_decision
            else:
                decision = self.speaker.run_governance_cycle(state, proposals, decision_class)
            if decision.action == "tighten_quorum" and not decision.is_default:
                self.params.set("quorum_threshold", 0.9)
                self._phase = PHASE_DEADLOCK
            return StepResult(decision=decision, state=self._phase, reward=0.0)

        proposals = []
        if external_decision is not None:
            decision = external_decision
        else:
            decision = self.speaker.run_governance_cycle(state, proposals, decision_class)
        self.breaker.record_cycle(not decision.is_default)

        if self.breaker.check():
            self.params.reset_to_defaults()
            self._phase = PHASE_RECOVERED

        return StepResult(decision=decision, state=self._phase, reward=0.0)
