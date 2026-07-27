/-
  Budget Enforcement Invariant (κ₂)
  =================================
  From Chapter 3 (Ulysses Contracts):
  "No member may submit more proposals in a single governance cycle
   than their allocated budget."

  We prove this invariant holds for all possible governance cycles.
-/

/-- A member identifier. -/
abbrev MemberId : Type := String

/-- A proposal submitted by a member. -/
structure Proposal where
  member : MemberId
  action : String

/-- Tracks each member's budget and how many proposals they've used. -/
structure BudgetState where
  budgets : MemberId → Nat
  used : MemberId → Nat

/-- Budget enforcement invariant: no member has exceeded their budget. -/
def budgetEnforced (state : BudgetState) : Prop :=
  ∀ (m : MemberId), state.used m ≤ state.budgets m

/-- Initial state: zero proposals submitted by anyone. -/
def initialState (budgets : MemberId → Nat) : BudgetState :=
  { budgets := budgets, used := λ _ => 0 }

theorem initial_budget_enforced (budgets : MemberId → Nat) :
    budgetEnforced (initialState budgets) := by
  intro m
  simp [initialState]

/--
  Decision from processing a single proposal:
  - approved: budget allowed it, proposal accepted
  - budgetExhausted: member has no remaining budget
-/
inductive Decision : Type
  | approved
  | budgetExhausted

/--
  Process one proposal with κ₂ budget enforcement.
  If the member has remaining budget (used < budgets), accept and increment counter.
  Otherwise reject with budgetExhausted.
-/
def processProposal (state : BudgetState) (p : Proposal) : BudgetState × Decision :=
  if h : state.used p.member < state.budgets p.member then
    ({ state with used := λ m =>
      if m = p.member then state.used m + 1 else state.used m
    }, Decision.approved)
  else
    (state, Decision.budgetExhausted)

/-- Process a list of proposals sequentially. -/
def processCycle (state : BudgetState) (proposals : List Proposal) : BudgetState :=
  proposals.foldl (λ s p => (processProposal s p).1) state

/-- processProposal preserves the budget invariant. -/
theorem process_proposal_preserves_invariant (state : BudgetState) (p : Proposal)
    (h : budgetEnforced state) : budgetEnforced (processProposal state p).1 := by
  unfold processProposal
  by_cases hbudget : state.used p.member < state.budgets p.member
  · simp [hbudget]
    intro m
    by_cases hm : m = p.member
    · subst hm
      have hle : state.used p.member + 1 ≤ state.budgets p.member :=
        Nat.succ_le_of_lt hbudget
      simpa
    · simpa [hm] using h m
  · simp [hbudget]
    exact h

/-- Budget invariant holds across an entire governance cycle. -/
theorem budget_invariant_holds (state : BudgetState) (proposals : List Proposal)
    (h : budgetEnforced state) : budgetEnforced (processCycle state proposals) := by
  induction proposals generalizing state with
  | nil =>
      simpa [processCycle]
  | cons p ps ih =>
      have h1 : budgetEnforced (processProposal state p).1 :=
        process_proposal_preserves_invariant state p h
      have h2 : budgetEnforced (processCycle (processProposal state p).1 ps) :=
        ih (processProposal state p).1 h1
      simpa [processCycle]

/-- Corollary: from initial state, any proposal sequence respects budgets. -/
theorem budget_never_exceeded (budgets : MemberId → Nat) (proposals : List Proposal) :
    budgetEnforced (processCycle (initialState budgets) proposals) :=
  budget_invariant_holds (initialState budgets) proposals (initial_budget_enforced budgets)

/-- Example: Alice (budget 3) and Bob (budget 5). -/
def exampleBudgets : MemberId → Nat
  | "Alice" => 3
  | "Bob" => 5
  | _ => 0

example : budgetEnforced (processCycle (initialState exampleBudgets)
    [⟨"Alice", "move"⟩, ⟨"Alice", "pickup"⟩]) := by
  apply budget_never_exceeded

example : budgetEnforced (processCycle (initialState exampleBudgets)
    [⟨"Alice", "a1"⟩, ⟨"Alice", "a2"⟩, ⟨"Alice", "a3"⟩,
     ⟨"Alice", "a4"⟩, ⟨"Alice", "a5"⟩]) := by
  apply budget_never_exceeded

example : budgetEnforced (processCycle (initialState exampleBudgets)
    [⟨"Alice", "a1"⟩, ⟨"Bob", "b1"⟩, ⟨"Alice", "a2"⟩, ⟨"Bob", "b2"⟩,
     ⟨"Alice", "a3"⟩, ⟨"Bob", "b3"⟩, ⟨"Bob", "b4"⟩, ⟨"Bob", "b5"⟩]) := by
  apply budget_never_exceeded

example : budgetEnforced (processCycle (initialState exampleBudgets) []) := by
  apply budget_never_exceeded
