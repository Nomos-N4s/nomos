/-
  Identity Coherence Threshold
  ============================
  From Chapter 4 §6.1 (The Integrity Committee as Proxy):

  - V_integrity(s, a) = identity_coherence(a, C_core): the committee
    evaluates every proposed action against the deterministic identity
    vector derived from the core commitments.
  - The identity vector is NOT learned: semantic drift in the optimization
    layer never shifts the yardstick.
  - A coherence gate guards identity mutation: only actions whose
    coherence score meets the configured threshold may be adopted; below
    threshold, the action is rejected and the identity state must not
    change at all.

  We prove the three claims of issue #194:
  1. Every accepted action keeps identity coherence at or above the
     configured threshold.
  2. An action that would reduce coherence below the threshold is
     rejected without mutating identity state.
  3. Coherence is monotonic under rejected actions — rejection never
     degrades identity coherence (the state is untouched).
-/

/-- Configured identity coherence threshold (example value; the identity
    vector and distance measure are specified in §6.1). -/
def COHERENCE_THRESHOLD : Nat := 70

/-- A proposed action carrying its empirically measured coherence score
    against the identity vector (V_integrity, §6.1). -/
structure Action where
  id : Nat
  coherenceScore : Nat

/-- The agent's current identity state: its coherence level. -/
structure IdentityState where
  coherence : Nat

/-- The coherence gate: the action is acceptable iff its measured coherence
    meets the configured threshold. -/
def acceptable (a : Action) : Bool :=
  decide (COHERENCE_THRESHOLD ≤ a.coherenceScore)

/-- Identity mutation under guard: an acceptable action adopts its
    coherence score; anything below threshold leaves the identity state
    untouched. -/
def acceptAction (state : IdentityState) (a : Action) : IdentityState :=
  if acceptable a then { coherence := a.coherenceScore } else state

/-- The gate is exactly the threshold comparison (acceptance criterion of
    §6.1). -/
theorem acceptable_iff_ge (a : Action) :
    acceptable a = true ↔ COHERENCE_THRESHOLD ≤ a.coherenceScore := by
  unfold acceptable
  constructor
  · intro h
    exact of_decide_eq_true h
  · intro h
    rw [decide_eq_true_eq]
    exact h

/-- Claim 1: every accepted action keeps identity coherence at or above the
    configured threshold. -/
theorem accepted_action_keeps_coherence (state : IdentityState) (a : Action)
    (h : acceptable a = true) :
    COHERENCE_THRESHOLD ≤ (acceptAction state a).coherence := by
  unfold acceptAction
  by_cases hg : acceptable a = true
  · simp [hg]
    exact (acceptable_iff_ge a).1 h
  · exact False.elim (hg h)

/-- An action whose coherence is below the threshold is rejected. -/
theorem below_threshold_rejection_leaves_state (state : IdentityState) (a : Action)
    (h : a.coherenceScore < COHERENCE_THRESHOLD) : acceptAction state a = state := by
  unfold acceptAction
  have hn : ¬ COHERENCE_THRESHOLD ≤ a.coherenceScore := by
    omega
  have hg : acceptable a = false := by
    simp [acceptable, hn]
  simp [hg]

/-- Claim 2: an action that would reduce coherence below the threshold is
    rejected WITHOUT mutating identity state. -/
theorem rejected_action_does_not_mutate_identity (state : IdentityState) (a : Action)
    (h : a.coherenceScore < COHERENCE_THRESHOLD) : (acceptAction state a).coherence = state.coherence := by
  rw [below_threshold_rejection_leaves_state state a h]

/-- Generic no-mutation: whenever the gate does not pass, the identity
    state is unchanged (covers threshold misses of any form). -/
theorem unacceptable_action_leaves_state (state : IdentityState) (a : Action)
    (h : acceptable a = false) : acceptAction state a = state := by
  unfold acceptAction
  by_cases hg : acceptable a = true
  · have hbad : true = false := by rw [← hg, h]
    exact False.elim (Bool.noConfusion hbad)
  · simp [hg]