"""Tests that the Lean claims made in prose are backed by the Lean corpus.

The root README headlines a short list of theorem names under "By the Numbers".
These tests hold that list to two standards: every name is really declared in
``gov-budget-proof/``, and none of them is discharged by the law of excluded
middle, which would make the headline claim independent of the model it names.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
README_PATH = REPO_ROOT / "README.md"
LEAN_ROOT = REPO_ROOT / "gov-budget-proof"
VOTE_MODULE = LEAN_ROOT / "GovBudgetProof" / "VoteAndFalsification.lean"

HEADLINE_LABEL = "Lean 4 theorems proven:"
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_'!?]*")
DECL_START = re.compile(
    r"^(?:@\[[^\]]*\]\s*)?"
    r"(?:private\s+|protected\s+|noncomputable\s+)*"
    r"(?:theorem|lemma|instance|def|abbrev|example|structure|inductive)\b"
)


def _headline_theorem_names() -> list[str]:
    """Return the theorem names the README lists under "Lean 4 theorems proven"."""
    lines = README_PATH.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(HEADLINE_LABEL):
            continue
        collected = [line[len(HEADLINE_LABEL) :]]
        for continuation in lines[index + 1 :]:
            if not continuation.strip() or not continuation[0].isspace():
                break
            collected.append(continuation)
        names = [part.strip() for part in " ".join(collected).split(",")]
        return [name for name in names if name]
    pytest.fail(f"README.md has no line starting with {HEADLINE_LABEL!r}")


def _lean_sources() -> list[Path]:
    """Return every Lean source file in the proof corpus, build output excluded."""
    return sorted(path for path in LEAN_ROOT.rglob("*.lean") if ".lake" not in path.parts)


def _declaration_body(name: str) -> tuple[Path, str]:
    """Return the file and source text of the declaration named ``name``.

    The body runs from the declaration header to the line before the next
    top-level declaration or comment block.
    """
    header = re.compile(
        r"^(?:private\s+|protected\s+|noncomputable\s+)*"
        r"(?:theorem|lemma|instance|def|abbrev)\s+" + re.escape(name) + r"\b"
    )
    for path in _lean_sources():
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if not header.match(line):
                continue
            body = [line]
            for following in lines[index + 1 :]:
                if DECL_START.match(following) or following.startswith("/-"):
                    break
                body.append(following)
            return path, "\n".join(body)
    pytest.fail(f"no Lean declaration named {name!r} in {LEAN_ROOT}")


def test_readme_headline_theorems_exist_and_are_not_vacuous() -> None:
    """Every headlined theorem is declared, and none is proved by Classical.em."""
    names = _headline_theorem_names()
    assert names, "the README headline list of Lean theorems is empty"

    for name in names:
        assert IDENTIFIER.fullmatch(name), f"{name!r} is not a Lean identifier"
        path, body = _declaration_body(name)
        assert "Classical." not in body, (
            f"{name} is headlined in README.md as proven but its proof in "
            f"{path.name} appeals to Classical — an excluded-middle proof holds "
            f"for any Prop and so claims nothing about the model it names"
        )


def test_vote_passes_has_a_constructive_decidable_instance() -> None:
    """votePasses is decided by computation, with no classical axiom in the proof."""
    source = VOTE_MODULE.read_text(encoding="utf-8")
    assert "Decidable (votePasses votes d)" in source, (
        "VoteAndFalsification.lean must declare a Decidable instance for "
        "votePasses so vote outcomes are computed rather than postulated"
    )

    _, body = _declaration_body("decidableVotePasses")
    assert "Classical" not in body, (
        "decidableVotePasses must be constructive: a Classical dependency here "
        "defeats the point of the instance"
    )


def test_governance_cycle_invariant_uses_the_decision_procedure() -> None:
    """The combined invariant rests on the decision procedure, not on Classical.em."""
    _, body = _declaration_body("governance_cycle_invariant")
    assert "Classical" not in body
    assert "vote_outcome_computes" in body, (
        "governance_cycle_invariant must state its vote conjunct over the "
        "Decidable instance (via vote_outcome_computes), not over an "
        "excluded-middle disjunction"
    )
