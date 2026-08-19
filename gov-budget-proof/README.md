# gov-budget-proof

The Lean 4 proof library for Nomos: seven proof modules plus the
`GovBudgetProof.lean` manifest, 102 theorems, zero `sorry`, zero axioms
declared by the corpus, and no dependencies at all (`lakefile.toml` declares
no `require`; the resolved `lake-manifest.json` is build output and is
gitignored). The toolchain is pinned in `lean-toolchain`
(`leanprover/lean4:v4.32.1`). Every pull request runs `lake build` in the
`lean-build` CI job, so a broken proof blocks a merge.

## Scope

**These are properties of Lean models of the protocol. They are not properties
of the Python in `src/nomos/`.** Nothing extracts the models from the
implementation and no refinement argument connects the two, so a green build
means the proofs compile, not that the implementation is verified (#297).

The full inventory, and the list of links a reader might assume exist but do
not, is in
[`book/formal-verification-lean.md`](../book/formal-verification-lean.md#scope-and-limits);
the argument is in
[`book/chapter-05/05-related-work.md`](../book/chapter-05/05-related-work.md#7-where-to-attack-this-chapter)
§7.

## Build

```bash
cd gov-budget-proof
lake build                  # Build completed successfully (20 jobs).
lake exe gov-budget-proof   # prints what the build checked, and what it did not
```
