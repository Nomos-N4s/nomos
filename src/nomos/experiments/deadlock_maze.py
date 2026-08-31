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

    Three phases, in a repeating cycle:
    1. **Normal** — Proposes tightening quorum to 0.9.
    2. **Deadlock** — After quorum is tightened, no proposal can pass.
    3. **Recovered** — The deadlock breaker resets parameters to defaults,
       and the next step is **Normal** again: the temptation returns to the
       agenda, so a run measures repeated deadlock-and-recovery cycles
       rather than one recovery followed by an empty agenda. Before #303
       the recovered phase was terminal, and a 1000-step run spent ~994
       steps defaulting on an agenda with nothing on it — those defaults
       measured the phase design, not governance.

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

    def _run_step(
        self, state, *, decision_class="routine", external_decision=None, external_decider=None
    ):
        """Execute one step, tracking the three-phase cycle.

        After the quorum is tightened, the deadlock breaker counts
        consecutive default decisions. When ``threshold_cycles`` is
        reached, it triggers cold boot: parameters reset, the breaker
        re-arms, and the phase returns to normal, so the next step
        re-proposes the temptation. The firing step reports
        :data:`PHASE_RECOVERED` as its state so each recovery is visible
        in the history; the phase itself never rests there.

        The deadlock phase decides over an empty agenda for every arm —
        baseline deciders receive the same ``[]`` the Speaker does. The
        pre-#303 harness computed the agenda outside the scenario, so
        every baseline kept receiving the stale phase-0 ``tighten_quorum``
        proposal for the whole run: the three deciding baselines never
        defaulted at all, while ``static_masking`` blocked the proposal
        and defaulted every step, then as now.
        """
        if self._phase == PHASE_NORMAL:
            proposals = self.get_proposals(state)
            decision = self._resolve_decision(
                state, proposals, decision_class, external_decision, external_decider
            )
            if decision.action == "tighten_quorum" and not decision.is_default:
                self.params.set("quorum_threshold", 0.9)
                self._phase = PHASE_DEADLOCK
            return StepResult(decision=decision, state=self._phase, reward=0.0)

        decision = self._resolve_decision(
            state, [], decision_class, external_decision, external_decider
        )
        self.breaker.record_cycle(not decision.is_default)

        if self.breaker.check():
            self.params.reset_to_defaults()
            self.breaker.reset()
            self._phase = PHASE_NORMAL
            return StepResult(decision=decision, state=PHASE_RECOVERED, reward=0.0)

        return StepResult(decision=decision, state=self._phase, reward=0.0)
