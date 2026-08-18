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

  NOTE: `hashImpl` is UNINTERPRETED (issue #299). It is a section variable
  of type `String -> Nat`, not a definition, so every declaration below is
  universally quantified over the hash and no proof, example or `decide`
  can appeal to a particular hash function. Tamper evidence therefore has
  to carry the hash change as an explicit hypothesis, mirroring the
  collision-resistance assumption of the real system.
-/

/-- An action binding `bind(i) = < Operation_i, hash_i >` (§2.1), carrying
    additionally the link to the previous binding in the chain. -/
structure ActionBinding where
  implementation : String
  bindingHash : Nat
  prevHash : Nat

/-- §4: genesis seed of the chain — the root commitment of the signed
    genesis manifest. -/
def GENESIS_HASH : Nat := 0

/-- Position multiplier of the chain fold. Any value greater than one makes
    the fold positional instead of commutative, which is what stops equal
    contributions in different positions from cancelling out. -/
def MIX : Nat := 31

/-- The multiplier is non-zero, so multiplying by it is injective — the only
    arithmetic fact about `MIX` the fold lemmas need. -/
theorem MIX_pos : 0 < MIX := by decide

section RuntimeHash

/- Runtime hash of an executable implementation (`H(implementation_i)` in
   §2.1), left completely uninterpreted: a section variable rather than a
   definition, so every declaration in this section is quantified over it. -/
variable (hashImpl : String → Nat)

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
      BindingValid hashImpl a ∧ b.prevHash = hashImpl a.implementation ∧
        IsValidChain (b :: rest)

/-- Claim 1: in a valid chain, every binding after the first carries exactly
    the runtime hash of the previous binding's implementation. -/
theorem link_matches_previous_implementation (a b : ActionBinding)
    (rest : List ActionBinding) (h : IsValidChain hashImpl (a :: b :: rest)) :
    b.prevHash = hashImpl a.implementation := by
  unfold IsValidChain at h
  exact h.2.1

/-- Claim 1 (first element): the chain head is a self-consistent binding
    (committed hash equals its implementation hash). -/
theorem head_binding_self_consistent (a b : ActionBinding)
    (rest : List ActionBinding) (h : IsValidChain hashImpl (a :: b :: rest)) :
    BindingValid hashImpl a := by
  unfold IsValidChain at h
  exact h.1

/-- The leaf digest of a single binding: a positional encoding of the whole
    record — the runtime hash of the implementation, the hash the record
    commits to, and the link to its predecessor. All three fields reach the
    chain root through this digest, so the root is sensitive to a swapped
    implementation, to a forged commitment and to a re-pointed link alike. -/
def bindingDigest (b : ActionBinding) : Nat :=
  MIX * MIX * hashImpl b.implementation + MIX * b.bindingHash + b.prevHash

/-- The chain root: a positional (Horner) fold of the per-binding digests,
    seeded by the genesis commitment. The step `acc ↦ MIX * acc + digest` is
    not commutative, so — unlike the plain sum this replaced — the root
    distinguishes orderings and sees every field of every record. -/
def chainRoot (bs : List ActionBinding) : Nat :=
  bs.foldl (fun acc b => MIX * acc + bindingDigest hashImpl b) GENESIS_HASH

/-- The implementation reaches the digest: two bindings that commit the same
    hash and the same link, but whose implementations hash apart, have
    different digests. -/
theorem bindingDigest_ne_of_impl_hash_ne (b b' : ActionBinding)
    (hCommit : b.bindingHash = b'.bindingHash) (hLink : b.prevHash = b'.prevHash)
    (hImpl : hashImpl b.implementation ≠ hashImpl b'.implementation) :
    bindingDigest hashImpl b ≠ bindingDigest hashImpl b' := by
  simp only [bindingDigest, MIX, hCommit, hLink]
  omega

/-- The link reaches the digest: re-pointing `prevHash` and nothing else
    changes the digest. -/
theorem bindingDigest_ne_of_prevHash_ne (b b' : ActionBinding)
    (hImpl : b.implementation = b'.implementation)
    (hCommit : b.bindingHash = b'.bindingHash) (hLink : b.prevHash ≠ b'.prevHash) :
    bindingDigest hashImpl b ≠ bindingDigest hashImpl b' := by
  simp only [bindingDigest, MIX, hImpl, hCommit]
  omega

/-- The commitment reaches the digest: forging `bindingHash` and nothing else
    changes the digest. This is what connects `BindingValid` to the root —
    under the old `+`-fold the committed hash never entered it. -/
theorem bindingDigest_ne_of_bindingHash_ne (b b' : ActionBinding)
    (hImpl : b.implementation = b'.implementation)
    (hLink : b.prevHash = b'.prevHash) (hCommit : b.bindingHash ≠ b'.bindingHash) :
    bindingDigest hashImpl b ≠ bindingDigest hashImpl b' := by
  simp only [bindingDigest, MIX, hImpl, hLink]
  omega

/-- Two self-consistent bindings (each satisfying `BindingValid`) that share a
    link but whose implementations hash apart have different digests. The
    commitments need not be assumed equal here: `BindingValid` ties each one
    to its own implementation hash. -/
theorem bindingDigest_ne_of_valid_commitments_and_hash_ne (b b' : ActionBinding)
    (hb : BindingValid hashImpl b) (hb' : BindingValid hashImpl b')
    (hLink : b.prevHash = b'.prevHash)
    (hImpl : hashImpl b.implementation ≠ hashImpl b'.implementation) :
    bindingDigest hashImpl b ≠ bindingDigest hashImpl b' := by
  unfold BindingValid at hb hb'
  simp only [bindingDigest, MIX, hb, hb', hLink]
  omega

/-- Auxiliary: the fold accumulator is determined by the fold result — equal
    roots over the same suffix force equal accumulators, because the combine
    step `acc ↦ MIX * acc + d` is injective in `acc` (`MIX ≠ 0`). -/
theorem foldl_mix_acc_determines_result (suffix : List ActionBinding) :
    ∀ a₁ a₂ : Nat,
      suffix.foldl (fun acc b => MIX * acc + bindingDigest hashImpl b) a₁ =
      suffix.foldl (fun acc b => MIX * acc + bindingDigest hashImpl b) a₂ → a₁ = a₂ := by
  induction suffix with
  | nil =>
      intro a₁ a₂ h
      simpa using h
  | cons b rest ih =>
      intro a₁ a₂ h
      have h' : MIX * a₁ + bindingDigest hashImpl b = MIX * a₂ + bindingDigest hashImpl b :=
        ih _ _ (by simpa [List.foldl_cons] using h)
      have hMul : MIX * a₁ = MIX * a₂ := Nat.add_right_cancel h'
      exact Nat.eq_of_mul_eq_mul_left MIX_pos hMul

/-- Claim 2 (tamper evidence), general form: replacing one binding — prefix
    and suffix untouched — changes the chain root, **provided the two
    bindings have different digests**. That hypothesis is the
    collision-resistance assumption of the real system. It cannot be
    discharged inside this file, because `hashImpl` is uninterpreted, which
    is why it is named in the theorem's name rather than left implied. -/
theorem tamper_changes_chain_root_of_distinct_digests (pre suf : List ActionBinding)
    (orig new : ActionBinding)
    (hDigest : bindingDigest hashImpl orig ≠ bindingDigest hashImpl new) :
    chainRoot hashImpl (pre ++ orig :: suf) ≠ chainRoot hashImpl (pre ++ new :: suf) := by
  intro hEq
  unfold chainRoot at hEq
  simp only [List.foldl_append, List.foldl_cons] at hEq
  have hAcc := foldl_mix_acc_determines_result hashImpl suf _ _ hEq
  exact hDigest (Nat.add_left_cancel hAcc)

/-- Claim 2 in the §2.1 shape: an implementation swap that leaves the
    record's committed hash and link in place, and whose two
    implementations hash apart, changes the root. -/
theorem tamper_changes_chain_root_of_hash_change (pre suf : List ActionBinding)
    (orig new : ActionBinding)
    (hCommit : orig.bindingHash = new.bindingHash)
    (hLink : orig.prevHash = new.prevHash)
    (hImpl : hashImpl orig.implementation ≠ hashImpl new.implementation) :
    chainRoot hashImpl (pre ++ orig :: suf) ≠ chainRoot hashImpl (pre ++ new :: suf) :=
  tamper_changes_chain_root_of_distinct_digests hashImpl pre suf orig new
    (bindingDigest_ne_of_impl_hash_ne hashImpl orig new hCommit hLink hImpl)

/-- Claim 2 at the level of a single modification: swapping the one binding
    of a one-element chain for a binding with a different digest changes the
    root. -/
theorem tamper_evidence_single_binding_of_distinct_digests (b₁ b₂ : ActionBinding)
    (hDigest : bindingDigest hashImpl b₁ ≠ bindingDigest hashImpl b₂) :
    chainRoot hashImpl [b₁] ≠ chainRoot hashImpl [b₂] :=
  tamper_changes_chain_root_of_distinct_digests hashImpl [] [] b₁ b₂ hDigest

/-- Order sensitivity, exactly: swapping two bindings leaves the root
    unchanged **iff** their digests coincide. Unconditional, and the precise
    replacement for the commutativity of the old `+`-fold, under which every
    reordering was invisible. -/
theorem chain_root_swap_eq_iff_digest_eq (a b : ActionBinding) :
    chainRoot hashImpl [a, b] = chainRoot hashImpl [b, a] ↔
      bindingDigest hashImpl a = bindingDigest hashImpl b := by
  unfold chainRoot
  simp only [List.foldl_cons, List.foldl_nil, GENESIS_HASH, MIX]
  constructor
  · intro h
    omega
  · intro h
    omega

/-- Reordering two bindings with distinct digests is visible in the root. -/
theorem chain_root_not_commutative_of_distinct_digests (a b : ActionBinding)
    (hDigest : bindingDigest hashImpl a ≠ bindingDigest hashImpl b) :
    chainRoot hashImpl [a, b] ≠ chainRoot hashImpl [b, a] := by
  intro hEq
  exact hDigest ((chain_root_swap_eq_iff_digest_eq hashImpl a b).mp hEq)

/-- `chainRoot [a, b] = chainRoot [b, a]` for **distinct** `a` and `b` — the
    property the old commutative root had — now fails, but only under the
    hypothesis this theorem is named for: that the digest is collision-free,
    i.e. that distinct records get distinct digests. With `hashImpl`
    uninterpreted the hypothesis cannot be discharged inside the file, and
    `chain_root_commutes_under_a_degenerate_hash` below shows it cannot
    simply be dropped either. -/
theorem chain_root_not_commutative_of_collision_free_digest
    (hCollisionFree : ∀ x y : ActionBinding,
      bindingDigest hashImpl x = bindingDigest hashImpl y → x = y)
    (a b : ActionBinding) (hne : a ≠ b) :
    chainRoot hashImpl [a, b] ≠ chainRoot hashImpl [b, a] :=
  chain_root_not_commutative_of_distinct_digests hashImpl a b
    (fun hEq => hne (hCollisionFree a b hEq))

/-- Claim 3 (determinism): the chain root is a function of the binding
    sequence — equal sequences give equal roots. -/
theorem chain_root_deterministic (bs bs' : List ActionBinding) (h : bs = bs') :
    chainRoot hashImpl bs = chainRoot hashImpl bs' := by
  rw [h]

/-- §6.1: TEE.verify_binding — the runtime implementation hash is compared
    against the committed binding hash. -/
def verifyRuntime (runtime : String) (b : ActionBinding) : Bool :=
  decide (hashImpl runtime = b.bindingHash)

/-- §6.1 ACCEPT path: an implementation matching the committed hash passes
    binding verification. -/
theorem verify_accepts_matching_implementation (runtime : String) (b : ActionBinding)
    (h : hashImpl runtime = b.bindingHash) : verifyRuntime hashImpl runtime b = true := by
  unfold verifyRuntime
  simp [h]

/-- §6.1 REJECT path: an implementation whose runtime hash differs from the
    committed hash is rejected with a binding violation, exactly as
    TEE.verify_binding specifies. -/
theorem verify_rejects_changed_implementation (runtime : String) (b : ActionBinding)
    (hChanged : hashImpl runtime ≠ hashImpl b.implementation)
    (hCommitted : b.bindingHash = hashImpl b.implementation) :
    verifyRuntime hashImpl runtime b = false := by
  unfold verifyRuntime
  by_cases hEq : hashImpl runtime = b.bindingHash
  · exact False.elim (hChanged (by rw [hCommitted] at hEq; exact hEq))
  · simp [hEq]

/-- Channel for §2.1: TEE independently recomputes the hash at batch time
    rather than trusting the proposed binding's own claim. -/
theorem tee_recomputes_hash_independently (runtime : String) (b : ActionBinding) :
    verifyRuntime hashImpl runtime b = decide (hashImpl runtime = b.bindingHash) := by
  rfl

/-- A benign binding passes verification when the runtime implementation is
    the one it commits to. The commitment enters as a `BindingValid`
    hypothesis, so the example asserts the relation between the literal `11`
    and `hashImpl "benign_impl"` instead of evaluating it. -/
example (hBenign : BindingValid hashImpl
      { implementation := "benign_impl", bindingHash := 11, prevHash := 0 }) :
    verifyRuntime hashImpl "benign_impl"
      { implementation := "benign_impl", bindingHash := 11, prevHash := 0 } = true :=
  verify_accepts_matching_implementation hashImpl _ _ hBenign.symm

/-- Swapping the runtime implementation for one that hashes differently makes
    the rejected action index log a binding violation. -/
example (hBenign : BindingValid hashImpl
      { implementation := "benign_impl", bindingHash := 11, prevHash := 0 })
    (hSwapped : hashImpl "evil_impl" ≠ hashImpl "benign_impl") :
    verifyRuntime hashImpl "evil_impl"
      { implementation := "benign_impl", bindingHash := 11, prevHash := 0 } = false :=
  verify_rejects_changed_implementation hashImpl _ _ hSwapped hBenign

/-- Tampering with a bound action's past implementation changes the root of
    its chain ('benign_impl' → 'tampered_impl'). Both records now carry their
    own `BindingValid` commitment — `13` and `11`, the lengths the documented
    stand-in gives — and the proof consumes both: it is the two commitments
    being different naturals that supplies the hash difference, so neither
    literal is decorative. -/
example
    (hTampered : BindingValid hashImpl
      { implementation := "tampered_impl", bindingHash := 13, prevHash := 0 })
    (hBenign : BindingValid hashImpl
      { implementation := "benign_impl", bindingHash := 11, prevHash := 0 }) :
    chainRoot hashImpl
        [{ implementation := "tampered_impl", bindingHash := 13, prevHash := 0 }]
      ≠ chainRoot hashImpl
        [{ implementation := "benign_impl", bindingHash := 11, prevHash := 0 }] := by
  refine tamper_evidence_single_binding_of_distinct_digests hashImpl _ _
    (bindingDigest_ne_of_valid_commitments_and_hash_ne hashImpl _ _ hTampered hBenign rfl ?_)
  unfold BindingValid at hTampered hBenign
  dsimp only at hTampered hBenign ⊢
  omega

end RuntimeHash

/-- Why every tamper- and order-sensitivity theorem above carries a
    hypothesis. An uninterpreted `hashImpl` may be constant, and then two
    bindings that differ only in their implementation have the same digest
    and the swap is invisible in the root. So the unconditional reading —
    "distinct bindings, therefore distinct roots" — is refutable, not merely
    unproven, and no honest theorem in this file may state it. -/
theorem chain_root_commutes_under_a_degenerate_hash :
    ∃ (hashImpl : String → Nat) (a b : ActionBinding),
      a ≠ b ∧ chainRoot hashImpl [a, b] = chainRoot hashImpl [b, a] := by
  refine ⟨fun _ => 0,
    { implementation := "benign_impl", bindingHash := 0, prevHash := 0 },
    { implementation := "rm_rf_slash", bindingHash := 0, prevHash := 0 }, ?_, rfl⟩
  intro h
  injection h with hImpl _ _
  exact absurd hImpl (by decide)
