"""
Key hierarchy and simulated 3-of-5 multisig for genesis bootstrapping (Chapter 4 §3).

The genesis bootstrapping protocol establishes the root of trust:

1. Five external key holders (genesis keys) are registered
2. At least 3-of-5 must sign to authorise the initial identity configuration
3. The signed configuration is sealed in a :class:`GenesisManifest`
4. After boot, the genesis keys are not needed for routine operation

Real-world analogy:
    A safe deposit box with five keyholders. Three must insert their
    keys simultaneously to open it. After the box is opened and its
    contents verified, the individual keys are no longer needed —
    the contents themselves become the source of authority.
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class KeyHolder:
    """A single genesis key holder with a public key and signing status.

    Attributes:
        name: Human-readable identifier (e.g. ``"alice"``).
        public_key: Hex string representing the holder's public key.
        has_signed: Whether this holder has signed the current operation.
    """

    name: str
    public_key: str
    has_signed: bool = False


class GenesisMultisig:
    """Simulated t-of-n multisig for genesis bootstrapping (default 3-of-5).

    Independent of the Parliament. Even if every Parliament member is
    compromised, the genesis multisig provides an external check.

    Args:
        threshold: Number of signatures required (default 3).
        total_holders: Total key holders (default 5).
    """

    def __init__(self, threshold: int = 3, total_holders: int = 5):
        self.threshold = threshold
        self.holders: List[KeyHolder] = []

    def add_holder(self, name: str) -> str:
        """Register a new key holder and generate their public key.

        Args:
            name: A unique name for this holder.

        Returns:
            The generated public key (hex string, first 16 chars of SHA-256).
        """
        pk = hashlib.sha256(secrets.token_bytes(32)).hexdigest()[:16]
        self.holders.append(KeyHolder(name=name, public_key=pk))
        return pk

    def sign(self, holder_name: str) -> bool:
        """Record a signature from a registered holder.

        A holder can only sign once per session (idempotent).

        Args:
            holder_name: Must match a registered holder's ``name``.

        Returns:
            True if the signature was recorded. False if the holder
            was not found or already signed.
        """
        for h in self.holders:
            if h.name == holder_name and not h.has_signed:
                h.has_signed = True
                return True
        return False

    @property
    def signatures_count(self) -> int:
        """Number of holders who have signed so far."""
        return sum(1 for h in self.holders if h.has_signed)

    @property
    def is_authorized(self) -> bool:
        """True if the signature threshold has been met (≥ t of n)."""
        return self.signatures_count >= self.threshold

    def reset(self):
        """Clear all signatures (for testing or rejection scenarios)."""
        for h in self.holders:
            h.has_signed = False


@dataclass
class GenesisManifest:
    """The sealed record of the identity genesis configuration.

    Once sealed, this manifest becomes the root of trust for the TEE
    attestation and Identity Layer. It contains cryptographic hashes
    of every boot-time parameter.

    Attributes:
        ontology_hash: SHA-256 hash of the initial action ontology.
        core_commitments_hash: Hash of the initial core commitments.
        parameter_envelope_hash: Hash of the parameter envelope.
        member_set_hash: Hash of the Parliament member set configuration.
        multisig: The genesis multisig instance that authorised this manifest.
        is_sealed: Whether the manifest has been finalised (immutable after seal).
    """

    ontology_hash: str = ""
    core_commitments_hash: str = ""
    parameter_envelope_hash: str = ""
    member_set_hash: str = ""
    multisig: GenesisMultisig = field(default_factory=GenesisMultisig)
    is_sealed: bool = False

    def seal(self):
        """Finalise the manifest. After sealing, it should not be modified."""
        self.is_sealed = True

    def __repr__(self):
        return f"<GenesisManifest sealed={self.is_sealed} sigs={self.multisig.signatures_count}/{self.multisig.threshold}>"
