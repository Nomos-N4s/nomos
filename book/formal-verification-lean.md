---
title: "Lean 4 Formal Verification"
description: "Inventory of the Lean 4 proof modules in gov-budget-proof: the machine-checked counterpart to the Identity Layer chapter (Chapter 4)."
---

# Lean 4 Formal Verification

The formal framework is backed by machine-checked proofs written in [Lean 4](https://lean-lang.org/).
The proof library lives in `gov-budget-proof/` and is enforced in CI: every pull
request runs the `lean-build` job (`lake build`), so a broken proof blocks a merge.

## Scope and limits

**These are machine-checked properties of Lean models of the protocol. They
are not properties of the Python in `src/nomos/`.** Nothing extracts the model
from `speaker.py`, and no refinement argument connects the two. That limit is
stated in the same words, and argued at length, in
[Chapter 5, Sec 7](chapter-05/05-related-work.md#7-where-to-attack-this-chapter);
that section is the canonical statement of it, and this one exists so the
caveat travels with the inventory instead of being findable only in the
related-work chapter.

Concretely, five links a reader might assume exist do not:

- **No extraction.** `gov-budget-proof/lakefile.toml` declares one `lean_lib`
  and one `lean_exe` and no codegen target. The executable, `Main.lean`, is a
  sequence of `IO.println` string literals: it computes nothing, and it reads
  nothing from the Python side.
- **No refinement argument.** No statement in the corpus relates a Lean
  definition to a Python function. `BudgetEnforcement.lean` reasons over its
  own `BudgetState` and `processProposal`; `src/nomos/speaker.py` implements
  the same gate as `_apply_budgets`. The two were written independently.
- **No differential test.** The `lean-build` CI job compiles the proofs and
  runs the guards in `tests/test_lean_claims.py`, which hold the corpus
  to its own claims: that every headlined theorem name is really declared;
  that no proof term reaches a classical axiom; that no proof is closed by a
  native decision tactic and no module declares an axiom of its own (the two
  halves of the #300 guard, one a source scan, one a sweep of the elaborated
  environment); that `votePasses` is decided by computation and the
  governance-cycle invariant rests on that decision procedure; that the
  falsification results are derived from the tier model rather than restated
  beside it; and that the prediction coverage map below names only
  declarations the corpus really has, and that the table and the README
  figures published from that map still agree with it. Every one of them
  reads the Lean sources or the prose that names them; the coverage guards
  also import the map from `src/nomos/prove/predictions.py`, but only to read
  it. None executes governance code from `src/nomos/`, and nothing anywhere
  runs a Lean decision and a Python one over the same input and compares them.
- **No binding identifiers.** Lean names do appear outside
  `gov-budget-proof/`, but nothing is bound to them: no Python object
  imports, extracts or takes its meaning from a Lean declaration. They appear
  in prose, as `processProposal` in Chapter 5; in docstrings saying the Python
  mirrors the Lean model, as `quorumCount` in `src/nomos/identity/keys.py` and
  `tests/test_keys.py`; as the string literals `tests/test_lean_claims.py`
  scans the Lean sources for; and as the `declarations` of `LEAN_COVERAGE` in
  `src/nomos/prove/predictions.py` — a shipped module, whose names the prove
  runner prints and the exported results JSON carries. A docstring or a table
  cell asserting a correspondence is a claim, not a mechanism that checks one;
  for the genesis quorum a Python test does check the corresponding property,
  but by hand, in Python, against no Lean artefact (see below). One kind of
  drift is caught now: the coverage guards fail if the corpus stops declaring
  a name the map lists, or declares it under a kind the row does not claim.
  That holds the map to the corpus's names, not the models to each other — a
  theorem and the assert beside it can come to say different things, and
  nothing fails.
- **Different numeric types.** The Lean model is `Nat` throughout —
  `IdentityCoherence.lean`'s `COHERENCE_THRESHOLD : Nat := 70` on a 0–100
  scale, `IdentityTiers.lean`'s `CONSTITUTIONAL_QUORUM : Nat := 3` as a count.
  The Python thresholds are `float` — `enactment_threshold: float = 0.66` as a
  fraction, `identity_coherence` on 0.0–1.0. The κ₂ budget is the one
  exception, a count on both sides, so the flagship budget theorem is not
  type-mismatched — merely unlinked.

None of that makes the corpus empty, and it should not be undersold either:
102 theorems across the seven modules below plus the manifest, zero `sorry`,
zero axioms declared by the corpus itself, no Mathlib and no other dependency
at all (`gov-budget-proof/lakefile.toml` declares no `require`), all of it
re-checked by the Lean kernel on every pull request. What is missing is the
bridge, not the proofs. That the implementation matches the specification is
**tested, not proven** — by `tests/test_speaker.py` for the κ₂ gate, by
`tests/test_keys.py::TestGenesisQuorumIntegrity` for the genesis quorum, and
by the pre-registered adversarial run in
[Appendix E](appendix-e-rl-adversary.md). The genesis one is the closest thing
the repo has to a model/code link: `double_signing_cannot_reach_quorum_alone`
proves `¬ genesisAccepted [a, a]` of the Lean model, and
`test_one_principal_cannot_reach_quorum_alone` asserts the same property of
`GenesisMultisig` — one principal signing three times leaves
`signatures_count == 1` and `is_authorized is False`. That is a real check on
the Python side, written and maintained by hand, not a mechanism that would
catch the Lean model and the Python drifting apart.

## Status

- **Identity Layer — done (2026-08-10).** Five proof modules for Chapter 4 were
  merged to `main` as stacked pull requests #195-#199 (stack #200, commit
  `f56efa4`). Epic #69 and its sub-issues #190-#194 are closed.
- **TEE isolation model — next (issue #70).** Formalization of
  [Appendix A](/book/appendix-a/tee-isolation) is planned.

## Module inventory

| Module | Proves | Source |
|---|---|---|
| `GovBudgetProof.lean` | Manifest importing all modules below | `gov-budget-proof/` |
| `BudgetEnforcement.lean` | Budget/threshold enforcement invariants (issues #43/#44) | `gov-budget-proof/GovBudgetProof/` |
| `VoteAndFalsification.lean` | Vote-threshold determinism, falsification counting and budget halving; falsification parameters declared immutable-tier and unchanged by a governance step gated on that tier | `gov-budget-proof/GovBudgetProof/` |
| `IdentityTiers.lean` | Tier mutability rules, and the constitutional modification bar stated against the imported `GENESIS_QUORUM` — [Chapter 4, Sec 3](/book/chapter-04/04-identity-layer) | `gov-budget-proof/GovBudgetProof/` |
| `IdentityGenesis.lean` | Genesis 3-of-5 multisig bootstrapping — [Chapter 4, Sec 4](/book/chapter-04/04-identity-layer) | `gov-budget-proof/GovBudgetProof/` |
| `IdentityBuffer.lean` | Sandboxed isolation buffer protocol; monitor approvals and the external key-holder audit are counted rather than flagged, the audit gate reusing the genesis 3-of-5 quorum — [Chapter 4, Sec 5.2](/book/chapter-04/04-identity-layer) | `gov-budget-proof/GovBudgetProof/` |
| `IdentityHashes.lean` | Runtime integrity hash chains over an uninterpreted hash; the root separates two bindings exactly as far as it separates their digests, and the digest packing is proved to collide, so tamper evidence is conditional on the two records having different digests — a claim about the digests that collision-resistance of the hash does not deliver; TEE.verify_binding takes the genesis commitment as its own argument and does not take the proposed binding at all, so the verdict is a function of the runtime and that commitment alone — where the caller obtained the commitment is an assumption of the model, disclosed in the module header, not a theorem — [Chapter 4, Sec 2.1 and 6.1](/book/chapter-04/04-identity-layer) | `gov-budget-proof/GovBudgetProof/` |
| `IdentityCoherence.lean` | Coherence threshold guard; below-threshold actions are rejected without mutating identity state — [Chapter 4, Sec 6.1](/book/chapter-04/04-identity-layer) | `gov-budget-proof/GovBudgetProof/` |

The table lists every module under `gov-budget-proof/GovBudgetProof/`, so
seven proof modules plus the manifest. It had one more row until issue #298:
`Basic.lean`, described here as "Core definitions (budget, thresholds)", was
in fact the unmodified `lake new` template `def hello := "world"` — imported
by the manifest and by nothing else. Issue #298 asked for the row to be
corrected or for the file to gain the definitions it claimed; the module was
deleted instead, which is a third route and is recorded here so it can be
reviewed as one.

## Prediction coverage

The repository ships 12 formal predictions, listed in the README and run with
`python -m src.nomos.runner prove --all`. They are Python asserts over
`src/nomos/`: running them runs no Lean, and a passing prediction is a passing
test, not a discharged proof obligation. This table records what the corpus
has to say about the same property, and where it has nothing to say.

| # | Prediction | Coverage | Lean declarations |
|---|---|---|---|
| P01 | Ch2 §3.1 — Budget caps proposals per member (κ₂) | proved of the Lean model | `budget_invariant_holds`, `budget_never_exceeded` |
| P02 | Ch2 §3.2 — CRITICAL_SAFETY priority before ROUTINE | no counterpart | — |
| P03 | Ch2 §3.4 — Weighted vote outcome matches formal spec | modelled, no theorem | `weightedSum`, `totalWeight`, `thresholdOf`, `votePasses` |
| P04 | Ch2 §3.7 — Tag falsification halves budget after 3+ offences | proved of the Lean model | `budget_halving_formula`, `budget_unchanged_below_cutoff`, `budget_preserves_positive` |
| P05 | Ch3 §2.1 — Contract restricts action set | no counterpart | — |
| P06 | Ch3 §2.3 — Revocation threshold above enactment threshold | no counterpart | — |
| P07 | Ch3 §2.4 — Timelock holds until its unlock cycle | no counterpart | — |
| P08 | Ch3 §3.0 — Mask composition: allowed − restricted | no counterpart | — |
| P09 | Ch4 §2.1 — Low-coherence proposal triggers integrity veto | modelled under a different encoding | `acceptable_iff_ge`, `below_threshold_rejection_leaves_state`, `rejected_action_does_not_mutate_identity` |
| P10 | Ch4 §2.5 — Tier-4 requires external multisig; lower tiers do not | modelled under a different encoding | `constitutional_requires_quorum_and_cooldown`, `constitutional_change_meets_genesis_bar`, `dynamic_requires_only_majority` |
| P11 | Ch4 §3.1 — Genesis 3-of-5: 2 sigs insufficient, 3 sigs authorises | proved of the Lean model | `two_signatures_insufficient`, `three_signatures_sufficient`, `double_signing_cannot_reach_quorum_alone`, `quorumCount_bounded_by_five` |
| P12 | Ch4 §3.6 — Deadlock breaker fires after N defaults, resets | no counterpart | — |

Reading the four coverage values:

- **proved of the Lean model** — a theorem states the prediction's property of
  the Lean model. It remains a property of the model and not of `src/nomos/`:
  everything in [Scope and limits](#scope-and-limits) applies to these rows
  unchanged. P01 and P11 are the two that section also names on the Python
  side, where a hand-written test checks the same property of `src/nomos/` —
  separately, in Python, against no Lean artefact.
- **modelled under a different encoding** — the corpus models the same
  mechanism and proves theorems about it, but under an encoding the Python
  does not share, so the theorem and the assert are not two statements of one
  claim. Both cases are numeric: a `Nat` coherence score against a 0–100
  threshold where the Python uses a `float` on 0.0–1.0, and a bar stated as a
  quorum count and a cooldown in days where the Python reads a `bool` flag.
- **modelled, no theorem** — the definitions are there and the constants
  agree, but no theorem states what the prediction asserts.
- **no counterpart** — nothing in the corpus models this at all.

The correspondence is thin in the other direction too. `IdentityBuffer.lean`
and `IdentityHashes.lean` — the sandboxed isolation buffer and the runtime
integrity hash chains — have no prediction pointing at them at all.

The table is rendered from `LEAN_COVERAGE` in
`src/nomos/prove/predictions.py`, which carries the per-row reasoning that
does not fit in a cell. `tests/test_lean_claims.py` keeps the two in step: a
name above that `gov-budget-proof/` does not declare fails there, and so does
this table disagreeing with the map it is rendered from.

## Building the proofs

Requires Lean 4 with elan (toolchain pinned in `gov-budget-proof/lean-toolchain`):

```bash
cd gov-budget-proof
lake build
```

A successful `lake build` compiles every module and its theorems; the CI
`lean-build` job runs the same command on every pull request.