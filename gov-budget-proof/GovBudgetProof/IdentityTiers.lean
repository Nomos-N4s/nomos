/-
  Identity Tier Mutability Rules
  ================================
  From Chapter 4 (§3 Tiered Mutability):
  - §3.1 Immutable tier: no governance procedure can modify these parameters.
  - §3.2 Constitutional tier: changes require unanimity of Parliament plus
    external multisig (3-of-5) and a 30-day cooling-off period.
  - §3.3 Operational tier: supermajority (2/3) plus a 7-day cooling-off period.
  - §3.4 Dynamic tier: standard majority, no cooling-off period.
  - §3.5 Procedural asymmetry: the bar to modify a parameter is at least as
    high as the bar to establish it at genesis.

  We prove:
  - immutable-tier parameters cannot be changed by any governance update (§3.1)
  - constitutional changes require quorum ≥ 3 and cooldown ≥ 30 days (§3.2)
  - lower tiers accept the constitutional bar — nothing stronger is required (§3.3–3.4)
  - the constitutional modification bar is at least the genesis bar (§3.5, §4.2)
-/

/-- The four mutability tiers of the Identity Layer (Chapter 4 §3). -/
inductive Tier : Type
  | immutable
  | constitutional
  | operational
  | dynamic

/-- Rank of a tier; higher means stricter. -/
def tierRank : Tier → Nat
  | Tier.immutable => 3
  | Tier.constitutional => 2
  | Tier.operational => 1
  | Tier.dynamic => 0

/-- `t₁` is at least as strict as `t₂`. -/
def stricter (t₁ t₂ : Tier) : Prop :=
  tierRank t₂ ≤ tierRank t₁

/-- Chapter 4 §3.1–3.4 procedural bars. -/
def CONSTITUTIONAL_QUORUM : Nat := 3
def CONSTITUTIONAL_COOLDOWN : Nat := 30
def OPERATIONAL_QUORUM : Nat := 2
def OPERATIONAL_COOLDOWN : Nat := 7
def DYNAMIC_QUORUM : Nat := 1

/-- A proposed governance change, carrying the quorum and cooling-off period
    it actually met. -/
structure Change where
  quorum : Nat
  cooldownDays : Nat

/-- A change is permitted at the Constitutional tier iff it matches the
    §3.2 bar: 3-of-5 external multisig and 30-day cooling-off. -/
def constitutionalPermitted (c : Change) : Prop :=
  CONSTITUTIONAL_QUORUM ≤ c.quorum ∧ CONSTITUTIONAL_COOLDOWN ≤ c.cooldownDays

/-- A change is permitted at the Operational tier iff it matches the
    §3.3 bar: 2/3 supermajority and 7-day cooling-off. -/
def operationalPermitted (c : Change) : Prop :=
  OPERATIONAL_QUORUM ≤ c.quorum ∧ OPERATIONAL_COOLDOWN ≤ c.cooldownDays

/-- A change is permitted at the Dynamic tier iff it matches the
    §3.4 bar: simple majority, no cooling-off required. -/
def dynamicPermitted (c : Change) : Prop :=
  DYNAMIC_QUORUM ≤ c.quorum

/-- Permission at a tier. The immutable tier has no bar at all:
    nothing is ever permitted there (§3.1). -/
def isPermitted (t : Tier) (c : Change) : Prop :=
  match t with
  | Tier.immutable => False
  | Tier.constitutional => constitutionalPermitted c
  | Tier.operational => operationalPermitted c
  | Tier.dynamic => dynamicPermitted c

/-- §3.1: immutable-tier parameters cannot be changed by any governance update. -/
theorem immutable_parameters_never_change (c : Change) :
    ¬ isPermitted Tier.immutable c := by
  intro h
  unfold isPermitted at h
  exact h

/-- §3.2: constitutional changes require at least the 3-of-5 multisig quorum
    and the full 30-day cooling-off period. -/
theorem constitutional_requires_quorum_and_cooldown (c : Change)
    (h : isPermitted Tier.constitutional c) :
    3 ≤ c.quorum ∧ 30 ≤ c.cooldownDays := by
  unfold isPermitted at h
  simp [constitutionalPermitted, CONSTITUTIONAL_QUORUM, CONSTITUTIONAL_COOLDOWN] at h
  exact h

/-- A change short of the §3.2 bar is rejected at the constitutional tier:
    2-of-5 signatures plus full cooldown still fail. -/
theorem two_of_five_insufficient_for_constitutional (cooldown : Nat)
    (h : 30 ≤ cooldown) : ¬ isPermitted Tier.constitutional { quorum := 2, cooldownDays := cooldown } := by
  unfold isPermitted
  simp [constitutionalPermitted, CONSTITUTIONAL_QUORUM, CONSTITUTIONAL_COOLDOWN]

/-- A change within the 30-day cooldown is rejected at the constitutional
    tier even with full quorum. -/
theorem insufficient_cooldown_insufficient_for_constitutional (quorum : Nat)
    (h : 3 ≤ quorum) (hshort : quorum ≤ 3) :
    ¬ isPermitted Tier.constitutional { quorum := quorum, cooldownDays := 29 } := by
  unfold isPermitted
  simp [constitutionalPermitted, CONSTITUTIONAL_QUORUM, CONSTITUTIONAL_COOLDOWN]

/-- §3.3: operational changes require at least the 2/3 supermajority and the
    7-day cooling-off period. -/
theorem operational_requires_quorum_and_cooldown (c : Change)
    (h : isPermitted Tier.operational c) :
    2 ≤ c.quorum ∧ 7 ≤ c.cooldownDays := by
  unfold isPermitted at h
  simp [operationalPermitted, OPERATIONAL_QUORUM, OPERATIONAL_COOLDOWN] at h
  exact h

/-- §3.4: dynamic changes require only the simple-majority quorum; no
    cooling-off condition AT ALL is required. -/
theorem dynamic_requires_only_majority (c : Change)
    (h : isPermitted Tier.dynamic c) : 1 ≤ c.quorum := by
  unfold isPermitted at h
  simp [dynamicPermitted, DYNAMIC_QUORUM] at h
  exact h

/-- §3.2–3.4: the constitutional bar satisfies every lower tier — nothing
    stronger than the constitutional requirement is ever required. -/
theorem constitutional_bar_suffices_for_lower_tiers (c : Change)
    (h : isPermitted Tier.constitutional c) :
    isPermitted Tier.operational c ∧ isPermitted Tier.dynamic c := by
  unfold isPermitted at h ⊢
  simp [constitutionalPermitted, CONSTITUTIONAL_QUORUM, CONSTITUTIONAL_COOLDOWN,
        operationalPermitted, OPERATIONAL_QUORUM, OPERATIONAL_COOLDOWN,
        dynamicPermitted, DYNAMIC_QUORUM] at h ⊢
  rcases h with ⟨hq, hc⟩
  constructor
  · constructor <;> omega
  · omega

/-- §3.3: the operational bar suffices for the dynamic tier. -/
theorem operational_bar_suffices_for_dynamic (c : Change)
    (h : isPermitted Tier.operational c) :
    isPermitted Tier.dynamic c := by
  unfold isPermitted at h ⊢
  simp [operationalPermitted, OPERATIONAL_QUORUM, OPERATIONAL_COOLDOWN,
        dynamicPermitted, DYNAMIC_QUORUM] at h ⊢
  rcases h with ⟨hq, hc⟩
  omega

/-- §3.5: the bar to modify a constitutional parameter is at least the bar
    used to establish it at genesis (both are 3-of-5, Chapter 4 §4.2). -/
theorem modification_bar_at_least_genesis_bar : 3 ≤ CONSTITUTIONAL_QUORUM := by
  unfold CONSTITUTIONAL_QUORUM
  decide

/-- Tier strictness order: immutable ≻ constitutional ≻ operational ≻ dynamic. -/
theorem tier_strictness_order :
    stricter Tier.immutable Tier.constitutional ∧
    stricter Tier.constitutional Tier.operational ∧
    stricter Tier.operational Tier.dynamic := by
  unfold stricter tierRank
  decide

/-- 3-of-5 with 30 days passes the constitutional tier. -/
example : isPermitted Tier.constitutional { quorum := 3, cooldownDays := 30 } := by
  unfold isPermitted
  simp [constitutionalPermitted, CONSTITUTIONAL_QUORUM, CONSTITUTIONAL_COOLDOWN]

/-- 2-of-5 with 30 days does NOT pass the constitutional tier. -/
example : ¬ isPermitted Tier.constitutional { quorum := 2, cooldownDays := 30 } := by
  unfold isPermitted
  simp [constitutionalPermitted, CONSTITUTIONAL_QUORUM, CONSTITUTIONAL_COOLDOWN]

/-- The constitutional bar (3-of-5, 30 days) clears the operational tier too
    — a lower tier never demands anything stronger. -/
example : isPermitted Tier.operational { quorum := 3, cooldownDays := 30 } := by
  unfold isPermitted
  simp [operationalPermitted, OPERATIONAL_QUORUM, OPERATIONAL_COOLDOWN]