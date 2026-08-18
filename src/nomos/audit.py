"""
Tamper-evident, append-only audit log (hash-chained JSONL) — #164.

The operational face of the TEE Merkle batch verification (Appendix A §8):
every governance event lands in an append-only JSONL store whose records are
linked by content hashes, so any mutation of history is detected at the exact
broken record.

Design goals (matching ``#164``):

- **Append-only by structure, not policy:** the public API has *no* update,
  delete, or truncate operations. The only way to extend a log is
  :meth:`AuditLog.append`, which chains the new record to the previous
  record's hash. Tampering therefore requires rewriting the file out of
  band — and every such rewrite is caught by :meth:`AuditLog.verify`.
- **Hash-chained records:** each record carries ``prev_hash`` (the previous
  record's content hash) and its own ``hash`` — SHA-256 over the canonical
  JSON of every other field. The first record links to
  :data:`ZERO_HASH`. Mutation of any historical record breaks either its own
  hash or the next record's ``prev_hash`` link.
- **Merkle anchoring (CWE-345):** :meth:`AuditLog.batch_root` folds every
  record hash into a single Merkle root via the TEE module's ``merkle_root``
  (Appendix A §8). That root is additionally persisted in a **sidecar anchor
  file** (``<path>.root``) *outside* the JSONL store, updated atomically on
  every append. ``verify()`` compares the on-disk chain's root against the
  anchor — a writer who rewrites every record and rehashes the whole chain
  passes the self-consistency checks but cannot match the anchor unless they
  also control the sidecar. For real deployments the anchor must be
  replicated/attested off-host (Appendix A); the sidecar is the reference
  implementation of that seam. If the process crashes between the JSONL
  write and the anchor update, ``verify()`` reports a root mismatch —
  fail-loud by design, no silent self-healing.
- **Deterministic:** canonical JSON (sorted keys, fixed separators, no
  random salts) plus an injectable clock (:meth:`AuditLog.__init__`'s
  ``now_fn``) make identical runs byte-identical — auditable reproducibility.
- **Two export modes:** plain JSONL (the store itself) and SIEM-ready
  RFC 5424-ish envelopes (:meth:`AuditLog.export_siem`).

Entity types (per-entity stores are separate files using the same format):
``proposal``, ``decision``, ``contract``, ``veto``, ``identity``.

Permissions (Identity Layer authority — Chapter 4):

- **Append:** components that are identity-authorized to record authoritative
  events — the Speaker (proposals, decisions, vetoes), the contract
  enforcement layer (lifecycle transitions), and the Identity Layer itself
  (commitment changes). Appends go exclusively through
  :meth:`AuditLog.append`.
- **Verify / export:** read-only; available to operators, auditors, and the
  verification tool with file access. Verification never writes.

Line format (one JSON object per line, sorted keys for canonicity)::

    {"entity_id": "...", "entity_type": "decision", "event": "adopted",
     "hash": "<sha256>", "payload": {...}, "prev_hash": "<sha256>",
     "seq": 0, "timestamp": "2026-08-11T15:00:00.000Z"}

Usage::

    from nomos.audit import AuditLog

    log = AuditLog("audit/decisions.jsonl")
    log.append("decision", "adopted", "proposal:7", {"action": "shutdown", "risk": 0.2})
    log.append("veto", "applied", "proposal:7", {"reason": "safety"})

    result = log.verify()
    assert result.valid            # reports (broken_index, message) otherwise
    log.batch_root()               # single Merkle root for external anchoring
    log.export_siem("audit/decisions.syslog")
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nomos.tee.batch import merkle_root

__all__ = [
    "ANCHOR_ALGORITHM",
    "AuditLog",
    "AuditRecord",
    "AuditVerification",
    "ENTITY_TYPES",
    "ZERO_HASH",
]

ANCHOR_ALGORITHM = 2
"""Merkle algorithm generation stamped into the sidecar anchor payload.

Generation 1 hashed leaves and internal nodes in a single space. Generation 2
domain-separates them (see :mod:`nomos.tee.batch`), so the same chain folds to
a different root. An anchor carrying no ``alg`` field predates the stamp and is
read as generation 1.
"""

ZERO_HASH = "0" * 64
"""The ``prev_hash`` of the first record (no predecessor)."""

ENTITY_TYPES = ("proposal", "decision", "contract", "veto", "identity")
"""Canonical entity types of the audit log."""

_RECORD_KEYS = (
    "seq",
    "entity_type",
    "event",
    "entity_id",
    "timestamp",
    "payload",
    "prev_hash",
    "hash",
)
"""Every key a stored record must carry (any other layout is tampering)."""


def _iso_utc_now() -> str:
    """Current time as ISO-8601 UTC with millisecond precision (``Z`` suffix)."""
    now = _dt.datetime.now(_dt.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _canonical(value: Any) -> Any:
    """Coerce ``value`` to a deterministic, JSON-serializable form.

    Dictionaries are recursively canonicalised (keys sorted at every level),
    non-finite floats become strings, and everything else that is not a
    native JSON value is converted with ``str()``.
    """
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, (int, float)):
        return value if isinstance(value, int) else (value if _finite(value) else str(value))
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    if isinstance(value, (set, frozenset)):
        return [_canonical(v) for v in sorted(value, key=repr)]
    return str(value)


def _finite(value: float) -> bool:
    """True if ``value`` is a finite IEEE-754 float."""
    import math

    return math.isfinite(value)


def _canonical_json(fields: dict[str, Any]) -> str:
    """Serialize ``fields`` with sorted keys and minimal separators."""
    return json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class AuditRecord:
    """One hash-chained audit record.

    Attributes:
        seq: Zero-based position in the log.
        entity_type: One of :data:`ENTITY_TYPES`.
        event: Event name, e.g. ``"adopted"``, ``"vetoed"``, ``"enacted"``.
        entity_id: Stable identifier of the subject (proposal, contract, ...).
        timestamp: ISO-8601 UTC timestamp of the event.
        payload: Canonicalised event payload (JSON-safe, sorted keys).
        prev_hash: SHA-256 of the previous record (ZERO_HASH for the first).
        hash: SHA-256 of every other field of this record.
    """

    seq: int
    entity_type: str
    event: str
    entity_id: str
    timestamp: str
    payload: dict[str, Any]
    prev_hash: str
    hash: str

    def to_dict(self) -> dict[str, Any]:
        """The record as a dict with canonical key order."""
        return {
            "seq": self.seq,
            "entity_type": self.entity_type,
            "event": self.event,
            "entity_id": self.entity_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }


@dataclass(frozen=True)
class AuditVerification:
    """Result of :meth:`AuditLog.verify`.

    Attributes:
        valid: True when every record is intact and properly chained.
        broken_index: Index of the first broken record, or ``None``.
        message: Human-readable explanation of the failure (or a success note).
    """

    valid: bool
    broken_index: int | None
    message: str


def _record_hash(
    seq: int,
    entity_type: str,
    event: str,
    entity_id: str,
    timestamp: str,
    payload: dict[str, Any],
    prev_hash: str,
) -> str:
    """SHA-256 over the canonical JSON of every field except ``hash``."""
    fields = {
        "seq": seq,
        "entity_type": entity_type,
        "event": event,
        "entity_id": entity_id,
        "timestamp": timestamp,
        "payload": payload,
        "prev_hash": prev_hash,
    }
    return hashlib.sha256(_canonical_json(fields).encode("utf-8")).hexdigest()


def _parse_line(index: int, line: str) -> AuditRecord | None:
    """Parse one stored line into an :class:`AuditRecord`, or ``None`` if malformed."""
    try:
        raw = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict) or any(k not in raw for k in _RECORD_KEYS):
        return None
    try:
        seq = int(raw["seq"])
        payload = dict(raw["payload"]) if isinstance(raw["payload"], dict) else {}
    except (TypeError, ValueError):
        return None
    return AuditRecord(
        seq=seq,
        entity_type=str(raw["entity_type"]),
        event=str(raw["event"]),
        entity_id=str(raw["entity_id"]),
        timestamp=str(raw["timestamp"]),
        payload=payload,
        prev_hash=str(raw["prev_hash"]),
        hash=str(raw["hash"]),
    )


class AuditLog:
    """Append-only, hash-chained audit log backed by a JSONL file.

    Args:
        path: Where the JSONL store lives (created on first append).
        now_fn: Callable returning the ISO-8601 UTC timestamp for new
            records; inject a fixed clock for reproducible runs (defaults to
            the real current time).

    Reopening an existing store restores the full chain from disk — ``seq``,
    ``prev_hash``, ``records()``, ``batch_root()``, and ``export_siem()``
    always reflect the complete log, never just this instance's appends.
    A malformed existing file raises :class:`ValueError` at construction.
    """

    def __init__(self, path: str | Path, now_fn: Callable[[], str] | None = None) -> None:
        self.path = Path(path)
        self._now_fn = now_fn or _iso_utc_now
        self._entries: list[AuditRecord] = []
        # Create the store eagerly (no held handle): an empty file means "no
        # records yet" while a missing file means out-of-band deletion.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self._load()

    def _load(self) -> None:
        """Restore the in-memory chain from the existing store.

        Raises:
            ValueError: The store contains a line that is not a parseable
                audit record (missing fields, wrong types, or bad JSON).
        """
        for index, line in enumerate(self.path.read_text(encoding="utf-8").splitlines()):
            record = _parse_line(index, line)
            if record is None:
                raise ValueError(f"audit log {self.path} is malformed at record {index}")
            self._entries.append(record)

    def append(
        self,
        entity_type: str,
        event: str,
        entity_id: str,
        payload: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Append one record and return it.

        Args:
            entity_type: One of :data:`ENTITY_TYPES`.
            event: Event name (free-form but stable per event kind).
            entity_id: Stable identifier of the subject.
            payload: Arbitrary event payload; canonicalised (sorted keys,
                JSON-safe) before storage. Must be a dict.

        Raises:
            ValueError: Unknown ``entity_type``.
            TypeError: ``payload`` is not a dict (or not dict-like).
        """
        if entity_type not in ENTITY_TYPES:
            raise ValueError(f"unknown entity_type {entity_type!r}; choose from {ENTITY_TYPES}")
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise TypeError(f"payload must be a dict, got {type(payload).__name__}")
        canonical_payload: dict[str, Any] = _canonical(payload)
        seq = len(self._entries)
        prev_hash = self._entries[-1].hash if self._entries else ZERO_HASH
        timestamp = self._now_fn()
        record = AuditRecord(
            seq=seq,
            entity_type=entity_type,
            event=event,
            entity_id=entity_id,
            timestamp=timestamp,
            payload=canonical_payload,
            prev_hash=prev_hash,
            hash=_record_hash(
                seq, entity_type, event, entity_id, timestamp, canonical_payload, prev_hash
            ),
        )
        # Open per append (no held handle): the file stays deletable/archivable
        # out of band — which is exactly what `verify()` must be able to detect.
        with self.path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(_canonical_json(record.to_dict()) + "\n")
        self._entries.append(record)
        self._write_anchor()
        return record

    @property
    def _anchor_path(self) -> Path:
        """Sidecar holding the trusted Merkle root, outside the JSONL file."""
        return self.path.with_name(self.path.name + ".root")

    def _write_anchor(self) -> None:
        """Persist the trusted Merkle root of the whole chain to the sidecar.

        Atomic (temp file + rename), so a reader never sees a partial anchor.
        The payload records the Merkle algorithm generation
        (:data:`ANCHOR_ALGORITHM`) that produced the root, so a reader can tell
        an anchor written under an earlier generation from a forged one.
        """
        payload = _canonical_json(
            {
                "alg": ANCHOR_ALGORITHM,
                "root": merkle_root([r.hash.encode("utf-8") for r in self._entries]),
            }
        )
        tmp = self._anchor_path.with_name(self._anchor_path.name + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, self._anchor_path)

    def _read_anchor(self) -> str | None:
        """The trusted root from the sidecar, or ``None`` if missing/malformed."""
        try:
            raw = json.loads(self._anchor_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        root = raw.get("root") if isinstance(raw, dict) else None
        return root if isinstance(root, str) and len(root) == 64 else None

    def records(self) -> tuple[AuditRecord, ...]:
        """The full chain: records loaded from disk plus this instance's appends."""
        return tuple(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def verify(self) -> AuditVerification:
        """Re-read the file and verify the whole chain from disk.

        Detection rules, in order:

        1. A line that is not parseable JSON or misses a required key is
           reported as *malformed* at its index.
        2. A record whose ``seq`` does not match its position is reported as
           *positional tamper* at its index (records were removed or inserted
           wholesale).
        3. A record whose stored ``hash`` differs from the content hash is
           reported as *tampered* at its index.
        4. A record whose ``prev_hash`` does not match the previous record's
           hash is reported as a *chain break* at its index.
        5. A file that is shorter than the chain this instance knows is
           reported as *truncated* (trailing records removed) — a shortened
           log would otherwise verify as an intact prefix.
        6. The Merkle root of the on-disk chain must equal the trusted root
           in the sidecar anchor (``<path>.root``), which lives *outside* the
           JSONL file. A writer that rewrites every record and rehashes the
           whole chain passes rules 1–5, but fails here — CWE-345.

        Returns:
            :class:`AuditVerification` with the exact broken index.
        """
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return AuditVerification(False, 0, "audit log file missing (deleted out of band)")
        if not lines:
            if self._entries:
                return AuditVerification(False, 0, "audit log truncated (all records removed)")
            return AuditVerification(True, None, "audit log is empty (no records)")

        previous_hash = ZERO_HASH
        disk_hashes: list[str] = []
        for index, line in enumerate(lines):
            record = _parse_line(index, line)
            if record is None:
                return AuditVerification(
                    False, index, f"record {index} is malformed (unparseable or missing fields)"
                )
            if record.seq != index:
                return AuditVerification(
                    False, index, f"record {index} carries seq {record.seq} (positional tamper)"
                )
            expected = _record_hash(
                record.seq,
                record.entity_type,
                record.event,
                record.entity_id,
                record.timestamp,
                record.payload,
                record.prev_hash,
            )
            if record.hash != expected:
                return AuditVerification(
                    False, index, f"record {index} content hash mismatch (tampered)"
                )
            if record.prev_hash != previous_hash:
                return AuditVerification(
                    False,
                    index,
                    f"record {index} prev_hash does not match previous record (chain break)",
                )
            previous_hash = record.hash
            disk_hashes.append(record.hash)
        if len(lines) < len(self._entries):
            return AuditVerification(
                False,
                len(lines),
                f"audit log truncated: {len(lines)} records on disk, {len(self._entries)} expected",
            )
        trusted_root = self._read_anchor()
        if trusted_root is None:
            return AuditVerification(
                False, 0, "anchor file missing or malformed (deleted out of band)"
            )
        disk_root = merkle_root([h.encode("utf-8") for h in disk_hashes])
        if disk_root != trusted_root:
            return AuditVerification(
                False,
                None,
                f"Merkle root mismatch with anchor (chain rewritten and rehashed): {disk_root[:16]}... != {trusted_root[:16]}...",
            )
        return AuditVerification(True, None, f"chain intact: {len(lines)} records verified")

    def batch_root(self) -> str:
        """Merkle root over every record hash (TEE batch verification, Appendix A §8).

        Anchors the entire log in one value; deterministic for a given chain.
        """
        return merkle_root([record.hash.encode("utf-8") for record in self._entries])

    def export_siem(self, out_path: str | Path, hostname: str = "-") -> int:
        """Export the log as RFC 5424-ish syslog envelopes.

        Line format::

            <13>1 TIMESTAMP HOSTNAME nomos SEQ EVENT [nomos-audit entity_type=".." entity_id=".." hash=".."] <compact JSON payload>

        ``hostname`` defaults to ``-`` (NILVALUE) so exports stay
        deterministic. Returns the number of records exported.
        """

        def _sd_escape(value: str) -> str:
            return value.replace("\\", "\\\\").replace('"', '\\"').replace("]", "\\]")

        out = Path(out_path)
        count = 0
        with out.open("w", encoding="utf-8", newline="\n") as fh:
            for record in self._entries:
                sd = (
                    f'[nomos-audit entity_type="{_sd_escape(record.entity_type)}" '
                    f'entity_id="{_sd_escape(record.entity_id)}" hash="{record.hash}"]'
                )
                msg = _canonical_json(record.payload)
                fh.write(
                    f"<13>1 {record.timestamp} {hostname} nomos {record.seq} "
                    f"{_sd_escape(record.event)} {sd} {msg}\n"
                )
                count += 1
        return count
