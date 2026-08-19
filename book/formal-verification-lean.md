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
| `Basic.lean` | Core definitions (budget, thresholds) | `gov-budget-proof/GovBudgetProof/` |
| `BudgetEnforcement.lean` | Budget/threshold enforcement invariants (issues #43/#44) | `gov-budget-proof/GovBudgetProof/` |
| `VoteAndFalsification.lean` | Vote falsification impossibility | `gov-budget-proof/GovBudgetProof/` |
| `IdentityTiers.lean` | Tier mutability rules — [Chapter 4, Sec 3](/book/chapter-04/04-identity-layer) | `gov-budget-proof/GovBudgetProof/` |
| `IdentityGenesis.lean` | Genesis 3-of-5 multisig bootstrapping — [Chapter 4, Sec 4](/book/chapter-04/04-identity-layer) | `gov-budget-proof/GovBudgetProof/` |
| `IdentityBuffer.lean` | Sandboxed isolation buffer protocol — [Chapter 4, Sec 5.2](/book/chapter-04/04-identity-layer) | `gov-budget-proof/GovBudgetProof/` |
| `IdentityHashes.lean` | Runtime integrity hash chains over an uninterpreted hash; the root separates two bindings exactly as far as it separates their digests, and the digest packing is proved to collide, so tamper evidence is conditional on the two records having different digests — a hypothesis stronger than collision-resistance of the hash, not implied by it — [Chapter 4, Sec 2.1 and 6.1](/book/chapter-04/04-identity-layer) | `gov-budget-proof/GovBudgetProof/` |
| `IdentityCoherence.lean` | Coherence threshold guard; below-threshold actions are rejected without mutating identity state — [Chapter 4, Sec 6.1](/book/chapter-04/04-identity-layer) | `gov-budget-proof/GovBudgetProof/` |

## Building the proofs

Requires Lean 4 with elan (toolchain pinned in `gov-budget-proof/lean-toolchain`):

```bash
cd gov-budget-proof
lake build
```

A successful `lake build` compiles every module and its theorems; the CI
`lean-build` job runs the same command on every pull request.