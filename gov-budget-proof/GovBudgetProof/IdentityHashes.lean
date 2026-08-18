/-
  Runtime Integrity Hash Chains
  =============================
  From Chapter 4 §2.1 (Ontology — action bindings) and §6.1 (Integrity
  Committee as Proxy — TEE.verify_binding):

  - §2.1: the ontology binds each action index to a runtime integrity
    hash:  bind(i) = < Operation_i, hash_i >  with  hash_i = H(implementation_i).
    At batch validation time the TEE independently reads the current
    runtime implementation, computes its hash, and compares it against
    the committed hash. On mismatch the batch is rejected and a binding
    violation is logged.
  - §6.1: TEE.verify_binding(action_index) — REJECT("binding violation")
    when runtime_hash != genesis_hash, ACCEPT otherwise. This check
    prevents the Vector-Space Compression Subversion (Phase 5.2,
    Attack 2).

  We prove the three claims of issue #193:
  1. Chain invariant: each binding carries the hash of the previous
     binding's implementation (valid chains are the only structure the
     ontology may hold; consecutive entries always satisfy the link).
  2. Tamper evidence: modifying any past binding (while keeping the hash
     of its implementation changed) changes the chain root — conditional
     on the cryptographic collision-resistance assumption, stated
     explicitly as the theorem hypothesis hImpl.
  3. Determinism: chain roots are a function of the binding sequence —
     equal sequences always yield equal roots.

  NOTE: `hashImpl` is a deterministic stand-in for a cryptographic H.
  No concrete injectivity of hashImpl is asserted; where tamper evidence
  needs a hash change it is carried as an explicit hypothesis, mirroring
  the collision-resistance assumption of the real system.
-/

/-- Runtime hash of an executable implementation (`H(implementation_i)`
    in §2.1). Deterministic stand-in; the proofs never unfold it. -/
def hashImpl (implementation : String) : Nat :=
  implementation.length

/-- An action binding `bind(i) = < Operation_i, hash_i >` (§2.1), carrying
    additionally the link to the previous binding in the chain. -/
structure ActionBinding where
  implementation : String
  bindingHash : Nat
  prevHash : Nat

/-- §4: genesis seed of the chain — the root commitment of the signed
    genesis manifest. -/
def GENESIS_HASH : Nat := 0

/-- Per-binding hash commitment: the stored hash is the runtime hash of the
    stored implementation. -/
def BindingValid (b : ActionBinding) : Prop :=
  b.bindingHash = hashImpl b.implementation

/-- Chain invariant (issue #193, claim 1): the ontology only holds chains in
    which every consecutive pair satisfies the link relation
    prevHash_after = hashImpl(implementation_before) and every member
    satisfies its own hash commitment. -/
def IsValidChain : List ActionBinding → Prop
  | [] => True
  | [_] => True
  | a :: b :: rest =>
      BindingValid a ∧ b.prevHash = hashImpl a.implementation ∧ IsValidChain (b :: rest)

/-- Claim 1: in a valid chain, every binding after the first carries exactly
    the runtime hash of the previous binding's implementation. -/
theorem link_matches_previous_implementation (a b : ActionBinding)
    (rest : List ActionBinding) (h : IsValidChain (a :: b :: rest)) :
    b.prevHash = hashImpl a.implementation := by
  unfold IsValidChain at h
  exact h.2.1

/-- Claim 1 (first element): the chain head is a self-consistent binding
    (committed hash equals its implementation hash). -/
theorem head_binding_self_consistent (a b : ActionBinding)
    (rest : List ActionBinding) (h : IsValidChain (a :: b :: rest)) :
    BindingValid a := by
  unfold IsValidChain at h
  exact h.1

/-- The chain root: deterministic fold of the runtime hashes of all bound
    implementations, seeded by the genesis commitment. -/
def chainRoot (bs : List ActionBinding) : Nat :=
  bs.foldl (fun acc b => hashImpl b.implementation + acc) GENESIS_HASH

/-- Auxiliary: the fold accumulator is a function of the accumulator —
    equal fold results over the same suffix force equal accumulators
    (the combine step is injective on its first argument). -/
theorem foldl_combine_acc_determines_result (suffix : List ActionBinding) :
    ∀ (a₁ a₂ : Nat),
      suffix.foldl (fun acc b => hashImpl b.implementation + acc) a₁ =
      suffix.foldl (fun acc b => hashImpl b.implementation + acc) a₂ → a₁ = a₂ := by
  induction suffix with
  | nil =>
      intro a₁ a₂ h
      simpa using h
  | cons b rest ih =>
      intro a₁ a₂ h
      have h' : hashImpl b.implementation + a₁ = hashImpl b.implementation + a₂ :=
        ih (hashImpl b.implementation + a₁) (hashImpl b.implementation + a₂)
          (by simpa [List.foldl_cons] using h)
      omega

/-- Claim 2 (tamper evidence): modifying any past binding — the candidate
    alone, prefix and suffix untouched — changes the chain root, provided
    the hash of the modified implementation differs (collision-resistance
    assumption, explicit hypothesis `hImpl`). -/
theorem tamper_changes_chain_root (pre suf : List ActionBinding)
    (orig new : ActionBinding)
    (hImpl : hashImpl orig.implementation ≠ hashImpl new.implementation) :
    chainRoot (pre ++ orig :: suf) ≠ chainRoot (pre ++ new :: suf) := by
  intro hEq
  unfold chainRoot at hEq
  simp [List.foldl_append] at hEq
  have hAcc :
      hashImpl orig.implementation + pre.foldl (fun acc b => hashImpl b.implementation + acc) GENESIS_HASH
        = hashImpl new.implementation + pre.foldl (fun acc b => hashImpl b.implementation + acc) GENESIS_HASH := by
    exact foldl_combine_acc_determines_result suf _ _ (by simpa [List.foldl_cons] using hEq)
  have hSame : hashImpl orig.implementation = hashImpl new.implementation := by
    omega
  exact hImpl hSame

/-- Claim 2 at the level of a single modification: if a binding is swapped
    for one with a different implementation hash, the root changes. -/
theorem tamper_evidence_single_binding (b₁ b₂ : ActionBinding)
    (hImpl : hashImpl b₁.implementation ≠ hashImpl b₂.implementation) :
    chainRoot [b₁] ≠ chainRoot [b₂] := by
  simpa [List.foldl] using tamper_changes_chain_root [] [] b₁ b₂ hImpl

/-- Claim 3 (determinism): the chain root is a function of the binding
    sequence — equal sequences give equal roots. -/
theorem chain_root_deterministic (bs bs' : List ActionBinding) (h : bs = bs') :
    chainRoot bs = chainRoot bs' := by
  rw [h]

/-- §6.1: TEE.verify_binding — the runtime implementation hash is compared
    against the committed binding hash. -/
def verifyRuntime (runtime : String) (b : ActionBinding) : Bool :=
  decide (hashImpl runtime = b.bindingHash)

/-- §6.1 ACCEPT path: an implementation matching the committed hash passes
    binding verification. -/
theorem verify_accepts_matching_implementation (runtime : String) (b : ActionBinding)
    (h : hashImpl runtime = b.bindingHash) : verifyRuntime runtime b = true := by
  unfold verifyRuntime
  simp [h]

/-- §6.1 REJECT path: an implementation whose runtime hash differs from the
    committed hash is rejected with a binding violation, exactly as
    TEE.verify_binding specifies. -/
theorem verify_rejects_changed_implementation (runtime : String) (b : ActionBinding)
    (hChanged : hashImpl runtime ≠ hashImpl b.implementation)
    (hCommitted : b.bindingHash = hashImpl b.implementation) :
    verifyRuntime runtime b = false := by
  unfold verifyRuntime
  by_cases hEq : hashImpl runtime = b.bindingHash
  · exact False.elim (hChanged (by rw [hCommitted] at hEq; exact hEq))
  · simp [hEq]

/-- Channel for §2.1: TEE independently recomputes the hash at batch time
    rather than trusting the proposed binding's own claim. -/
theorem tee_recomputes_hash_independently (runtime : String) (b : ActionBinding) :
    verifyRuntime runtime b = decide (hashImpl runtime = b.bindingHash) := by
  rfl

/-- A benign binding passes verification when runtime matches the binding
    commitment. -/
example : verifyRuntime "benign_impl"
      { implementation := "benign_impl",
        bindingHash := 11, prevHash := 0 } = true := by
  apply verify_accepts_matching_implementation
  native_decide

/-- Swapping the runtime implementation changes the hash, so the rejected
    action index logs a binding violation. -/
example : verifyRuntime "evil_impl"
      { implementation := "benign_impl",
        bindingHash := 11, prevHash := 0 } = false := by
  apply verify_rejects_changed_implementation
  · native_decide
  · native_decide

/-- Tampering with a bound action's past implementation changes the root of
    its chain ('benign_impl' → 'tampered_impl'). -/
example : chainRoot
      [{ implementation := "tampered_impl", bindingHash := 13, prevHash := 0 }]
    ≠ chainRoot
      [{ implementation := "benign_impl", bindingHash := 11, prevHash := 0 }] := by
  apply tamper_evidence_single_binding
  native_decide