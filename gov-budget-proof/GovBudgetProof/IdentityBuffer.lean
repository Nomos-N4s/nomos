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
  - properties measured in the buffer are validated by the independent
    monitors before any extension can happen: clearance requires approvals
    from `MONITOR_COUNT` DISTINCT monitors of the roster, and duplicates
    never count twice
  - Phase 3 is the same 3-of-5 external multisig the genesis manifest is
    held to: the audit gate is `GENESIS_QUORUM ≤ quorumCount signatures`,
    imported from `GovBudgetProof.IdentityGenesis` rather than restated, so
    two key holders can no more clear a buffer extension than they can
    bootstrap genesis
  - extensions from the buffer never mutate the base ontology directly:
    base ontology changes require the core (Constitutional-tier) mutability
    path
  - a failed validation leaves the base ontology unchanged — no partial
    application

  Two limits a reader must keep, and no docstring below softens either.
  First, the roster holds exactly `MONITOR_COUNT` monitors, so the Phase 2
  bar is UNANIMITY of the monitors that exist and not a threshold among a
  larger pool; `every_monitor_must_approve` states that outright. Second,
  the sandbox measurement of Phase 2 is still a single `Bool`
  (`measuredByMonitor`): it is an input this model records, not a quantity
  it counts, and nothing here proves a measurement happened.

  Before issue #298 the monitors and the key holders were three `Bool`
  fields: `MONITOR_COUNT` was declared and then never mentioned outside its
  own theorem `1 ≤ MONITOR_COUNT`, and the "external 3-of-5 key-holder
  audit" of Phase 3 was a single `auditedByKeyholders : Bool`. Nothing in
  the module counted anybody.
-/

import GovBudgetProof.IdentityGenesis

/-- The base ontology: strings standing for the immutable action namespace O
    (Chapter 4 §2.1). Buffer extensions may append to it, never modify it. -/
def baseOntology : List String :=
  ["identity_commit", "checkpoint", "withdraw"]

/-- The independent monitors observing the sandbox (§5.2 Phase 2). Named
    individually so that "an independent monitor validated it" can be counted
    rather than asserted by a flag. -/
inductive Monitor : Type
  | m1
  | m2
  | m3
  deriving DecidableEq

/-- The monitor roster: the N independent monitors of §5.2 Phase 2. -/
def monitorRoster : List Monitor :=
  [Monitor.m1, Monitor.m2, Monitor.m3]

/-- Number of independent monitors observing the buffer (§5.2 Phase 2), and
    the number of distinct approvals a candidate needs. -/
def MONITOR_COUNT : Nat := 3

/-- A configuration check and nothing more: both sides reduce to the numeral
    3, so this is closed by `rfl` and would hold of a roster the running
    system rewrote on every tick. It carries no claim about monitors. What it
    is for is that it stops compiling if the bar and the roster drift apart —
    shorten `monitorRoster` or raise `MONITOR_COUNT` and the mismatch is
    caught here rather than turning `monitorsValidated` into a gate no
    approval list can pass. -/
theorem monitor_roster_has_monitor_count : monitorRoster.length = MONITOR_COUNT := rfl

/-- Whether a monitor has approved: their name occurs in the approval list. -/
def hasApproved (m : Monitor) (approvals : List Monitor) : Bool :=
  approvals.any (fun k => decide (k = m))

/-- The number of DISTINCT roster monitors that approved. Duplicates never
    count twice — the same shape as `IdentityGenesis.quorumCount`, and for
    the same reason: one monitor repeating itself is not independent
    observation. -/
def approvalCount (approvals : List Monitor) : Nat :=
  (monitorRoster.filter (fun m => hasApproved m approvals)).length

/-- An extension candidate sitting in the isolation buffer (§5.2 Phase 2–3).
    The monitor approvals and the key-holder signatures are lists, not flags:
    both gates are counted. -/
structure BufferedExtension where
  candidate : String
  measuredByMonitor : Bool
  monitorApprovals : List Monitor
  keyholderSignatures : List GenesisKey

/-- §5.2 Phase 2 gate: `MONITOR_COUNT` distinct monitors approved. -/
def monitorsValidated (ext : BufferedExtension) : Bool :=
  MONITOR_COUNT ≤ approvalCount ext.monitorApprovals

/-- §5.2 Phase 3 gate: the external key-holder audit, decided by the very
    quorum count the genesis manifest is held to (`IdentityGenesis`). -/
def keyholdersAudited (ext : BufferedExtension) : Bool :=
  GENESIS_QUORUM ≤ quorumCount ext.keyholderSignatures

/-- §5.2 Phase 2–3: all three gates — sandbox measurement, independent-monitor
    validation, and the external 3-of-5 key-holder audit. -/
def clearedCheck (ext : BufferedExtension) : Bool :=
  ext.measuredByMonitor && monitorsValidated ext && keyholdersAudited ext

/-- The clearance proposition: `clearedCheck ext = true`. -/
def isCleared (ext : BufferedExtension) : Prop :=
  clearedCheck ext = true

/-- Apply the buffered extension. A failed validation yields the base
    ontology unchanged — no partial application can occur. -/
def extendFromBuffer (ext : BufferedExtension) : List String :=
  if clearedCheck ext then baseOntology ++ [ext.candidate] else baseOntology

/-- The approval count cannot exceed the roster: no list of approvals, however
    long or however repetitive, counts more monitors than exist. -/
theorem approval_count_bounded_by_roster (approvals : List Monitor) :
    approvalCount approvals ≤ MONITOR_COUNT := by
  unfold approvalCount MONITOR_COUNT
  have h := List.length_filter_le (fun m => hasApproved m approvals) monitorRoster
  rw [show monitorRoster.length = 3 by unfold monitorRoster; rfl] at h
  exact h

/-- §5.2 Phase 2: no extension is applied unless the candidate was measured in
    the sandbox and `MONITOR_COUNT` distinct monitors approved it. This is
    what `MONITOR_COUNT` now buys; the constant used to appear only in
    `1 ≤ MONITOR_COUNT`. -/
theorem extension_requires_monitor_validation (ext : BufferedExtension)
    (h : isCleared ext) :
    ext.measuredByMonitor ∧ MONITOR_COUNT ≤ approvalCount ext.monitorApprovals := by
  unfold isCleared clearedCheck monitorsValidated at h
  simp [Bool.and_eq_true] at h
  exact ⟨h.1.1, h.1.2⟩

/-- §5.2 Phase 2: too few distinct approvals and the candidate is never
    cleared, whatever else it carries. -/
theorem unvalidated_extension_never_cleared (ext : BufferedExtension)
    (h : approvalCount ext.monitorApprovals < MONITOR_COUNT) : ¬ isCleared ext := by
  intro hc
  exact absurd (extension_requires_monitor_validation ext hc).2 (Nat.not_le.mpr h)

/-- §5.2 Phase 2: a single monitor cannot stand in for the roster by signing
    repeatedly — the duplicate is counted once. -/
theorem duplicate_approval_counts_once (m : Monitor) : approvalCount [m, m] = 1 := by
  unfold approvalCount monitorRoster hasApproved
  cases m <;> decide

/-- §5.2 Phase 2: two monitors, distinct or not, never reach the bar. -/
theorem two_monitor_approvals_insufficient (a b : Monitor) :
    ¬ MONITOR_COUNT ≤ approvalCount [a, b] := by
  unfold MONITOR_COUNT approvalCount monitorRoster hasApproved
  cases a <;> cases b <;> decide

/-- The bar is reachable — `MONITOR_COUNT` is not set above what the roster
    can supply, so the theorems that assume clearance are not assuming
    something impossible. -/
theorem full_roster_clears_the_monitor_gate :
    MONITOR_COUNT ≤ approvalCount monitorRoster := by
  unfold MONITOR_COUNT approvalCount monitorRoster hasApproved
  decide

/-- What clearance means for each monitor individually: with the roster the
    size of the bar, `MONITOR_COUNT` distinct approvals is unanimity, so every
    monitor on the roster approved. -/
theorem every_monitor_must_approve (approvals : List Monitor)
    (h : MONITOR_COUNT ≤ approvalCount approvals) (m : Monitor) :
    hasApproved m approvals = true := by
  unfold MONITOR_COUNT approvalCount monitorRoster at h
  by_cases h1 : hasApproved Monitor.m1 approvals = true <;>
    by_cases h2 : hasApproved Monitor.m2 approvals = true <;>
      by_cases h3 : hasApproved Monitor.m3 approvals = true <;>
        simp [List.filter, h1, h2, h3] at h ⊢ <;>
          cases m <;> simp [h1, h2, h3]

/-- §5.2 Phase 3: no extension is applied without the external key-holder
    audit, and the audit is the genesis quorum — `GENESIS_QUORUM` distinct
    key holders out of the five, counted by `IdentityGenesis.quorumCount`. -/
theorem extension_requires_external_audit (ext : BufferedExtension)
    (h : isCleared ext) : GENESIS_QUORUM ≤ quorumCount ext.keyholderSignatures := by
  unfold isCleared clearedCheck keyholdersAudited at h
  simp [Bool.and_eq_true] at h
  exact h.2

/-- §5.2 Phase 3 + §4.4: two key holders cannot clear a buffer extension, for
    the same reason they cannot bootstrap genesis. The proof consumes
    `IdentityGenesis.any_two_signatures_insufficient`, so the two modules are
    joined in the proof term and not merely in the prose. -/
theorem two_keyholder_signatures_never_clear (candidate : String) (measured : Bool)
    (approvals : List Monitor) (a b : GenesisKey) :
    ¬ isCleared { candidate := candidate, measuredByMonitor := measured,
                  monitorApprovals := approvals, keyholderSignatures := [a, b] } := by
  intro hc
  exact any_two_signatures_insufficient a b (extension_requires_external_audit _ hc)

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

/-- Measured, approved by the whole monitor roster, and audited by three of
    the five key holders: the candidate is appended. -/
example : extendFromBuffer
      { candidate := "safe_action", measuredByMonitor := true,
        monitorApprovals := monitorRoster,
        keyholderSignatures := [GenesisKey.k1, GenesisKey.k2, GenesisKey.k3] }
    = baseOntology ++ ["safe_action"] := by
  apply cleared_extension_appends_candidate
  unfold isCleared clearedCheck monitorsValidated keyholdersAudited
    approvalCount monitorRoster hasApproved MONITOR_COUNT
    quorumCount genesisKeys hasSigned GENESIS_QUORUM
  decide

/-- Two monitors out of three is short of the Phase 2 bar, so the base
    ontology is untouched — even with a full key-holder audit. -/
example : extendFromBuffer
      { candidate := "risky_action", measuredByMonitor := true,
        monitorApprovals := [Monitor.m1, Monitor.m2],
        keyholderSignatures := [GenesisKey.k1, GenesisKey.k2, GenesisKey.k3] }
    = baseOntology := by
  apply failed_validation_leaves_base_unchanged
  apply unvalidated_extension_never_cleared
  unfold MONITOR_COUNT approvalCount monitorRoster hasApproved
  decide

/-- Two key holders out of five is short of the Phase 3 bar, so the base
    ontology is untouched — even with the whole monitor roster behind the
    candidate. -/
example : extendFromBuffer
      { candidate := "risky_action", measuredByMonitor := true,
        monitorApprovals := monitorRoster,
        keyholderSignatures := [GenesisKey.k1, GenesisKey.k2] }
    = baseOntology := by
  apply failed_validation_leaves_base_unchanged
  exact two_keyholder_signatures_never_clear _ _ _ _ _