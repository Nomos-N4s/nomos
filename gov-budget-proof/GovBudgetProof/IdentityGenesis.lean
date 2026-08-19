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

/-- The TEE rejects a two-signature manifest. -/
theorem tee_rejects_two : teeVerifies [GenesisKey.k1, GenesisKey.k2] = false :=
  decide_eq_false two_signatures_insufficient

/-- The TEE accepts a three-signature manifest. -/
theorem tee_accepts_three : teeVerifies [GenesisKey.k1, GenesisKey.k2, GenesisKey.k3] = true :=
  decide_eq_true three_signatures_sufficient

/-- The TEE ignores duplicates: k1 signing twice still counts once. -/
theorem tee_rejects_duplicate_alone : teeVerifies [GenesisKey.k1, GenesisKey.k1] = false := by
  native_decide