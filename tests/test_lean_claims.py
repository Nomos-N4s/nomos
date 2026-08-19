"""Tests that the Lean claims made in prose are backed by the Lean corpus.

The root README headlines a short list of theorem names under "By the Numbers".
These tests hold that list to two standards: every name is really declared in
``gov-budget-proof/``, and no declaration's proof term reaches a classical
axiom, which would mean the goal was closed by excluded middle and so holds
for any ``Prop`` at all.

The prediction-to-theorem map in ``src/nomos/prove/predictions.py`` is held to
the first of those standards too, since it names theorems in the same way and
is published as a table in the book.

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

from src.nomos.prove.predictions import LEAN_COVERAGE

REPO_ROOT = Path(__file__).parent.parent
README_PATH = REPO_ROOT / "README.md"
BOOK_PATH = REPO_ROOT / "book" / "formal-verification-lean.md"
COVERAGE_HEADING = "## Prediction coverage"
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
DECLARED_NAME = re.compile(
    r"^(?:private\s+|protected\s+|noncomputable\s+)*"
    r"(?:theorem|lemma|instance|def|abbrev)\s+([A-Za-z_][A-Za-z0-9_'!?]*)"
)
AXIOM_REPORT = re.compile(r"^'([^']+)' (.+)$", re.MULTILINE)
BACKTICKED = re.compile(r"`([^`]+)`")
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


def _declared_names() -> dict[str, Path]:
    """Return every named declaration in the corpus, mapped to its file.

    Anonymous ``example`` blocks carry no name and so are absent, which is
    why this cannot stand in for the axiom sweep. It is a source scan, so it
    needs no Lean toolchain.
    """
    found: dict[str, Path] = {}
    for path in _lean_sources():
        for line in path.read_text(encoding="utf-8").splitlines():
            match = DECLARED_NAME.match(line)
            if match:
                found.setdefault(match.group(1), path)
    return found


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
    """Return the file's text with comments blanked out, line numbers preserved.

    Scans the source rather than pattern-matching it. Two properties of Lean
    defeat a regex pass, and both fail *open* - they blank real code, which
    silently disarms the guard below rather than tripping it:

    * ``/-`` inside a string literal opens no comment, but a regex treats it
      as one and blanks everything through the next genuine ``-/``.
    * Block comments nest, so the first ``-/`` does not necessarily close the
      comment a ``/-`` opened.

    Character literals are deliberately not tracked: ``'`` is an identifier
    character in Lean (``bs'``), so treating it as a delimiter would mis-scan
    far more often than it would help.
    """
    text = path.read_text(encoding="utf-8")
    out: list[str] = []
    index = 0
    length = len(text)
    depth = 0
    while index < length:
        if depth:
            if text.startswith("/-", index):
                depth += 1
                out.append("  ")
                index += 2
            elif text.startswith("-/", index):
                depth -= 1
                out.append("  ")
                index += 2
            else:
                character = text[index]
                out.append(character if character.isspace() else " ")
                index += 1
            continue
        if text.startswith("/-", index):
            depth = 1
            out.append("  ")
            index += 2
            continue
        if text.startswith("--", index):
            stop = text.find("\n", index)
            stop = length if stop == -1 else stop
            out.append("".join(c if c.isspace() else " " for c in text[index:stop]))
            index = stop
            continue
        if text[index] == chr(34):
            out.append(chr(34))
            index += 1
            while index < length:
                if text[index] == "\\" and index + 1 < length:
                    out.append(text[index : index + 2])
                    index += 2
                    continue
                out.append(text[index])
                index += 1
                if text[index - 1] == chr(34):
                    break
            continue
        out.append(text[index])
        index += 1
    return "".join(out)


def test_comment_stripper_does_not_blank_live_code(tmp_path: Path) -> None:
    """The source guard must not be disarmed by a comment-shaped string.

    ``_source_without_comments`` decides what the native-decision scan can
    see, so any way of making it blank live code is a hole in that guard --
    and one that fails silently, because a blanked proof simply is not
    scanned. Two shapes broke the regex it replaced: a string literal
    containing ``/-``, which opened a comment that ran to the next genuine
    ``-/`` and swallowed everything between, and a nested block comment,
    whose first ``-/`` does not close the outer one.

    Anonymous ``example`` blocks are exactly what this must protect: they
    carry no name, so ``test_lean_corpus_declares_no_axioms_of_its_own``
    cannot see them and this scan is their only guard.
    """
    live = {
        "string literal holding a comment opener": (
            'def s : String := "holds /- an opener"\n\n'
            "example : (1 : Nat) = 1 := by native_decide\n\n/- a real comment -/\n"
        ),
        "nested block comment": (
            "/- outer /- inner -/ still commented -/\nexample : (1 : Nat) = 1 := by native_decide\n"
        ),
    }
    for description, source in live.items():
        probe = tmp_path / "live.lean"
        probe.write_text(source, encoding="utf-8")
        assert NATIVE_DECISION.search(_source_without_comments(probe)), (
            f"the native decision is live code but the stripper hid it: {description}"
        )

    commented = {
        "inside a block comment": "/- example : (1 : Nat) = 1 := by native_decide -/\n",
        "after a line comment": "-- example : (1 : Nat) = 1 := by native_decide\n",
    }
    for description, source in commented.items():
        probe = tmp_path / "commented.lean"
        probe.write_text(source, encoding="utf-8")
        assert not NATIVE_DECISION.search(_source_without_comments(probe)), (
            f"a commented-out tactic was reported as live: {description}"
        )


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

    The bug class is guarded by the sweep in
    ``test_lean_corpus_declares_no_axioms_of_its_own``, which reads the
    elaborated environment and so does not care how the tactic is spelled.
    This scan is still needed alongside it for the one case that sweep cannot
    see: an anonymous ``example`` leaves no constant in the environment, so a
    native decision inside one is invisible to any axiom check. That case is
    not hypothetical: ``IdentityHashes.lean`` carried four such uses inside
    anonymous ``example`` blocks until #299 rewrote the file. This scan also
    runs without a Lean toolchain, where the sweep skips.

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
    decision inside one is invisible here. The gap is real: ``IdentityHashes``
    carried four such uses inside anonymous ``example`` blocks until #299
    rewrote the file. The source scan in
    ``test_no_proof_closes_by_a_native_decision`` is what covers that case.
    Neither check subsumes the other.

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


def test_prediction_coverage_names_declarations_the_corpus_has() -> None:
    """Every Lean name in the prediction coverage map is really declared (#305).

    ``LEAN_COVERAGE`` is the repo's prediction-to-theorem map and the source
    of the coverage table in ``book/formal-verification-lean.md``. A name in
    it that the corpus does not declare would leave a published table
    pointing at nothing, which is not hypothetical: the issue that asked for
    this map cited ``vote_resolution_deterministic``, a name the corpus has
    not declared since the commit that replaced it with a constructive
    proof.

    The check says nothing about whether a named theorem is *about* the
    prediction beside it. That judgement is in the map's ``note`` fields and
    in the book, and no source check makes it for us.

    A source scan, so it runs with no Lean toolchain installed.
    """
    declared = _declared_names()

    modules = [path for path in _lean_sources() if path.parent.name == "GovBudgetProof"]
    assert modules, f"no proof modules under {LEAN_ROOT}, so the scan proves nothing"
    silent = sorted(path.name for path in modules if path not in declared.values())
    assert not silent, (
        f"the declaration scan found no declaration at all in {silent}, so a "
        f"missing name would go unnoticed and this test would pass for the "
        f"wrong reason"
    )

    missing = {
        f"P{pid:02d}": [name for name in coverage.declarations if name not in declared]
        for pid, coverage in sorted(LEAN_COVERAGE.items())
        if any(name not in declared for name in coverage.declarations)
    }
    assert not missing, (
        f"the prediction coverage map names Lean declarations the corpus does "
        f"not have: {missing}. Either the declaration was renamed or removed "
        f"and the map still points at the old name, or the map claims a "
        f"counterpart that was never there. Re-derive the row against "
        f"{LEAN_ROOT}, and if the prediction has no counterpart any more, say "
        f"so with LeanStatus.NO_COUNTERPART rather than by dropping the row"
    )

    malformed = {
        f"P{pid:02d}": [name for name in coverage.declarations if not IDENTIFIER.fullmatch(name)]
        for pid, coverage in sorted(LEAN_COVERAGE.items())
        if any(not IDENTIFIER.fullmatch(name) for name in coverage.declarations)
    }
    assert not malformed, f"these are not Lean identifiers: {malformed}"


def _book_coverage_table() -> dict[int, tuple[str, tuple[str, ...]]]:
    """Return the coverage table published in the book, keyed by prediction id.

    Each value is the row's coverage wording and the Lean declarations it
    names, in the order it names them.
    """
    text = BOOK_PATH.read_text(encoding="utf-8")
    _, heading, after = text.partition(COVERAGE_HEADING)
    assert heading, f"{BOOK_PATH} has no {COVERAGE_HEADING!r} section"

    published: dict[int, tuple[str, tuple[str, ...]]] = {}
    for line in after.splitlines():
        if line.startswith("## "):
            break
        if not line.startswith("| P"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        assert len(cells) == 4, f"the coverage row has {len(cells)} cells: {line}"
        identifier = int(cells[0].lstrip("P"))
        assert identifier not in published, f"P{identifier:02d} has two rows in the table"
        published[identifier] = (cells[2], tuple(BACKTICKED.findall(cells[3])))
    return published


def test_book_prediction_coverage_table_matches_the_map() -> None:
    """The published coverage table says what LEAN_COVERAGE says (#305).

    The table in ``book/formal-verification-lean.md`` is rendered from
    ``LEAN_COVERAGE``, and a rendered table drifts from its source the moment
    someone edits one of them -- which is the whole failure this epic is
    remediating. Re-deriving a row in the map without re-rendering the table
    fails here, and so does editing a cell by hand.

    The names themselves are checked against the corpus by
    ``test_prediction_coverage_names_declarations_the_corpus_has``; this test
    only holds the two published forms to each other.
    """
    published = _book_coverage_table()
    assert published, (
        f"no coverage rows parsed out of {BOOK_PATH}: the table is gone, or "
        f"its rows no longer start with '| P'"
    )

    expected = {
        identifier: (coverage.status.value, coverage.declarations)
        for identifier, coverage in LEAN_COVERAGE.items()
    }
    differing = sorted(
        identifier
        for identifier in set(published) | set(expected)
        if published.get(identifier) != expected.get(identifier)
    )
    assert not differing, (
        f"the coverage table in {BOOK_PATH.name} and LEAN_COVERAGE in "
        f"src/nomos/prove/predictions.py disagree about "
        f"{[f'P{i:02d}' for i in differing]}. The map is the source: "
        f"published={ {i: published.get(i) for i in differing} }, "
        f"map={ {i: expected.get(i) for i in differing} }"
    )
