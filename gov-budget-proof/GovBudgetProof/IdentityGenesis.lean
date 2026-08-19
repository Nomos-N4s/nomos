/-
  Genesis Bootstrapping: 3-of-5 Multisig
  =======================================
  From Chapter 4 (§4 Genesis Bootstrapping):
  - §4.1: the genesis manifest G is signed by the external multisig before
    the TEE is initialized with it.
  - §4.2 Phase 1: five key holders are selected and each independently signs
    the manifest; the TEE verifies ≥ 3 signatures before initialization.
  - §4.4: the 3-of-5 threshold means compromising any two entities is
    insufficient; social engineering would require three entities.

  We prove:
  - with exactly five genesis keys, two distinct signatures are insufficient:
    the genesis update is rejected
  - three distinct signatures succeed
  - signatures are idempotent: double-signing never counts twice, so
    duplicates can never inflate a signature list to quorum

  AXIOM DISCIPLINE (issue #300). The three `teeVerifies` theorems at the end
  of this file used to close by `native_decide`. On the pinned toolchain
  (`lean-toolchain` = leanprover/lean4:v4.32.1) that tactic does not run in
  the kernel: it asserts the compiled evaluation as a fresh opaque axiom,
  `<theorem>._native.native_decide.ax_1_1`, one per declaration. `teeVerifies`
  is by definition the `decide` of `genesisAccepted`, so each Bool theorem is
  now a term proof off the `Prop` sibling above it — `decide_eq_false` or
  `decide_eq_true` applied to a lemma the kernel already checked — and
  `#print axioms` reports "does not depend on any axioms" for all six. Do not
  reintroduce `native_decide` here: the signature lists are tiny and plain
  `decide` is a kernel computation.

  That rule is enforced by two checks in `tests/test_lean_claims.py`, not by
  grepping this tree. `test_no_proof_closes_by_a_native_decision` scans the
  source for the three spellings that mint such an axiom on this toolchain —
  `native_decide`, `decide +native`, `decide (config := { native := true })`.
  `test_lean_corpus_declares_no_axioms_of_its_own` reads the elaborated
  environment and fails if any GovBudgetProof module declares an axiom at all,
  however the tactic is spelled. A bare `grep -rn native_decide
  gov-budget-proof/` is not that check and does not come back empty: it still
  matches this note, and the hash note at `IdentityHashes.lean:38` that
  predates issue #300. Both are prose telling editors what not to do, and the
  guards blank comments out before scanning so prose cannot trip them.

  Three declarations in this file are not axiom-free, and none of them is a
  TEE theorem: `any_three_distinct_signatures_sufficient` and
  `double_signing_never_increases_quorum` depend on `propext` and `Quot.sound`
  through `simp`, and `quorumCount_bounded_by_five` on `propext` through the
  core lemma `List.length_filter_le`. Those are Lean's standard structural
  axioms; no declaration here depends on `Classical.choice`.
-/

/-- The five genesis key holders (§4.2 Phase 1 step 3). -/
inductive GenesisKey : Type
  | k1
  | k2
  | k3
  | k4
  | k5
  deriving DecidableEq

/-- The exact genesis key set: five keys, no more, no less. -/
def genesisKeys : List GenesisKey :=
  [GenesisKey.k1, GenesisKey.k2, GenesisKey.k3, GenesisKey.k4, GenesisKey.k5]

/-- The 3-of-5 quorum threshold (§4.2 Phase 1 step 6). -/
def GENESIS_QUORUM : Nat := 3

/-- Whether a key holder has signed: their key occurs in the signature list. -/
def hasSigned (key : GenesisKey) (signatures : List GenesisKey) : Bool :=
  signatures.any (fun k => decide (k = key))

/-- The number of distinct key holders among the five that have signed.
    Duplicates never count twice: each key is counted at most once. -/
def quorumCount (signatures : List GenesisKey) : Nat :=
  (genesisKeys.filter (fun key => hasSigned key signatures)).length

/-- The genesis manifest is accepted iff the 3-of-5 quorum is met
    (§4.2 Phase 1 step 6: "TEE verifies >= 3 signatures"). -/
def genesisAccepted (signatures : List GenesisKey) : Prop :=
  GENESIS_QUORUM ≤ quorumCount signatures

/-- §4.4: with exactly five genesis keys, two signatures are insufficient —
    the genesis update is rejected. -/
theorem two_signatures_insufficient :
    ¬ genesisAccepted [GenesisKey.k1, GenesisKey.k2] := by
  unfold genesisAccepted quorumCount hasSigned
  decide

/-- §4.4: any two signatures (even from distinct key holders) are insufficient. -/
theorem any_two_signatures_insufficient (a b : GenesisKey) :
    ¬ genesisAccepted [a, b] := by
  unfold genesisAccepted quorumCount hasSigned
  cases a <;> cases b <;> decide

/-- §4.4: a single signature is trivially insufficient. -/
theorem one_signature_insufficient (a : GenesisKey) :
    ¬ genesisAccepted [a] := by
  unfold genesisAccepted quorumCount hasSigned
  cases a <;> decide

/-- §4.4: no signatures at all are insufficient. -/
theorem no_signatures_insufficient :
    ¬ genesisAccepted [] := by
  unfold genesisAccepted quorumCount hasSigned
  decide

/-- §4.1–4.2: three distinct key holders bootstrap the manifest — the
    genesis update succeeds. -/
theorem three_signatures_sufficient :
    genesisAccepted [GenesisKey.k1, GenesisKey.k2, GenesisKey.k3] := by
  unfold genesisAccepted quorumCount hasSigned
  decide

/-- §4.2: any three pairwise-distinct key holders bootstrap the manifest. -/
theorem any_three_distinct_signatures_sufficient (a b c : GenesisKey)
    (hab : a ≠ b) (hac : a ≠ c) (hbc : b ≠ c) :
    genesisAccepted [a, b, c] := by
  unfold genesisAccepted quorumCount hasSigned
  cases a <;> cases b <;> cases c <;> simp at hab hac hbc ⊢ <;> decide

/-- §4.2: even four or five signatures succeed (quorum is a floor, not a cap). -/
theorem four_signatures_sufficient :
    genesisAccepted [GenesisKey.k1, GenesisKey.k2, GenesisKey.k3, GenesisKey.k4] := by
  unfold genesisAccepted quorumCount hasSigned
  decide

/-- §4.2: double-signing counts once — a single key holder cannot inflate
    the quorum by signing repeatedly. -/
theorem duplicate_signature_counts_once :
    quorumCount [GenesisKey.k1, GenesisKey.k1] = 1 := by
  unfold quorumCount hasSigned
  decide

/-- §4.2: appending a duplicate signature never increases the quorum. -/
theorem double_signing_never_increases_quorum (signatures : List GenesisKey) (key : GenesisKey) :
    quorumCount (signatures ++ [key, key]) = quorumCount (signatures ++ [key]) := by
  unfold quorumCount hasSigned
  congr 1
  apply List.filter_congr
  intro k hk
  by_cases h : k = key
  · simp [h, List.any_append, List.any_cons, List.any_nil]
  · simp [h, List.any_append, List.any_cons, List.any_nil]

/-- §4.2: duplicates cannot smuggle two signatures past the quorum check. -/
theorem double_signing_cannot_reach_quorum_alone (a : GenesisKey) :
    ¬ genesisAccepted [a, a] := by
  unfold genesisAccepted quorumCount hasSigned
  cases a <;> decide

/-- §4.2: repeated duplicate signing across all five keys reaches exactly
    five, never more — the quorum count is bounded by the key set. -/
theorem quorumCount_bounded_by_five (signatures : List GenesisKey) :
    quorumCount signatures ≤ 5 := by
  unfold quorumCount
  have hlen : (genesisKeys.filter (fun key => hasSigned key signatures)).length ≤ genesisKeys.length :=
    List.length_filter_le (fun key => hasSigned key signatures) genesisKeys
  rw [show genesisKeys.length = 5 by unfold genesisKeys; rfl] at hlen
  exact hlen

/-- TEE-side genesis verification (§4.2 Phase 1 step 6): exactly the quorum
    check, returned as a Bool. -/
def teeVerifies (signatures : List GenesisKey) : Bool :=
  GENESIS_QUORUM ≤ quorumCount signatures

/-- The TEE rejects the two-signature manifest `[k1, k2]`. This is the Bool
    image of `two_signatures_insufficient` at that one list, not a claim about
    every pair; the quantified statement is `any_two_signatures_insufficient`,
    which is a Prop and has no Bool counterpart here. -/
theorem tee_rejects_two : teeVerifies [GenesisKey.k1, GenesisKey.k2] = false :=
  decide_eq_false two_signatures_insufficient

/-- The TEE accepts the three-signature manifest `[k1, k2, k3]`. This is the
    Bool image of `three_signatures_sufficient` at that one list, not a claim
    about every triple; the quantified statement is
    `any_three_distinct_signatures_sufficient`. -/
theorem tee_accepts_three : teeVerifies [GenesisKey.k1, GenesisKey.k2, GenesisKey.k3] = true :=
  decide_eq_true three_signatures_sufficient

/-- The TEE rejects a manifest that k1 signed twice and nobody else signed.
    It says that duplicate list fails the quorum check — not that the count is
    exactly one, which is `duplicate_signature_counts_once`, nor that appending
    a duplicate never helps, which is `double_signing_never_increases_quorum`. -/
theorem tee_rejects_duplicate_alone : teeVerifies [GenesisKey.k1, GenesisKey.k1] = false :=
  decide_eq_false (double_signing_cannot_reach_quorum_alone GenesisKey.k1)