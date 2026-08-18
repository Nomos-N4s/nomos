"""Tests that the Lean claims made in prose are backed by the Lean corpus.

The root README headlines a short list of theorem names under "By the Numbers".
These tests hold that list to two standards: every name is really declared in
``gov-budget-proof/``, and no declaration's proof term reaches a classical
axiom, which would mean the goal was closed by excluded middle and so holds
for any ``Prop`` at all.

An axiom-free proof term is a necessary condition for a headline claim, not a
sufficient one: it rules out excluded middle, not a statement that is trivially
true of the model. Whether each headlined statement says something about the
governance model is a judgement no source check makes for us.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
README_PATH = REPO_ROOT / "README.md"
LEAN_ROOT = REPO_ROOT / "gov-budget-proof"
VOTE_MODULE = LEAN_ROOT / "GovBudgetProof" / "VoteAndFalsification.lean"
TIER_MODULE = LEAN_ROOT / "GovBudgetProof" / "IdentityTiers.lean"
TIER_IMPORT = "import GovBudgetProof.IdentityTiers"

HEADLINE_LABEL = "Lean 4 theorems proven:"
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_'!?]*")
DECL_START = re.compile(
    r"^(?:@\[[^\]]*\]\s*)?"
    r"(?:private\s+|protected\s+|noncomputable\s+)*"
    r"(?:theorem|lemma|instance|def|abbrev|example|structure|inductive)\b"
)
AXIOM_REPORT = re.compile(r"^'([^']+)' (.+)$", re.MULTILINE)
LEAN_TIMEOUT_SECONDS = 600
VOTE_DECLARATIONS = (
    "decidableVotePasses",
    "vote_outcome_computes",
    "vote_resolution_total",
    "governance_cycle_invariant",
    "decidableIsPermitted",
    "governance_step_unchanged_at_immutable_tier",
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


def _lean_probe(commands: list[str], what: str) -> str:
    """Build the corpus and return what Lean prints for ``commands``.

    Skipped when the pinned toolchain is absent; the Lean CI job runs this with
    the toolchain installed.
    """
    lake = shutil.which("lake")
    if lake is None:
        pytest.skip(f"lake is not on PATH, so {what} cannot be resolved")

    build = subprocess.run(
        [lake, "build", "GovBudgetProof"],
        cwd=LEAN_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=LEAN_TIMEOUT_SECONDS,
    )
    assert build.returncode == 0, f"lake build failed:\n{build.stdout}\n{build.stderr}"

    probe = "\n".join(["import GovBudgetProof", *commands])
    with tempfile.TemporaryDirectory() as directory:
        probe_path = Path(directory) / "Probe.lean"
        probe_path.write_text(probe + "\n", encoding="utf-8")
        printed = subprocess.run(
            [lake, "env", "lean", str(probe_path)],
            cwd=LEAN_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=LEAN_TIMEOUT_SECONDS,
        )

    assert printed.returncode == 0, (
        f"Lean rejected the {what} probe, so at least one name is not declared "
        f"in the corpus:\n{printed.stdout}\n{printed.stderr}"
    )
    return printed.stdout


def _axiom_dependencies(names: list[str]) -> dict[str, str]:
    """Return what ``#print axioms`` reports for each of ``names``.

    Lean resolves the whole proof term, so a classical dependency reached
    through an intermediate lemma is reported here even when the declaration's
    own source text never spells ``Classical``.
    """
    stdout = _lean_probe([f"#print axioms {name}" for name in names], "Lean axiom dependencies")
    reported = dict(AXIOM_REPORT.findall(stdout))
    missing = [name for name in names if name not in reported]
    assert not missing, f"Lean reported no axioms line for {missing}:\n{stdout}"
    return reported


def test_readme_headline_theorems_are_declared() -> None:
    """Every headlined theorem is a real declaration in the Lean corpus."""
    names = _headline_theorem_names()
    assert names, "the README headline list of Lean theorems is empty"

    for name in names:
        assert IDENTIFIER.fullmatch(name), f"{name!r} is not a Lean identifier"
        _declaration_body(name)


def test_headline_and_vote_declarations_depend_on_no_classical_axiom() -> None:
    """Lean reports the axiom base of every headlined and vote declaration."""
    names = list(dict.fromkeys(_headline_theorem_names() + list(VOTE_DECLARATIONS)))
    for name, axioms in _axiom_dependencies(names).items():
        assert "Classical." not in axioms, (
            f"{name} {axioms}: a classical axiom anywhere in the proof term "
            f"means the declaration is closed by excluded middle somewhere in "
            f"its dependencies, which holds for any Prop and so claims nothing "
            f"about the model it names"
        )


def test_vote_passes_has_a_decidable_instance() -> None:
    """votePasses is decided by computation rather than postulated."""
    source = VOTE_MODULE.read_text(encoding="utf-8")
    assert "Decidable (votePasses votes d)" in source, (
        "VoteAndFalsification.lean must declare a Decidable instance for "
        "votePasses so vote outcomes are computed rather than postulated"
    )
    _declaration_body("decidableVotePasses")


def test_governance_cycle_invariant_uses_the_decision_procedure() -> None:
    """The combined invariant rests on the decision procedure, not on a disjunction."""
    _, body = _declaration_body("governance_cycle_invariant")
    assert "vote_outcome_computes" in body, (
        "governance_cycle_invariant must state its vote conjunct over the "
        "Decidable instance (via vote_outcome_computes), not over an "
        "excluded-middle disjunction"
    )


def test_falsification_module_imports_the_tier_model() -> None:
    """The falsification parameters can only be tiered if the tiers are in scope."""
    assert TIER_MODULE.exists(), f"{TIER_MODULE} is the tier model the import names"
    assert TIER_IMPORT in VOTE_MODULE.read_text(encoding="utf-8"), (
        f"VoteAndFalsification.lean must {TIER_IMPORT!r}: without it the "
        f"falsification parameters are linked to the tier model by prose only"
    )


def test_falsification_invariance_derives_from_the_tier_theorem() -> None:
    """The immutable-tier invariance really rests on the tier model.

    An import that is never used would satisfy the source check above while
    leaving the two models as disconnected as they were before it. So this
    reads the elaborated proof terms instead: the headlined theorem must reach
    ``immutable_parameters_never_change`` through the generic tier gate.
    """
    headline = "falsification_params_unchanged_at_immutable_tier"
    generic = "governance_step_unchanged_at_immutable_tier"
    stdout = _lean_probe([f"#print {headline}", f"#print {generic}"], "Lean proof terms")

    printed = stdout.split(f"theorem {generic}")
    assert len(printed) == 2, f"Lean printed no proof term for {generic}:\n{stdout}"
    assert generic in printed[0], (
        f"{headline} does not use {generic}, so its proof no longer routes "
        f"through the tier gate:\n{stdout}"
    )
    assert "immutable_parameters_never_change" in printed[1], (
        f"{generic} does not use IdentityTiers.immutable_parameters_never_change, "
        f"so the immutable tier is asserted here rather than derived:\n{stdout}"
    )
