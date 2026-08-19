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
BLOCK_COMMENT = re.compile(r"/-.*?-/", re.DOTALL)
LINE_COMMENT = re.compile(r"--.*")
NATIVE_DECISION = re.compile(r"native_decide|\+\s*native\b|\bnative\s*:=\s*true\b")
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


def _lean_probe(commands: list[str], what: str, extra_imports: tuple[str, ...] = ()) -> str:
    """Build the corpus and return what Lean prints for ``commands``.

    ``extra_imports`` are added after ``import GovBudgetProof`` for probes that
    need modules the corpus itself does not import -- ``Lean`` in particular,
    for probes that inspect the environment rather than a named declaration.

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

    imports = [f"import {module}" for module in ("GovBudgetProof", *extra_imports)]
    probe = "\n".join([*imports, *commands])
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


def _source_without_comments(path: Path) -> str:
    """Return the file's text with comments blanked out, line numbers preserved."""

    def blank(match: re.Match[str]) -> str:
        return "".join(c if c.isspace() else " " for c in match.group(0))

    return LINE_COMMENT.sub(blank, BLOCK_COMMENT.sub(blank, path.read_text(encoding="utf-8")))


def test_no_proof_closes_by_a_native_decision() -> None:
    """No proof in the corpus is closed by a native decision tactic (#300).

    On the pinned toolchain these tactics do not reduce in the kernel: they
    assert the compiled evaluation as a fresh opaque axiom per declaration,
    named ``<theorem>._native.<tactic>.ax_1_1``. That name contains no
    ``Classical.``, so the classical-axiom test above cannot see it.

    This is a source scan, and it covers exactly the three spellings that
    elaborate to such an axiom on leanprover/lean4:v4.32.1::

        native_decide
        decide +native
        decide (config := { native := true })

    All three were checked against the toolchain; the latter two mint
    ``._native.decide.ax_1_1`` and contain no ``native_decide`` substring, so
    an earlier substring test passed them. This scan is therefore a guard
    against known spellings, not against the bug class: a spelling not listed
    above would still slip past it.

    Comments are blanked out first, so prose naming a tactic -- including the
    module note in ``IdentityGenesis.lean`` that tells future editors not to
    reintroduce it -- does not trip the guard.
    """
    used = [
        f"{path.relative_to(REPO_ROOT).as_posix()}:{number}"
        for path in _lean_sources()
        for number, line in enumerate(_source_without_comments(path).splitlines(), 1)
        if NATIVE_DECISION.search(line)
    ]
    assert not used, (
        f"a native decision tactic closes a proof at {used}: on the pinned "
        f"toolchain it asserts the evaluation as an opaque axiom instead of "
        f"checking it, so the declaration rests on the compiler rather than on "
        f"the kernel. Use decide, or a term proof off the Prop sibling"
    )


CORPUS_AXIOM_SWEEP = """open Lean in
#eval show CoreM Unit from do
  let env ← getEnv
  let modules := env.header.moduleNames
  let corpus := modules.filter fun m => m == `GovBudgetProof || (`GovBudgetProof).isPrefixOf m
  let mut declared : Array Name := #[]
  for (name, info) in env.constants.toList do
    match info with
    | .axiomInfo _ =>
      match env.getModuleIdxFor? name with
      | some index => if corpus.contains modules[index.toNat]! then declared := declared.push name
      | none => declared := declared.push name
    | _ => pure ()
  IO.println s!"CORPUS_MODULES {corpus.toList}"
  IO.println s!"CORPUS_AXIOMS {declared.toList}"
"""


def _swept_names(stdout: str, marker: str) -> list[str]:
    """Return the Lean name list printed on the sweep's ``marker`` line."""
    printed = [line for line in stdout.splitlines() if line.startswith(marker + " ")]
    assert len(printed) == 1, f"the sweep printed {len(printed)} {marker} lines:\n{stdout}"
    inside = printed[0][len(marker) + 1 :].strip()
    assert inside.startswith("[") and inside.endswith("]"), f"unparsable line: {printed[0]}"
    return [item.strip() for item in inside[1:-1].split(",") if item.strip()]


def test_lean_corpus_declares_no_axioms_of_its_own() -> None:
    """No module in the proof corpus declares an axiom of its own (issue #300).

    A native decision tactic works by declaring a fresh axiom in the module
    being elaborated and asserting the compiled evaluation as its statement --
    ``<theorem>._native.native_decide.ax_1_1`` for ``native_decide``,
    ``<theorem>._native.decide.ax_1_1`` for ``decide +native``. A hand-written
    ``axiom`` command does the same thing. This sweeps the elaborated
    environment rather than the source text, so it catches every such
    declaration however the tactic is spelled, including spellings that did not
    exist when it was written.

    What it does not cover: an anonymous ``example`` leaves nothing behind in
    the environment -- not the axiom, not any constant at all -- so a native
    decision inside one is invisible here. Four of the occurrences #300 removed
    sat in ``example`` blocks, so the gap is real, and the source scan in
    ``test_no_proof_closes_by_a_native_decision`` is what covers it. Neither
    check subsumes the other.

    The ``CORPUS_MODULES`` assertion is what stops this passing vacuously: if
    the module filter ever stopped matching, the axiom list would come back
    empty for the wrong reason and the test would still be green.

    Skipped without a Lean toolchain; the ``lean-build`` CI job installs one
    and runs this file.
    """
    stdout = _lean_probe([CORPUS_AXIOM_SWEEP], "the corpus's own axiom declarations", ("Lean",))

    modules = _swept_names(stdout, "CORPUS_MODULES")
    assert "GovBudgetProof.IdentityGenesis" in modules, (
        f"the sweep matched no GovBudgetProof modules, so an empty axiom list "
        f"would say nothing about the corpus; it saw {modules}"
    )

    declared = _swept_names(stdout, "CORPUS_AXIOMS")
    assert not declared, (
        f"the corpus declares axioms of its own: {declared}. An axiom is "
        f"asserted, not proven, so every declaration reaching one rests on "
        f"that assertion rather than on the kernel. A ``._native.`` name means "
        f"a native decision tactic asserted a compiled evaluation; use decide, "
        f"or a term proof off the Prop sibling"
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
    """The immutable-tier invariance is routed through the tier model.

    An import that is never used would satisfy the source check above while
    leaving the two models as disconnected as they were before it. So this
    reads the elaborated proof terms instead: the headlined theorem must reach
    ``immutable_parameters_never_change`` through the generic tier gate.

    The equation those theorems state is definitional -- ``isPermitted
    Tier.immutable`` reduces to ``False``, so ``rfl`` would close it too --
    which is why the routing needs a guard at all: nothing in the build would
    notice if a proof stopped mentioning the tier theorem. This test pins that
    routing convention; it is not a measure of proof strength.
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
        f"so the link to the tier model is no longer carried by the proof "
        f"term:\n{stdout}"
    )
