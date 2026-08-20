import GovBudgetProof

/-- Report what `lake build` established, in terms that hold.

Building this executable elaborates the whole `GovBudgetProof` library first,
so reaching `main` means every declaration in it was accepted. Nothing is
computed here: the lines below report that build.

What was checked are properties of the Lean models in `GovBudgetProof/`, not
properties of the Python in `src/nomos/`. Nothing extracts these models from
the implementation and no refinement argument connects the two (#297), so a
successful build says nothing about `speaker.py`. The calibrated statement is
in `book/formal-verification-lean.md` under "Scope and limits".
-/
def main : IO Unit := do
  IO.println "gov-budget-proof: the Lean proof library built."
  IO.println ""
  IO.println "Machine-checked models, by module:"
  IO.println "  - BudgetEnforcement    budget/threshold enforcement (κ₂)"
  IO.println "  - VoteAndFalsification vote resolution, falsification counting, budget halving"
  IO.println "  - IdentityTiers        tier mutability and the constitutional modification bar"
  IO.println "  - IdentityGenesis      3-of-5 multisig genesis bootstrapping"
  IO.println "  - IdentityBuffer       sandboxed isolation buffer protocol"
  IO.println "  - IdentityHashes       runtime integrity hash chains"
  IO.println "  - IdentityCoherence    coherence threshold guard"
  IO.println ""
  IO.println "Scope: these are properties of the models above, not of src/nomos/."
  IO.println "Nothing extracts the models from the Python implementation and no"
  IO.println "refinement argument connects the two, so this says nothing about"
  IO.println "speaker.py. See book/formal-verification-lean.md, Scope and limits."
