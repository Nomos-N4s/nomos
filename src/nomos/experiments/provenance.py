"""Platform-stable provenance for the pre-registration (D3, #307).

"Pre-registered" is a claim about time, and a document living in the same
repository as its results cannot establish it by assertion. The claim is made
checkable two independent ways: a digest showing the text has not moved, and
the commit that last touched it showing the text predates the run.

Both checks are only worth as much as their reproducibility. Digesting raw
working-tree bytes makes the value depend on the checkout - a CRLF clone and an
LF clone of identical content disagree - so the digest is taken over
newline-normalised content and matches the bytes git stores. A reader on any
platform recomputes the same value, and a mismatch means the text really moved.

Paths resolve against the repository root, not the process working directory,
and every git call runs there: provenance that depended on where the validator
happened to be invoked from would be provenance about the caller.

An evidence claim that cannot be checked is reported as a problem, not passed
over. A result with no verifiable pre-registration is not a weaker result, it is
an unfalsifiable one, so "could not verify" and "verified" must never look alike.

Stdlib only, so the validator can import this without the RL extras.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from collections.abc import Mapping
from typing import Any

PREREGISTRATION_PATH = "book/appendix-e-preregistration.md"


def normalise(data: bytes) -> bytes:
    """Return data with CRLF and lone CR line endings reduced to LF."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _run(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - no git
        return None


def repo_root(start: str | None = None) -> str | None:
    """Absolute path of the enclosing git work tree, or None if there is none."""
    out = _run(["git", "rev-parse", "--show-toplevel"], cwd=start)
    if out is None or out.returncode != 0:
        return None
    return out.stdout.strip() or None


def _git(*args: str) -> str | None:
    """Run git at the repository root and return stdout, or None on failure."""
    out = _run(["git", *args], cwd=repo_root())
    if out is None or out.returncode != 0:
        return None
    return out.stdout.strip() or None


def resolve(path: str) -> str:
    """Resolve a repository-relative provenance path against the repo root.

    Falls back to the path as given when there is no repository, so the function
    stays usable on a loose checkout.
    """
    if os.path.isabs(path):
        return path
    root = repo_root()
    if root:
        return os.path.join(root, path)
    return path


def is_shallow_repository() -> bool:
    """True if the checkout lacks full history, so git cannot resolve old commits."""
    return _git("rev-parse", "--is-shallow-repository") == "true"


def content_digest(path: str) -> str | None:
    """SHA-256 of path over newline-normalised bytes, or None if unreadable.

    Equal to the digest of the blob git stores for a text file, so
    ``git show <rev>:<path> | sha256sum`` reproduces it on every platform.
    """
    try:
        with open(resolve(path), "rb") as fh:
            return hashlib.sha256(normalise(fh.read())).hexdigest()
    except OSError:
        return None


def commit_is_ancestor(commit: str, ref: str = "HEAD") -> bool | None:
    """True if commit is reachable from ref; None if it cannot be told.

    A recorded commit that a rebase orphaned is not reachable from main, so the
    ``git log`` half of the published verification fails even though the text is
    unchanged. None means git could not answer (missing binary, shallow clone) -
    an unknown, not a pass.
    """
    out = _run(["git", "merge-base", "--is-ancestor", commit, ref], cwd=repo_root())
    if out is None:  # pragma: no cover - no git
        return None
    if out.returncode == 0:
        return True
    if out.returncode == 1:
        return False
    return None  # 128: unknown revision (shallow clone, missing object)


def commit_touched_path(commit: str, path: str) -> bool | None:
    """True if commit itself modified path; None if it cannot be told.

    Reachability alone does not bind a commit to this document: any ancestor
    would satisfy it, so an unrelated (and conveniently older) commit could be
    substituted to supply the certification date. The binding checked here is
    "this commit modified this path" rather than "this is the newest commit that
    modified it", because later provenance-only corrections are expected and are
    itemised in the record.
    """
    out = _run(["git", "rev-list", "--max-count=1", commit, "--", path], cwd=repo_root())
    if out is None:  # pragma: no cover - no git
        return None
    if out.returncode != 0:
        return None  # unknown revision
    return out.stdout.strip() == commit


def preregistration_provenance(path: str = PREREGISTRATION_PATH) -> dict[str, Any]:
    """Capture checkable evidence of which pre-registration a run was bound to.

    Everything degrades to None rather than raising. A missing git binary is a
    reason to report weaker provenance, not to lose a training run - but the
    absence is recorded, so a result can never look better evidenced than it is.

    Args:
        path: Path to the pre-registration, relative to the repository root.

    Returns:
        Mapping with path, sha256, commit, committed_at and head; any field that
        could not be determined is None.
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
    which is how a platform-dependent hash survived to publication. A check that
    cannot be performed is reported too: silently accepting an unresolvable file
    or an unresolvable commit would let a frontier claim evidence it never had.
    """
    problems: list[str] = []
    if not isinstance(provenance, Mapping):
        return ["missing 'preregistration' provenance block"]

    recorded = provenance.get("sha256")
    if not recorded:
        return ["preregistration.sha256 is missing - the pre-registration is unverifiable"]

    path = provenance.get("path") or PREREGISTRATION_PATH
    actual = content_digest(path)
    if actual is None:
        problems.append(
            f"preregistration.sha256 cannot be verified: {path} is not readable at "
            f"{resolve(path)} - an unverifiable pre-registration is not a weaker "
            "claim, it is an unfalsifiable one"
        )
    elif actual != recorded:
        problems.append(
            f"preregistration.sha256 does not match {path}: "
            f"recorded {recorded[:12]}..., computed {actual[:12]}... - "
            "the pre-registration text has moved since the run it certifies"
        )

    commit = provenance.get("commit")
    if not commit:
        problems.append("preregistration.commit is missing - the date claim cannot be checked")
        return problems

    ancestor = commit_is_ancestor(commit)
    touched = commit_touched_path(commit, path)

    if ancestor is False:
        problems.append(
            f"preregistration.commit {commit[:12]}... is not an ancestor of HEAD - "
            "the recorded commit is unreachable, so its date cannot be checked"
        )
    elif touched is False:
        problems.append(
            f"preregistration.commit {commit[:12]}... never modified {path} - "
            "a reachable but unrelated commit cannot certify this document"
        )
    elif ancestor is None or touched is None:
        detail = (
            "the checkout is shallow, so git cannot see the recorded commit"
            if is_shallow_repository()
            else "git could not resolve the recorded commit"
        )
        problems.append(f"preregistration.commit {commit[:12]}... cannot be verified: {detail}")
    return problems
