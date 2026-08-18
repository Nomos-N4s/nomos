"""Platform-stable provenance for the pre-registration (D3, #307).

"Pre-registered" is a claim about time, and a document living in the same
repository as its results cannot establish it by assertion. The claim is made
checkable two independent ways: a digest showing the text has not moved, and
the commit that last touched it showing the text predates the run.

Both checks are only worth as much as their reproducibility. Digesting raw
working-tree bytes makes the value depend on the reader's checkout — a CRLF
clone and an LF clone of identical content disagree — so the digest is taken
over newline-normalised content and matches the bytes git stores. A reader on
any platform recomputes the same value, and a mismatch means the text really
did move.

Stdlib only, so the validator can import this without the RL extras.
"""

from __future__ import annotations

import hashlib
import subprocess
from typing import Any

PREREGISTRATION_PATH = "book/appendix-e-preregistration.md"


def normalise(data: bytes) -> bytes:
    """Return ``data`` with CRLF and lone CR line endings reduced to LF."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def content_digest(path: str) -> str | None:
    """SHA-256 of ``path`` over newline-normalised bytes, or None if unreadable.

    Equal to the digest of the blob git stores for a text file, so
    ``git show HEAD:<path> | sha256sum`` reproduces it on every platform.
    """
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(normalise(fh.read())).hexdigest()
    except OSError:
        return None


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - no git
        return None
    if out.returncode != 0:
        return None
    value = out.stdout.strip()
    return value or None


def commit_is_ancestor(commit: str, ref: str = "HEAD") -> bool | None:
    """True if ``commit`` is reachable from ``ref``; None if it cannot be told.

    A recorded commit that a rebase orphaned is not reachable from ``main``, so
    the ``git log`` half of the published verification fails even though the
    text is unchanged. None means git could not answer (missing binary, shallow
    clone) — an unknown, not a failure.
    """
    try:
        out = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, ref],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - no git
        return None
    if out.returncode == 0:
        return True
    if out.returncode == 1:
        return False
    return None  # 128: unknown revision (shallow clone, missing object)


def preregistration_provenance(path: str = PREREGISTRATION_PATH) -> dict[str, Any]:
    """Capture checkable evidence of *which* pre-registration a run was bound to.

    Everything degrades to ``None`` rather than raising. A missing git binary is
    a reason to report weaker provenance, not to lose a training run — but the
    absence is recorded, so a result can never look better evidenced than it is.

    Args:
        path: Path to the pre-registration, relative to the repository root.

    Returns:
        Mapping with ``path``, ``sha256``, ``commit``, ``committed_at`` and
        ``head``; any field that could not be determined is ``None``.
    """
    provenance: dict[str, Any] = {
        "path": path,
        "sha256": None,
        "commit": None,
        "committed_at": None,
        "head": None,
    }
    digest = content_digest(path)
    if digest is None:
        return provenance
    provenance["sha256"] = digest
    provenance["commit"] = _git("log", "-1", "--format=%H", "--", path)
    provenance["committed_at"] = _git("log", "-1", "--format=%cI", "--", path)
    provenance["head"] = _git("rev-parse", "HEAD")
    return provenance


def verify_preregistration(provenance: Any) -> list[str]:
    """Return problems with a recorded provenance block (empty = verified).

    Recording a digest and never comparing it lets a wrong value sit unnoticed,
    which is how a platform-dependent hash survives to publication. Unknowns
    (no git, file absent from this checkout) are not reported as failures — only
    a digest that demonstrably disagrees, or a commit git can prove unreachable.
    """
    from collections.abc import Mapping

    problems: list[str] = []
    if not isinstance(provenance, Mapping):
        return ["missing 'preregistration' provenance block"]

    recorded = provenance.get("sha256")
    if not recorded:
        return ["preregistration.sha256 is missing — the pre-registration is unverifiable"]

    path = provenance.get("path") or PREREGISTRATION_PATH
    actual = content_digest(path)
    if actual is not None and actual != recorded:
        problems.append(
            f"preregistration.sha256 does not match {path}: "
            f"recorded {recorded[:12]}…, computed {actual[:12]}… — "
            "the pre-registration text has moved since the run it certifies"
        )

    commit = provenance.get("commit")
    if commit and commit_is_ancestor(commit) is False:
        problems.append(
            f"preregistration.commit {commit[:12]}… is not an ancestor of HEAD — "
            "the recorded commit is unreachable, so its date cannot be checked"
        )
    return problems
