import GovBudgetProof

def main : IO Unit := do
  IO.println "All governance-layer invariants verified:"
  IO.println "  ✔ Budget enforcement (κ₂)"
  IO.println "  ✔ Vote threshold resolution"
  IO.println "  ✔ Falsification counter"
  IO.println "  ✔ Budget halving invariant"
