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
     ontology may hold; consecutive entries always satisfy the link), and
     re-pointing a link is visible in the chain root.
  2. Tamper evidence: replacing a binding changes the chain root —
     conditional on the replacement changing that binding's DIGEST, carried
     as an explicit hypothesis named in every theorem that needs it. That
     hypothesis is about the two records' digests; it is a different claim
     from collision-resistance of the hash, and collision-resistance does
     not deliver it —
     `chain_root_swap_invisible_for_two_valid_bindings` is the
     counterexample.
  3. Determinism: chain roots are a function of the binding sequence —
     equal sequences always yield equal roots.

  THE HASH IS UNINTERPRETED (issue #299). `hashImpl` is a section variable
  of type `String -> Nat`, not a definition, so every declaration inside
  section `RuntimeHash` is universally quantified over the hash: nothing in
  the section can unfold it, evaluate it, or discharge a goal with
  `decide`/`native_decide` on a concrete digest, and in particular no proof
  there may appeal to `String.length`.

  One declaration sits after `end RuntimeHash` and is the deliberate
  exception: `chain_root_commutes_under_a_degenerate_hash` quantifies over
  hashes existentially, so it has to exhibit one — the constant `fun _ => 0`
  — and its proof does evaluate that hash with `rfl` and `decide`. The
  exception is safe in one direction only: a concrete hash may witness a
  limitation, never a guarantee, and this is the sole place in the file
  where a concrete hash appears at all.

  Two consequences a reader must keep in mind:

  * Every tamper- and order-sensitivity result is CONDITIONAL, and the
    condition is that the two records have distinct DIGESTS — not that the
    hash is well behaved. Two limitations follow, and no docstring below may
    soften either. First, "the bindings differ, therefore the roots differ"
    is refutable, for EVERY `hashImpl` and not merely for a degenerate one,
    because the digest packing itself collides
    (`chain_root_swap_invisible_for_some_distinct_bindings`; and
    `chain_root_swap_invisible_for_two_valid_bindings` for two self-
    consistent records whose implementations the hash does separate).
    Second, "a chain failing `IsValidChain` cannot share a root with a valid
    one" is false for every `hashImpl` as well
    (`invalid_chain_can_share_a_root_with_a_valid_one`). Degeneracy of the
    hash is a further and weaker limitation, kept for what it is in
    `chain_root_commutes_under_a_degenerate_hash`. Each theorem names the
    hypothesis it needs.
  * The concrete examples at the foot of the section introduce their
    commitments (`bindingHash := 11`, `bindingHash := 13`) through
    `BindingValid` hypotheses, and the proofs consume those hypotheses. The
    literals are the values the documented stand-in `String.length` would
    give for those strings, but NOTHING in this file ties either literal to
    its string, and with the hash uninterpreted nothing can: a `BindingValid`
    hypothesis asserts `11 = hashImpl "benign_impl"`, it does not check it.
    The proofs use only that 13 and 11 are different naturals, so any other
    distinct pair would compile just as well. Read the literals as
    illustration; the distinctness is the only load-bearing part.
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

/-- The leaf digest of a single binding: a stride-`MIX` packing of the runtime
    hash of the implementation, the hash the record commits to, and the link
    to its predecessor. Each of the three fields reaches the chain root
    through this digest, so changing any ONE of them on its own moves the
    digest — that is what the three `bindingDigest_ne_of_*` lemmas below say,
    and it is all they say.

    The packing is NOT injective, and the docstrings here are careful not to
    suggest it is. `MIX * bindingHash` and `prevHash` are added at the same
    stride and neither field is bounded, so two changes can cancel:
    `bindingDigest_collides_for_some_distinct_bindings` exhibits distinct
    records with equal digests for every `hashImpl`, and
    `bindingDigest_eq_iff_fields_eq_of_fields_lt_MIX` gives the range in
    which no such cancellation is available. -/
def bindingDigest (b : ActionBinding) : Nat :=
  MIX * MIX * hashImpl b.implementation + MIX * b.bindingHash + b.prevHash

/-- The chain root: a positional (Horner) fold of the per-binding digests,
    seeded by the genesis commitment. The step `acc ↦ MIX * acc + digest` is
    not commutative, so — unlike the plain sum this replaced — the root
    distinguishes two orderings exactly when it distinguishes the two digests
    (`chain_root_swap_eq_iff_digest_eq`). It does not follow that the root
    sees every field of every record: it sees the digest, and the digest is
    lossy (see `bindingDigest`). Two distinct records with equal digests are
    interchangeable everywhere in this file. -/
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

/-- The limit of the three lemmas above, proved rather than assumed: each
    field reaches the digest **in isolation**, but the digest does not
    separate records. `MIX * bindingHash` and `prevHash` are added at the same
    stride, so raising one of the two by `MIX` while lowering the other by one
    cancels out. The two witnesses below carry the *same* implementation
    string, so no property of `hashImpl` — collision-resistance, injectivity,
    anything — can rule the collision out: it holds for every hash. -/
theorem bindingDigest_collides_for_some_distinct_bindings (s : String) :
    ∃ x y : ActionBinding,
      x ≠ y ∧ bindingDigest hashImpl x = bindingDigest hashImpl y := by
  refine ⟨{ implementation := s, bindingHash := 1, prevHash := 0 },
          { implementation := s, bindingHash := 0, prevHash := MIX }, ?_, ?_⟩
  · intro hEq
    injection hEq with _ hCommit _
    exact absurd hCommit (by decide)
  · simp only [bindingDigest, MIX]

/-- Therefore "distinct records get distinct digests" is not an assumption a
    reader may grant: it is refutable, for every `hashImpl`. Anything proved
    from it would be vacuous — the hypothesis also proves `0 = 1` — so no
    theorem in this file carries it, and the order- and tamper-sensitivity
    results below are conditional on the two records at hand having distinct
    digests instead. -/
theorem bindingDigest_is_not_collision_free :
    ¬ ∀ x y : ActionBinding,
        bindingDigest hashImpl x = bindingDigest hashImpl y → x = y := by
  intro hCollisionFree
  rcases bindingDigest_collides_for_some_distinct_bindings hashImpl "" with ⟨x, y, hne, hEq⟩
  exact hne (hCollisionFree x y hEq)

/-- Exactly where the packing stops losing information: while both packed
    fields stay below the stride, the digest determines all three components
    of the record, and the collision above is impossible. The hypotheses are
    what the name says and nothing weaker — `MIX` is 31, so this holds only
    of records whose committed hash and link are single "digits" in base
    `MIX`. A `BindingValid` record commits `hashImpl b.implementation`, and a
    real hash's outputs are not below 31, so this lemma does NOT apply to the
    bindings the chapter is about; it is here to locate the failure, not to
    repair it. -/
theorem bindingDigest_eq_iff_fields_eq_of_fields_lt_MIX (b b' : ActionBinding)
    (hCommit : b.bindingHash < MIX) (hLink : b.prevHash < MIX)
    (hCommit' : b'.bindingHash < MIX) (hLink' : b'.prevHash < MIX) :
    bindingDigest hashImpl b = bindingDigest hashImpl b' ↔
      hashImpl b.implementation = hashImpl b'.implementation ∧
        b.bindingHash = b'.bindingHash ∧ b.prevHash = b'.prevHash := by
  simp only [bindingDigest, MIX] at hCommit hLink hCommit' hLink' ⊢
  constructor
  · intro hEq
    refine ⟨?_, ?_, ?_⟩ <;> omega
  · intro hFields
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
    bindings have different digests**. The hypothesis is stated over the
    digests, and the theorem's name says so, because that is the only form
    that is true here.

    It is NOT the collision-resistance assumption of the real system, and it
    is not implied by one: collision-resistance separates the implementation
    hashes, whereas this asks the whole packed digest to differ.
    `chain_root_swap_invisible_for_two_valid_bindings` exhibits two records
    that a hash separating their implementations still leaves with the same
    digest. So a caller must discharge `hDigest` for the pair at hand; it
    does not come for free from the strength of `hashImpl`. -/
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

/-- The unconditional reading — "`chainRoot [a, b] = chainRoot [b, a]` fails
    whenever `a ≠ b`" — is FALSE in this model, and this is its refutation,
    not a caveat. It holds for every `hashImpl`, so it is not a statement
    about a weak hash: the two witnesses share an implementation string and
    differ only in the two fields the packing conflates. What survives is the
    digest-level form immediately above; distinctness of the records is not
    enough and cannot be made enough by strengthening `hashImpl`. -/
theorem chain_root_swap_invisible_for_some_distinct_bindings (s : String) :
    ∃ a b : ActionBinding,
      a ≠ b ∧ chainRoot hashImpl [a, b] = chainRoot hashImpl [b, a] := by
  rcases bindingDigest_collides_for_some_distinct_bindings hashImpl s with ⟨a, b, hne, hEq⟩
  exact ⟨a, b, hne, (chain_root_swap_eq_iff_digest_eq hashImpl a b).mpr hEq⟩

/-- The collision above uses one implementation string twice, so a reader may
    hope that two *self-consistent* records whose implementations the hash
    separates are safe. They are not. For any two strings the hash tells
    apart there are records committing to them — each satisfying
    `BindingValid`, i.e. each carrying the true runtime hash of its own
    implementation — whose swap the root does not see. The forger pays for
    the difference between the two implementation hashes in the link field,
    which the packing adds at a stride the difference can exceed.

    This is the precise sense in which collision-resistance of `hashImpl`
    does not lift to the digest: `hSep` is exactly what a collision-resistant
    hash gives on distinct implementations, and it is not enough. -/
theorem chain_root_swap_invisible_for_two_valid_bindings (s t : String)
    (hSep : hashImpl s ≠ hashImpl t) :
    ∃ a b : ActionBinding,
      a ≠ b ∧ a.implementation = s ∧ b.implementation = t ∧
        BindingValid hashImpl a ∧ BindingValid hashImpl b ∧
          chainRoot hashImpl [a, b] = chainRoot hashImpl [b, a] := by
  have hst : s ≠ t := fun hEq => hSep (by rw [hEq])
  rcases Nat.le_total (hashImpl s) (hashImpl t) with hle | hle
  · refine ⟨{ implementation := s, bindingHash := hashImpl s,
              prevHash := (MIX * MIX + MIX) * (hashImpl t - hashImpl s) },
            { implementation := t, bindingHash := hashImpl t, prevHash := 0 },
            ?_, rfl, rfl, rfl, rfl, ?_⟩
    · intro hEq
      injection hEq with hImpl _ _
      exact hst hImpl
    · refine (chain_root_swap_eq_iff_digest_eq hashImpl _ _).mpr ?_
      simp only [bindingDigest, MIX]
      omega
  · refine ⟨{ implementation := s, bindingHash := hashImpl s, prevHash := 0 },
            { implementation := t, bindingHash := hashImpl t,
              prevHash := (MIX * MIX + MIX) * (hashImpl s - hashImpl t) },
            ?_, rfl, rfl, rfl, rfl, ?_⟩
    · intro hEq
      injection hEq with hImpl _ _
      exact hst hImpl
    · refine (chain_root_swap_eq_iff_digest_eq hashImpl _ _).mpr ?_
      simp only [bindingDigest, MIX]
      omega

/-- Claim 3 (determinism): the chain root is a function of the binding
    sequence — equal sequences give equal roots. -/
theorem chain_root_deterministic (bs bs' : List ActionBinding) (h : bs = bs') :
    chainRoot hashImpl bs = chainRoot hashImpl bs' := by
  rw [h]

/-- Chain validity and the chain root, joined — before issue #299 the two
    identifier sets were disjoint and no theorem related them. Re-pointing
    one binding's `prevHash` is the cheapest forgery available to an attacker
    who leaves every implementation byte-identical: it breaks `IsValidChain`
    at that position **and** moves the root, so a chain forged this way from
    a valid chain cannot pass itself off as that chain.

    Note the scope, which is narrower than "no invalid chain shares a root
    with a valid one": this covers invalidity caused by a broken *link*
    between two otherwise identical chains, and it needs `hForged` to name
    the field that moved. A chain can also fail `IsValidChain` through a
    forged `bindingHash`, which moves the root only while the rest of the
    record is held fixed — `bindingDigest_ne_of_bindingHash_ne` assumes an
    unchanged link, and an attacker free to move the link too can forge the
    commitment and leave the root exactly where it was. So the general
    statement is not proved here and must not be read into this one: it is
    false, for every `hashImpl` and not only for degenerate ones, and
    `invalid_chain_can_share_a_root_with_a_valid_one` below is the
    counterexample. -/
theorem relink_breaks_validity_and_changes_root
    (a b : ActionBinding) (rest : List ActionBinding) (forgedPrev : Nat)
    (hValid : IsValidChain hashImpl (a :: b :: rest))
    (hForged : forgedPrev ≠ b.prevHash) :
    ¬ IsValidChain hashImpl (a :: { b with prevHash := forgedPrev } :: rest) ∧
      chainRoot hashImpl (a :: b :: rest) ≠
        chainRoot hashImpl (a :: { b with prevHash := forgedPrev } :: rest) := by
  have hLink : b.prevHash = hashImpl a.implementation :=
    link_matches_previous_implementation hashImpl a b rest hValid
  refine ⟨?_, ?_⟩
  · intro hBad
    have hForgedLink : forgedPrev = hashImpl a.implementation :=
      link_matches_previous_implementation hashImpl a _ rest hBad
    exact hForged (hForgedLink.trans hLink.symm)
  · exact tamper_changes_chain_root_of_distinct_digests hashImpl [a] rest b
      { b with prevHash := forgedPrev }
      (bindingDigest_ne_of_prevHash_ne hashImpl b _ rfl rfl (fun h => hForged h.symm))

/-- The scope limit on `relink_breaks_validity_and_changes_root`, made
    explicit and proved. "A chain failing `IsValidChain` cannot share a root
    with a valid one" is false, and it is false for EVERY `hashImpl` —
    `hashImpl` is the section variable here, so this counterexample is
    universally quantified over it and an injective, collision-resistant hash
    admits it just as the constant hash does.

    The valid chain is as strong as the model allows: it satisfies
    `IsValidChain` and every one of its bindings satisfies `BindingValid`.
    The forgery keeps the second record byte-identical and rewrites the head,
    raising its committed hash by one — which breaks `BindingValid`, and with
    it the chain — while dropping the head's link by `MIX`. The digest packs
    those two fields at the same stride, so the two changes cancel and the
    root does not move. -/
theorem invalid_chain_can_share_a_root_with_a_valid_one (sa sb : String) :
    ∃ valid invalid : List ActionBinding,
      IsValidChain hashImpl valid ∧ (∀ b ∈ valid, BindingValid hashImpl b) ∧
        ¬ IsValidChain hashImpl invalid ∧
          chainRoot hashImpl valid = chainRoot hashImpl invalid := by
  refine ⟨[{ implementation := sa, bindingHash := hashImpl sa, prevHash := MIX },
           { implementation := sb, bindingHash := hashImpl sb,
             prevHash := hashImpl sa }],
          [{ implementation := sa, bindingHash := hashImpl sa + 1, prevHash := 0 },
           { implementation := sb, bindingHash := hashImpl sb,
             prevHash := hashImpl sa }],
          ⟨rfl, rfl, trivial⟩, ?_, ?_, ?_⟩
  · intro b hb
    simp only [List.mem_cons, List.not_mem_nil, or_false] at hb
    rcases hb with rfl | rfl <;> rfl
  · intro hForged
    have hHead : hashImpl sa + 1 = hashImpl sa := hForged.1
    omega
  · unfold chainRoot bindingDigest
    simp only [List.foldl_cons, List.foldl_nil, GENESIS_HASH, MIX]
    omega

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
    its chain ('benign_impl' → 'tampered_impl'). Each record carries its own
    `BindingValid` commitment — `13` and `11`, the lengths the documented
    stand-in would give — and the proof consumes both hypotheses: they are
    what turns the two literals into a difference between
    `hashImpl "tampered_impl"` and `hashImpl "benign_impl"`.

    What the proof uses of the literals is only that they are DISTINCT. No
    step ties 13 to `"tampered_impl"`, and with `hashImpl` uninterpreted no
    step could: substituting 12, or any other natural different from 11,
    leaves the example compiling. The values illustrate §2.1, they are not
    pinned by it. -/
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

/-- The hash's own contribution to the limitation, isolated. Under a constant
    `hashImpl` two bindings that differ ONLY in their implementation carry
    the same digest, so the swap is invisible in the root.

    This is the weaker half of the story and is kept for exactly that: it is
    the one failure mode a stronger `hashImpl` would remove. The collisions
    proved inside the section assume nothing about the hash and survive an
    injective one, so it is those, not this, that stop any theorem here from
    reading "distinct bindings, therefore distinct roots".

    Being existential over hashes it must exhibit one, so — alone in this
    file — it evaluates a concrete `hashImpl`. That is why it sits outside
    section `RuntimeHash`, where the header's no-evaluation rule holds, and
    why what it proves is a limitation rather than a guarantee. -/
theorem chain_root_commutes_under_a_degenerate_hash :
    ∃ (hashImpl : String → Nat) (a b : ActionBinding),
      a ≠ b ∧ chainRoot hashImpl [a, b] = chainRoot hashImpl [b, a] := by
  refine ⟨fun _ => 0,
    { implementation := "benign_impl", bindingHash := 0, prevHash := 0 },
    { implementation := "rm_rf_slash", bindingHash := 0, prevHash := 0 }, ?_, rfl⟩
  intro h
  injection h with hImpl _ _
  exact absurd hImpl (by decide)
