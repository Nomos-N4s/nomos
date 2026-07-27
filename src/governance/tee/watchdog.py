"""
Heartbeat watchdog and deadlock breaker for the governance enclave (Appendix A §9).

Two complementary mechanisms guard against compute failure:

1. **Heartbeat watchdog** — The enclave must send periodic heartbeats.
   If a heartbeat is missed, the watchdog escalates the state to
   ``HEARTBEAT_MISSED``. If the heartbeat resumes, it returns to ``NORMAL``.

2. **Deadlock breaker** — If the governance process produces no decisions
   for ``threshold_cycles`` consecutive cycles, the deadlock breaker triggers
   a cold-boot recovery of the entire enclave.

Real-world analogy:
    A safety switch on a treadmill. If the user stops walking (missed
    heartbeat), the belt slows. If the belt stays stopped for too long
    (deadlock), the machine powers off entirely and needs a manual reset.
"""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, List, Optional


class WatchdogState(Enum):
    """Current state of the hardware watchdog timer.

    States flow: ``NORMAL ↔ HEARTBEAT_MISSED``, or
    ``NORMAL → HEARTBEAT_MISSED → DEADLOCKED → COLD_BOOT``
    """

    NORMAL = auto()
    HEARTBEAT_MISSED = auto()
    DEADLOCKED = auto()
    COLD_BOOT = auto()


@dataclass
class WatchdogEvent:
    """A recorded event in the watchdog's event log.

    Attributes:
        event_type: Category (e.g. ``heartbeat_missed``,
            ``heartbeat_restored``, ``cold_boot``).
        timestamp: Unix timestamp of the event.
        details: Human-readable description.
    """

    event_type: str
    timestamp: float
    details: str = ""


class WatchdogTimer:
    """Heartbeat-based watchdog timer.

    The enclave must call :meth:`heartbeat` within the timeout window.
    If it fails to do so, the watchdog detects compute starvation and
    can trigger escalation.

    Args:
        heartbeat_timeout_ms: Maximum allowed interval between heartbeats
            in milliseconds (default 100.0 ms).
    """

    def __init__(self, heartbeat_timeout_ms: float = 100.0):
        self.heartbeat_timeout = heartbeat_timeout_ms / 1000.0
        self._last_heartbeat: float = time.time()
        self._state = WatchdogState.NORMAL
        self._events: List[WatchdogEvent] = []

    def heartbeat(self):
        """Send a heartbeat signal. Reset the timer and restore normal state."""
        self._last_heartbeat = time.time()
        if self._state == WatchdogState.HEARTBEAT_MISSED:
            self._state = WatchdogState.NORMAL
            self._log("heartbeat_restored", "Heartbeat restored")

    def check(self) -> WatchdogState:
        """Check whether the watchdog has timed out.

        If the elapsed time since the last heartbeat exceeds the timeout,
        the state transitions to ``HEARTBEAT_MISSED``.

        Returns:
            The current :class:`WatchdogState`.
        """
        if self._state == WatchdogState.COLD_BOOT:
            return self._state
        elapsed = time.time() - self._last_heartbeat
        if elapsed > self.heartbeat_timeout:
            if self._state != WatchdogState.HEARTBEAT_MISSED:
                self._state = WatchdogState.HEARTBEAT_MISSED
                self._log("heartbeat_missed",
                          f"Last heartbeat {elapsed:.2f}s ago")
        return self._state

    @property
    def state(self) -> WatchdogState:
        """The current watchdog state."""
        return self._state

    def _log(self, event_type: str, details: str = ""):
        self._events.append(WatchdogEvent(
            event_type=event_type,
            timestamp=time.time(),
            details=details,
        ))

    def get_events(self) -> List[WatchdogEvent]:
        """Return the full event log (immutable copy)."""
        return list(self._events)


class DeadlockBreaker:
    """Monitors governance cycles and triggers cold boot on persistent deadlock.

    A deadlock is defined as ``threshold_cycles`` consecutive cycles without
    a decision. This matches the formal definition in Chapter 3 §3.3 where
    the contract system cannot reach consensus due to incompatible masks.

    Args:
        threshold_cycles: Number of stalled cycles before cold boot
            (default 100).
    """

    def __init__(self, threshold_cycles: int = 100):
        self.threshold = threshold_cycles
        self._cycles_without_decision: int = 0
        self._cold_boot_triggered: bool = False
        self._total_cold_boots: int = 0

    def record_cycle(self, decision_produced: bool):
        """Record whether the latest governance cycle produced a decision.

        Args:
            decision_produced: True if at least one proposal was decided.
        """
        if self._cold_boot_triggered:
            return
        if decision_produced:
            self._cycles_without_decision = 0
        else:
            self._cycles_without_decision += 1

    def check(self) -> bool:
        """Check whether the deadlock threshold has been reached.

        If so, trigger a cold boot (once). Cold boot is idempotent —
        subsequent calls return False until :meth:`reset`.

        Returns:
            True if this is the moment a cold boot should be triggered.
        """
        if self._cold_boot_triggered:
            return False
        if self._cycles_without_decision >= self.threshold:
            self._cold_boot_triggered = True
            self._total_cold_boots += 1
            return True
        return False

    def reset(self):
        """Reset the deadlock breaker after a cold boot recovery."""
        self._cycles_without_decision = 0
        self._cold_boot_triggered = False

    @property
    def is_deadlocked(self) -> bool:
        """True if currently in a deadlock state (stalled ≥ threshold)."""
        return self._cycles_without_decision >= self.threshold

    @property
    def stalled_cycles(self) -> int:
        """Number of consecutive cycles without a decision."""
        return self._cycles_without_decision

    @property
    def total_cold_boots(self) -> int:
        """Total number of cold boots triggered over the enclave's lifetime."""
        return self._total_cold_boots
