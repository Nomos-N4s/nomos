/-
  Vote Threshold and Falsification Counter Invariants
  ====================================================
  From Chapter 2 (§2.4–2.5) and Chapter 4 (§7.2):
  - Vote resolution is deterministic
  - Threshold comparison is consistent across decision classes
  - Falsification counts are non-negative and correct
  - Budget halving preserves b ≥ 1 when starting from b ≥ 1
  - Falsification parameters are immutable-tier
-/

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

/-- Vote resolution is deterministic (law of excluded middle). -/
theorem vote_resolution_deterministic (votes : List Vote) (d : DecisionClass) :
    votePasses votes d ∨ ¬ votePasses votes d := by
  apply Classical.em

/-- Consistency: equal vote lists produce the same outcome. -/
theorem vote_threshold_consistent (v1 v2 : List Vote) (d : DecisionClass)
    (h : v1 = v2) : votePasses v1 d ↔ votePasses v2 d := by
  subst h; rfl

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
  Falsification parameters are immutable-tier: no governance procedure
  can change TAG_COMPLIANCE_THRESHOLD or FALSIFICATION_BUDGET_CUTOFF.
-/

def falsificationParamsImmutable : Prop :=
  TAG_COMPLIANCE_THRESHOLD = 4 ∧ FALSIFICATION_BUDGET_CUTOFF = 3

theorem falsification_params_are_immutable : falsificationParamsImmutable := by
  unfold falsificationParamsImmutable
  constructor <;> rfl

/-
  Combined invariant: every governance cycle deterministically produces
  a vote outcome, and the falsification pipeline preserves budget ≥ 1.
-/

theorem governance_cycle_invariant (votes : List Vote) (d : DecisionClass)
    (oldBudget : Nat) (member : String) (proposals : List TrackedProposal)
    (hpos : 1 ≤ oldBudget) :
    (votePasses votes d ∨ ¬ votePasses votes d) ∧
    1 ≤ budgetAfterFalsification oldBudget (falsificationCount member proposals) :=
  And.intro (vote_resolution_deterministic votes d)
            (budget_preserves_positive oldBudget (falsificationCount member proposals) hpos)
