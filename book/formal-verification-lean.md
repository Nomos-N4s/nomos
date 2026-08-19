---
title: "Lean 4 Formal Verification"
description: "Inventory of the Lean 4 proof modules in gov-budget-proof: the machine-checked counterpart to the Identity Layer chapter (Chapter 4)."
---

# Lean 4 Formal Verification

The formal framework is backed by machine-checked proofs written in [Lean 4](https://lean-lang.org/).
The proof library lives in `gov-budget-proof/` and is enforced in CI: every pull
request runs the `lean-build` job (`lake build`), so a broken proof blocks a merge.

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

## Building the proofs

Requires Lean 4 with elan (toolchain pinned in `gov-budget-proof/lean-toolchain`):

```bash
cd gov-budget-proof
lake build
```

A successful `lake build` compiles every module and its theorems; the CI
`lean-build` job runs the same command on every pull request.