"""
Ontology extension protocol with sandboxed isolation buffer (Chapter 4 §5.1).

New actions enter an isolation buffer state where independent monitors
empirically measure their properties before external audit and finalisation.
If the empirical measurements deviate too far from the candidate's claimed
properties, the extension is rejected.

This prevents "bait-and-switch" ontology poisoning: an attacker proposes an
action with benign claimed properties, but the monitor round reveals the
true behaviour before the action is registered.

Real-world analogy:
    A new drug candidate enters a clinical trial (isolation buffer).
    Independent researchers (monitors) measure its actual effects.
    If the real effects differ significantly from the claimed ones,
    the drug is rejected by the regulator.
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

from .keys import GenesisMultisig
from .ontology import Ontology, ActionBinding


class ExtensionPhase(Enum):
    """Lifecycle phase of an extension candidate.

    The progression is:
        PROPOSAL → ISOLATION_BUFFER → EMPIRICAL_AUDIT → FINALIZED
                                                     ↘ REJECTED
    """

    PROPOSAL = auto()
    ISOLATION_BUFFER = auto()
    EMPIRICAL_AUDIT = auto()
    FINALIZED = auto()
    REJECTED = auto()


@dataclass
class ExtensionCandidate:
    """A proposed ontology extension going through the sandbox protocol.

    Attributes:
        index: The action index being proposed.
        operation: Human-readable description of the action.
        candidate_properties: Claimed properties by the proposer.
        empirical_properties: Independently measured properties after
            sandbox rounds (set by :meth:`ExtensionSandbox.run_sandbox`).
        phase: Current lifecycle phase.
        monitor_reports: Per-round observations from independent monitors.
        multisig_approved: Whether genesis multisig has approved this candidate.
        runtime_hash: The final runtime integrity hash after finalisation.
    """

    index: int
    operation: str
    candidate_properties: Dict[str, float]
    empirical_properties: Optional[Dict[str, float]] = None
    phase: ExtensionPhase = ExtensionPhase.PROPOSAL
    monitor_reports: List[Dict[str, Any]] = field(default_factory=list)
    multisig_approved: bool = False
    runtime_hash: Optional[str] = None

    @property
    def is_sandboxed(self) -> bool:
        """True if the candidate is currently in the isolation buffer."""
        return self.phase == ExtensionPhase.ISOLATION_BUFFER


class ExtensionSandbox:
    """Sandboxed isolation buffer for ontology extensions (Ch 4 §5.1 fix).

    New action proposals pass through:

    1. **Proposal** — The proposer submits claimed properties.
    2. **Isolation buffer** — Independent monitors run ``rounds``
       measurements, adding controlled noise to simulate real-world variance.
    3. **Audit** — If empirical properties deviate from claimed beyond
       ``tolerance``, the extension is rejected.
    4. **Finalisation** — Requires multisig authorisation **and** passing audit.
       The action is then registered in the ontology.

    Args:
        ontology: The parent ontology to extend.
        multisig: Genesis multisig required for finalisation.
    """

    def __init__(self, ontology: Ontology, multisig: GenesisMultisig):
        self.ontology = ontology
        self.multisig = multisig
        self._candidates: Dict[int, ExtensionCandidate] = {}

    def propose(self, index: int, operation: str,
                candidate_properties: Dict[str, float]) -> ExtensionCandidate:
        """Propose a new action for the ontology.

        Args:
            index: Must not already be bound in the ontology.
            operation: Human-readable name for the action.
            candidate_properties: Claimed properties (what the proposer
                *says* the action does).

        Returns:
            The new :class:`ExtensionCandidate`.

        Raises:
            ValueError: If the index is already in the ontology.
        """
        if self.ontology.has_index(index):
            raise ValueError(f"Index {index} already bound")
        candidate = ExtensionCandidate(
            index=index,
            operation=operation,
            candidate_properties=candidate_properties,
        )
        self._candidates[index] = candidate
        return candidate

    def run_sandbox(self, index: int, rounds: int = 5):
        """Run independent monitor rounds in the isolation buffer.

        Each round adds small noise (:math:`\\pm 0.05`) to each property
        and appends a monitor report. This simulates the independent
        verification process described in Chapter 4 §5.1.

        Args:
            index: The candidate to sandbox.
            rounds: Number of measurement rounds (default 5).
        """
        candidate = self._candidates.get(index)
        if candidate is None or candidate.phase != ExtensionPhase.PROPOSAL:
            return
        candidate.phase = ExtensionPhase.ISOLATION_BUFFER

        empirical = dict(candidate.candidate_properties)
        for r in range(rounds):
            for key in empirical:
                noise = (secrets.randbelow(11) - 5) / 100.0
                empirical[key] = round(max(0.0, min(1.0, empirical[key] + noise)), 3)
            candidate.monitor_reports.append({
                "round": r + 1,
                "observed": dict(empirical),
            })
        candidate.empirical_properties = empirical

    def audit(self, index: int, tolerance: float = 0.1) -> bool:
        """Compare empirical properties against the candidate's claimed values.

        If any property deviates by more than ``tolerance``, the candidate
        is marked REJECTED.

        Args:
            index: The candidate to audit.
            tolerance: Maximum allowed absolute deviation (default 0.1).

        Returns:
            True if the candidate passes audit, False otherwise.
        """
        candidate = self._candidates.get(index)
        if candidate is None or candidate.empirical_properties is None:
            return False
        for key in candidate.candidate_properties:
            diff = abs(candidate.candidate_properties[key] - candidate.empirical_properties[key])
            if diff > tolerance:
                candidate.phase = ExtensionPhase.REJECTED
                return False
        return True

    def finalize(self, index: int,
                 implementation_bytes: bytes) -> Optional[ActionBinding]:
        """Finalise a candidate, registering it in the ontology.

        Requires both multisig authorisation **and** a passing audit.
        If either fails, the candidate is rejected.

        Args:
            index: The candidate to finalise.
            implementation_bytes: The action's implementation bytes for
                integrity hashing.

        Returns:
            The :class:`~.ontology.ActionBinding` if successful, or None
            if the candidate was rejected or not found.
        """
        candidate = self._candidates.get(index)
        if candidate is None:
            return None
        if not self.multisig.is_authorized:
            candidate.phase = ExtensionPhase.REJECTED
            return None
        if not self.audit(index):
            return None
        binding = self.ontology.register(
            index=index,
            operation=candidate.operation,
            implementation_bytes=implementation_bytes,
            properties=candidate.empirical_properties or candidate.candidate_properties,
        )
        candidate.phase = ExtensionPhase.FINALIZED
        candidate.runtime_hash = binding.runtime_hash
        return binding

    def get_candidate(self, index: int) -> Optional[ExtensionCandidate]:
        """Look up a candidate by its action index."""
        return self._candidates.get(index)
