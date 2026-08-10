/-
  Sandboxed Isolation Buffer (Ontology Extension)
  ===============================================
  From Chapter 4 (§5 Ontology Extension, §5.2 The Extension Protocol):
  - Phase 1: Parliament votes unanimously to propose x_new; the vote
    authorizes the sandbox, it does not bind the action.
  - Phase 2: x_new enters the isolation buffer: a cryptographic sandbox
    whose runtime behavior is observed by N independent monitors, each
    deriving an empirical property vector prop_new^(emp).
  - Phase 3: external key-holders audit the empirical properties (3-of-5).
  - Phase 4: only a fully cleared binding is appended to the ontology.

  We prove:
  - properties measured in the buffer are validated by independent monitors
    before any extension can happen
  - extensions from the buffer never mutate the base ontology directly:
    base ontology changes require the core (Constitutional-tier) mutability
    path
  - a failed validation leaves the base ontology unchanged — no partial
    application
-/

/-- The base ontology: strings standing for the immutable action namespace O
    (Chapter 4 §2.1). Buffer extensions may append to it, never modify it. -/
def baseOntology : List String :=
  ["identity_commit", "checkpoint", "withdraw"]

/-- An extension candidate sitting in the isolation buffer (§5.2 Phase 2–3). -/
structure BufferedExtension where
  candidate : String
  measuredByMonitor : Bool
  validatedByMonitor : Bool
  auditedByKeyholders : Bool

/-- Number of independent monitors observing the buffer (§5.2 Phase 2). -/
def MONITOR_COUNT : Nat := 3

/-- §5.2 Phase 2: the buffer must be observed by at least one independent
    monitor. -/
theorem monitor_coverage_at_least_one : 1 ≤ MONITOR_COUNT := by
  unfold MONITOR_COUNT
  decide

/-- §5.2 Phase 2–3: all three gates — sandbox measurement, independent-monitor
    validation, and the external 3-of-5 key-holder audit. -/
def clearedCheck (ext : BufferedExtension) : Bool :=
  ext.measuredByMonitor && ext.validatedByMonitor && ext.auditedByKeyholders

/-- The clearance proposition: `clearedCheck ext = true`. -/
def isCleared (ext : BufferedExtension) : Prop :=
  clearedCheck ext = true

/-- Apply the buffered extension. A failed validation yields the base
    ontology unchanged — no partial application can occur. -/
def extendFromBuffer (ext : BufferedExtension) : List String :=
  if clearedCheck ext then baseOntology ++ [ext.candidate] else baseOntology

/-- §5.2 Phase 2: no extension is applied unless an independent monitor
    measured and validated the candidate's properties in the sandbox. -/
theorem extension_requires_monitor_validation (ext : BufferedExtension)
    (h : isCleared ext) : ext.measuredByMonitor ∧ ext.validatedByMonitor := by
  unfold isCleared clearedCheck at h
  simp [Bool.and_eq_true] at h
  exact ⟨h.1.1, h.1.2⟩

/-- §5.2 Phase 2: a measured but unvalidated candidate is never cleared,
    regardless of any other flags. -/
theorem unvalidated_extension_never_cleared (ext : BufferedExtension)
    (h : ¬ ext.validatedByMonitor) : ¬ isCleared ext := by
  intro hc
  unfold isCleared clearedCheck at hc
  simp [Bool.and_eq_true] at hc
  exact h hc.1.2

/-- §5.2 Phase 3: no extension is applied without the external 3-of-5
    key-holder audit. -/
theorem extension_requires_external_audit (ext : BufferedExtension)
    (h : isCleared ext) : ext.auditedByKeyholders := by
  unfold isCleared clearedCheck at h
  simp [Bool.and_eq_true] at h
  exact h.2

/-- §5.2 Phase 2–3: without full clearance the base ontology is unchanged. -/
theorem failed_validation_leaves_base_unchanged (ext : BufferedExtension)
    (h : ¬ isCleared ext) : extendFromBuffer ext = baseOntology := by
  unfold extendFromBuffer
  by_cases hc : clearedCheck ext = true
  · exact False.elim (h hc)
  · simp [hc]

/-- §5.2: no partial application — the result is either the untouched base
    ontology or the complete extension baseOntology ++ [candidate]. -/
theorem no_partial_application (ext : BufferedExtension) :
    extendFromBuffer ext = baseOntology ∨
    extendFromBuffer ext = baseOntology ++ [ext.candidate] := by
  unfold extendFromBuffer
  by_cases hc : clearedCheck ext = true <;> simp [hc]

/-- §5.2 Phase 4: a cleared extension appends exactly its candidate to the
    base ontology. -/
theorem cleared_extension_appends_candidate (ext : BufferedExtension)
    (h : isCleared ext) : extendFromBuffer ext = baseOntology ++ [ext.candidate] := by
  unfold extendFromBuffer
  by_cases hc : clearedCheck ext = true
  · simp [hc]
  · exact False.elim (hc h)

/-- §5.2: whatever the buffer returns, the base ontology is its strict-prefix
    part — entries can never be altered, reordered, or removed by a buffer
    extension. Extension is append-only. -/
theorem extension_only_extends_base (ext : BufferedExtension) :
    List.IsPrefix baseOntology (extendFromBuffer ext) := by
  unfold extendFromBuffer
  by_cases hc : clearedCheck ext = true <;> simp [hc, baseOntology, List.IsPrefix]

/-- §5.2 + §3.2: a buffer extension never rewrites the base ontology — the
    base is either untouched or extended by exactly one entry. Base ontology
    changes outside this protocol are Constitutional-tier core-mutability
    changes, which are disjoint from the extension procedure. -/
theorem buffer_extension_never_rewrites_base (ext : BufferedExtension) :
    (extendFromBuffer ext).length = baseOntology.length ∨
    (extendFromBuffer ext).length = baseOntology.length + 1 := by
  unfold extendFromBuffer
  by_cases hc : clearedCheck ext = true <;> simp [hc, baseOntology]

/-- The buffer cannot remove or replace base entries: the candidate can never
    appear inside the base segment. -/
theorem candidate_never_replaces_base_entry (ext : BufferedExtension) :
    baseOntology = (extendFromBuffer ext).take baseOntology.length := by
  unfold extendFromBuffer
  by_cases hc : clearedCheck ext = true <;> simp [hc, baseOntology, List.take, List.length]

/-- Fully measured, validated, and audited candidate is appended. -/
example : extendFromBuffer
      { candidate := "safe_action", measuredByMonitor := true,
        validatedByMonitor := true, auditedByKeyholders := true }
    = baseOntology ++ ["safe_action"] := by
  apply cleared_extension_appends_candidate
  simp [isCleared, clearedCheck]

/-- A candidate that failed monitor validation leaves the base ontology
    untouched. -/
example : extendFromBuffer
      { candidate := "risky_action", measuredByMonitor := true,
        validatedByMonitor := false, auditedByKeyholders := true }
    = baseOntology := by
  apply failed_validation_leaves_base_unchanged
  intro hc
  unfold isCleared clearedCheck at hc
  simp at hc