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

    Raises:
        ValueError: If the threshold or holder count is not a valid t-of-n
            (``1 <= threshold <= total_holders``).
    """

    def __init__(self, threshold: int = 3, total_holders: int = 5):
        if total_holders < 1:
            raise ValueError(f"total_holders must be at least 1, got {total_holders}")
        if threshold < 1:
            raise ValueError(f"threshold must be at least 1, got {threshold}")
        if threshold > total_holders:
            raise ValueError(
                f"threshold {threshold} exceeds total_holders {total_holders} — "
                "a quorum that can never be reached is not a valid t-of-n"
            )
        self.threshold = threshold
        self.total_holders = total_holders
        self.holders: list[KeyHolder] = []

    def add_holder(self, name: str) -> str:
        """Register a new key holder and generate their public key.

        The name is the holder's identity: ``sign`` matches on it and nothing
        else. Duplicate names are therefore refused, otherwise one principal
        could register several times and sign a quorum alone. The registry is
        also capped at ``total_holders`` so the *n* in *t-of-n* is enforced.

        Args:
            name: A unique name for this holder.

        Returns:
            The generated public key (hex string, first 16 chars of SHA-256).

        Raises:
            ValueError: If ``name`` is already registered, or the registry is
                already at ``total_holders``.
        """
        if any(h.name == name for h in self.holders):
            raise ValueError(f"holder {name!r} is already registered")
        if len(self.holders) >= self.total_holders:
            raise ValueError(
                f"cannot register {name!r}: already at total_holders={self.total_holders}"
            )
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
        """Number of *distinct* holders who have signed so far.

        Counting distinct names rather than signed records mirrors the Lean
        model's ``quorumCount`` (``IdentityGenesis.lean``), which filters a
        fixed key set. The invariant then holds even if a duplicate record is
        introduced by some other path.
        """
        return len({h.name for h in self.holders if h.has_signed})

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
