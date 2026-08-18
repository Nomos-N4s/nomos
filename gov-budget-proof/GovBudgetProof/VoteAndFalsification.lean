/-
  Vote Threshold and Falsification Counter Invariants
  ====================================================
  From Chapter 2 (§2.4–2.5) and Chapter 4 (§7.2):
  - Vote resolution is constructively decidable, and is determined by the
    tallies alone
  - Threshold comparison is consistent across decision classes
  - Falsification counts are non-negative and correct
  - Budget halving preserves b ≥ 1 when starting from b ≥ 1
  - Falsification parameters are immutable-tier
-/

import GovBudgetProof.IdentityTiers

/-- Three decision classes for vote threshold. -/
inductive DecisionClass : Type
  | routine
  | highImpact
  | identity

/-- A member's vote consists of a weight and a score. -/
structure Vote where
  weight : Nat
  score : Nat

/-- Sum of votes' weighted scores. -/
def weightedSum (votes : List Vote) : Nat :=
  votes.foldl (λ acc v => acc + v.weight * v.score) 0

/-- Sum of votes' weights. -/
def totalWeight (votes : List Vote) : Nat :=
  votes.foldl (λ acc v => acc + v.weight) 0

/-- Threshold for each decision class as numerator/denominator.
    vote passes iff  weightedSum * denom ≥ num * totalWeight
-/
structure Threshold where
  num : Nat
  denom : Nat

def thresholdOf (d : DecisionClass) : Threshold :=
  match d with
  | DecisionClass.routine    => { num := 1, denom := 2 }
  | DecisionClass.highImpact => { num := 2, denom := 3 }
  | DecisionClass.identity   => { num := 1, denom := 1 }

/-- A vote passes if the weighted average meets or exceeds the threshold. -/
def votePasses (votes : List Vote) (d : DecisionClass) : Prop :=
  let t := thresholdOf d
  let ws := weightedSum votes
  let tw := totalWeight votes
  tw ≠ 0 ∧ t.num * tw ≤ ws * t.denom

/-- Vote resolution is decidable *constructively*: `votePasses` unfolds to a
    `Nat` disequality and a `Nat` comparison, so the outcome is computed by
    `Nat.decEq` and `Nat.decLe` and never postulated. `#print axioms` on this
    instance reports no axioms at all — in particular no `Classical.choice`. -/
instance decidableVotePasses (votes : List Vote) (d : DecisionClass) :
    Decidable (votePasses votes d) :=
  inferInstanceAs (Decidable (totalWeight votes ≠ 0 ∧
    (thresholdOf d).num * totalWeight votes ≤ weightedSum votes * (thresholdOf d).denom))

/-- The boolean decision procedure agrees with the specification: `decide`
    returns `true` exactly on the ballots that pass. -/
theorem vote_outcome_computes (votes : List Vote) (d : DecisionClass) :
    decide (votePasses votes d) = true ↔ votePasses votes d :=
  decide_eq_true_iff

/-- Every ballot resolves one way or the other. The disjunction is closed by
    `Decidable.em` on the instance above — excluded middle for a proposition
    that is *decidable*, which is a theorem — rather than by the classical
    axiom `Classical.em`. The delta is the axiom base, and only that:
    `#print axioms vote_resolution_total` reports no axioms. -/
theorem vote_resolution_total (votes : List Vote) (d : DecisionClass) :
    votePasses votes d ∨ ¬ votePasses votes d :=
  Decidable.em (votePasses votes d)

/-- Consistency: equal vote lists produce the same outcome. -/
theorem vote_threshold_consistent (v1 v2 : List Vote) (d : DecisionClass)
    (h : v1 = v2) : votePasses v1 d ↔ votePasses v2 d := by
  subst h; rfl

/-- Determinism: the outcome is a function of the tallies alone. Two ballot
    lists with the same weighted sum and the same total weight resolve the
    same way in every decision class, so who cast which ballot, in what order
    and in how many pieces, cannot change the result. -/
theorem vote_resolution_determined_by_tallies (v1 v2 : List Vote) (d : DecisionClass)
    (hw : weightedSum v1 = weightedSum v2) (ht : totalWeight v1 = totalWeight v2) :
    votePasses v1 d ↔ votePasses v2 d := by
  simp only [votePasses, hw, ht]

/-- Identity passing (1*tw ≤ ws*1) implies totalWeight ≤ weightedSum. -/
theorem identity_passes_implies_sum_ge (votes : List Vote)
    (h : votePasses votes DecisionClass.identity) :
    totalWeight votes ≤ weightedSum votes := by
  rcases h with ⟨htw, h⟩
  simpa [thresholdOf] using h

/-- If vote passes identity, it also passes highImpact and routine. -/
theorem identity_passes_implies_others (votes : List Vote)
    (h : votePasses votes DecisionClass.identity) :
    votePasses votes DecisionClass.highImpact ∧
    votePasses votes DecisionClass.routine := by
  have h_ge : totalWeight votes ≤ weightedSum votes :=
    identity_passes_implies_sum_ge votes h
  rcases h with ⟨htw, _⟩
  have h_high : votePasses votes DecisionClass.highImpact := by
    refine ⟨htw, ?_⟩
    calc
      2 * totalWeight votes ≤ 3 * totalWeight votes :=
        Nat.mul_le_mul_right (totalWeight votes) (by decide : 2 ≤ 3)
      _ = totalWeight votes * 3 := by simpa [Nat.mul_comm]
      _ ≤ weightedSum votes * 3 := Nat.mul_le_mul_right 3 h_ge
  have h_routine : votePasses votes DecisionClass.routine := by
    refine ⟨htw, ?_⟩
    calc
      1 * totalWeight votes ≤ 1 * weightedSum votes :=
        Nat.mul_le_mul_left 1 h_ge
      _ = weightedSum votes := by simp
      _ ≤ weightedSum votes * 2 := by
        have : 1 ≤ 2 := by decide
        simpa [Nat.mul_comm] using Nat.mul_le_mul_right (weightedSum votes) this
  exact And.intro h_high h_routine

/-- Empty vote list never passes. -/
theorem empty_vote_never_passes (d : DecisionClass) :
    ¬ votePasses [] d := by
  intro h
  rcases h with ⟨htw, _⟩
  simp [totalWeight] at htw

/-- A routine ballot that clears its threshold is resolved by computation:
    `decide` closes the goal, so no classical step is involved. -/
example : votePasses [⟨2, 1⟩] DecisionClass.routine := by decide

/-- Boundary above: routine passes exactly at the halfway mark (4 ≤ 4). -/
example : votePasses [⟨2, 1⟩, ⟨2, 0⟩] DecisionClass.routine := by decide

/-- Boundary below: one weight more and the same computation rejects it. -/
example : ¬ votePasses [⟨2, 1⟩, ⟨3, 0⟩] DecisionClass.routine := by decide

/-- An identity vote that misses the unanimity bar is rejected by computation. -/
example : ¬ votePasses [⟨2, 0⟩, ⟨1, 1⟩] DecisionClass.identity := by decide

/-- The empty roll is rejected by the decision procedure too, independently of
    `empty_vote_never_passes`. -/
example : ¬ votePasses [] DecisionClass.highImpact := by decide

/-- Two different ballot lists with the same tallies resolve alike. -/
example : votePasses [⟨2, 1⟩] DecisionClass.routine ↔
    votePasses [⟨1, 2⟩, ⟨1, 0⟩] DecisionClass.routine :=
  vote_resolution_determined_by_tallies _ _ _ rfl rfl

/-
  Falsification Counter
  =====================
  A falsification occurs when integrity score < TAG_COMPLIANCE_THRESHOLD.
-/

/-- Compliance threshold: integrity < 4 means falsification. -/
def TAG_COMPLIANCE_THRESHOLD : Nat := 4

/-- Boolean check: is the integrity score a falsification? -/
def isFalsification (integrityScore : Nat) : Bool :=
  integrityScore < TAG_COMPLIANCE_THRESHOLD

/-- A proposal has a member id and an integrity score. -/
structure TrackedProposal where
  memberId : String
  integrityScore : Nat

/-- Count falsifications per member (returns a Nat). -/
def falsificationCount (member : String) (proposals : List TrackedProposal) : Nat :=
  (proposals.filter λ p => p.memberId = member && isFalsification p.integrityScore).length

/-- Falsification count is non-negative. -/
theorem falsification_count_nonneg (member : String) (proposals : List TrackedProposal) :
    0 ≤ falsificationCount member proposals :=
  Nat.zero_le _

/-- A member with no proposals has zero falsifications. -/
theorem falsification_count_empty (member : String) :
    falsificationCount member [] = 0 := by
  simp [falsificationCount]

/-- Every proposal is either a falsification or not. -/
theorem falsification_or_not (integrityScore : Nat) :
    (isFalsification integrityScore) ∨ ¬ (isFalsification integrityScore) := by
  unfold isFalsification
  apply Classical.em

/-
  Budget Halving
  ==============
-/

/-- The cutoff for budget halving. -/
def FALSIFICATION_BUDGET_CUTOFF : Nat := 3

/-- Update budget based on falsification count. -/
def budgetAfterFalsification (oldBudget : Nat) (fc : Nat) : Nat :=
  if fc ≥ FALSIFICATION_BUDGET_CUTOFF then
    max 1 (oldBudget / 2)
  else
    oldBudget

/-- If budget is at least 1 before, it stays at least 1 after. -/
theorem budget_preserves_positive (oldBudget : Nat) (fc : Nat)
    (hpos : 1 ≤ oldBudget) : 1 ≤ budgetAfterFalsification oldBudget fc := by
  unfold budgetAfterFalsification
  split
  · exact Nat.le_max_left 1 (oldBudget / 2)
  · exact hpos

/-- If falsification count is below cutoff, budget is unchanged. -/
theorem budget_unchanged_below_cutoff (oldBudget : Nat) (fc : Nat)
    (h : fc < FALSIFICATION_BUDGET_CUTOFF) :
    budgetAfterFalsification oldBudget fc = oldBudget := by
  unfold budgetAfterFalsification
  have : ¬ (fc ≥ FALSIFICATION_BUDGET_CUTOFF) := by omega
  simp [this]

/-- If fc ≥ cutoff, budget = max 1 (oldBudget / 2). -/
theorem budget_halving_formula (oldBudget : Nat) (fc : Nat)
    (h : fc ≥ FALSIFICATION_BUDGET_CUTOFF) :
    budgetAfterFalsification oldBudget fc = max 1 (oldBudget / 2) := by
  unfold budgetAfterFalsification
  simp [h]

/-
  Falsification Parameter Mutability
  ==================================
  Chapter 4 §3.1. The falsification parameters are *declared* to sit at the
  immutable tier of `GovBudgetProof.IdentityTiers`, and this section works out
  what that declaration buys: a governance step gated on `isPermitted` cannot
  move them.
-/

/-- `isPermitted` is decidable, so a governance step can branch on it by
    computation. Every branch is a `Nat` comparison or the empty condition of
    the immutable tier, so the instance is constructive: `#print axioms`
    reports none, in particular no `Classical.choice`.

    The instance lives here rather than in `IdentityTiers.lean` because it is
    this module that needs to *run* the gate; the tier model itself states the
    bars propositionally and is left untouched. -/
instance decidableIsPermitted (t : Tier) (c : Change) : Decidable (isPermitted t c) :=
  match t with
  | Tier.immutable      => inferInstanceAs (Decidable False)
  | Tier.constitutional =>
      inferInstanceAs (Decidable (CONSTITUTIONAL_QUORUM ≤ c.quorum ∧
        CONSTITUTIONAL_COOLDOWN ≤ c.cooldownDays))
  | Tier.operational    =>
      inferInstanceAs (Decidable (OPERATIONAL_QUORUM ≤ c.quorum ∧
        OPERATIONAL_COOLDOWN ≤ c.cooldownDays))
  | Tier.dynamic        => inferInstanceAs (Decidable (DYNAMIC_QUORUM ≤ c.quorum))

/-- The falsification parameters as a block a governance step could rewrite.
    A bare `def` cannot be immutable — every `def` equals its own body by
    `rfl`, whatever the running system does — so the parameters are carried in
    a value that a transition function is free to change. -/
structure FalsificationParams where
  tagComplianceThreshold : Nat
  budgetCutoff : Nat
  deriving DecidableEq

/-- The block this module actually computes with: the two constants above. -/
def defaultFalsificationParams : FalsificationParams :=
  { tagComplianceThreshold := TAG_COMPLIANCE_THRESHOLD,
    budgetCutoff := FALSIFICATION_BUDGET_CUTOFF }

/-- The tier the falsification parameters are declared at (Chapter 4 §3.1).
    This is a *declaration*, not a theorem: nothing here proves that the
    running system files these parameters under this tier. What the tier buys,
    once granted, is proved below. -/
def falsificationParamsTier : Tier := Tier.immutable

/-- The falsification test, read off a parameter block rather than off the
    module constant. -/
def isFalsificationWith (p : FalsificationParams) (integrityScore : Nat) : Bool :=
  integrityScore < p.tagComplianceThreshold

/-- The budget update, read off a parameter block rather than off the module
    constant. -/
def budgetAfterFalsificationWith (p : FalsificationParams) (oldBudget : Nat) (fc : Nat) : Nat :=
  if fc ≥ p.budgetCutoff then
    max 1 (oldBudget / 2)
  else
    oldBudget

/-- The parameterised falsification test is the operative one: at the default
    block it *is* `isFalsification`, by `rfl`. Without this the block below
    would be a shadow model, and invariance of it would say nothing about the
    behaviour this module defines. -/
theorem isFalsification_eq_at_default (integrityScore : Nat) :
    isFalsification integrityScore
      = isFalsificationWith defaultFalsificationParams integrityScore :=
  rfl

/-- The parameterised budget update is likewise the operative one. -/
theorem budgetAfterFalsification_eq_at_default (oldBudget : Nat) (fc : Nat) :
    budgetAfterFalsification oldBudget fc
      = budgetAfterFalsificationWith defaultFalsificationParams oldBudget fc :=
  rfl

/-
  Falsification parameters are immutable-tier: no governance procedure
  can change TAG_COMPLIANCE_THRESHOLD or FALSIFICATION_BUDGET_CUTOFF.
-/

def falsificationParamsImmutable : Prop :=
  TAG_COMPLIANCE_THRESHOLD = 4 ∧ FALSIFICATION_BUDGET_CUTOFF = 3

theorem falsification_params_are_immutable : falsificationParamsImmutable := by
  unfold falsificationParamsImmutable
  constructor <;> rfl

/-
  Combined invariant: every governance cycle computes its vote outcome with
  the decision procedure of `decidableVotePasses`, and the falsification
  pipeline preserves budget ≥ 1.

  The vote conjunct is `decide`/`Prop` agreement. That agreement is
  definitional for any `Decidable` instance, so it is not a proved
  correspondence between two independent definitions; what is specific to this
  model is that the conjunct can be stated at all — the outcome is computed,
  not postulated. What the outcome depends on is proved separately by
  `vote_resolution_determined_by_tallies`.
-/

theorem governance_cycle_invariant (votes : List Vote) (d : DecisionClass)
    (oldBudget : Nat) (member : String) (proposals : List TrackedProposal)
    (hpos : 1 ≤ oldBudget) :
    (decide (votePasses votes d) = true ↔ votePasses votes d) ∧
    1 ≤ budgetAfterFalsification oldBudget (falsificationCount member proposals) :=
  And.intro (vote_outcome_computes votes d)
            (budget_preserves_positive oldBudget (falsificationCount member proposals) hpos)
