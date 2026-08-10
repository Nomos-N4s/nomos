---
title: "Appendix C: core data types reference"
description: "Type signatures, field semantics, and invariants for the core dataclasses used by the Speaker, Parliament members, contracts, and identity components."
---

# Appendix C: Data Types Reference

> *Complete type signatures, field semantics, and invariants for all core dataclasses.*

---

## C.1 `PriorityTag`

File: `src/nomos/models.py:16`

Defines the five-tier priority hierarchy used for agenda sorting.

| Tag | Value | Name | Description |
|-----|-------|------|-------------|
| `CRITICAL_SAFETY` | 0 | Highest | Imminent harm prevention |
| `HIGH_IMPACT` | 1 | High | Significant long-term consequences |
| `ROUTINE` | 2 | Normal | Standard operational decisions |
| `EXPLORATORY` | 3 | Low | Experimental or curiosity-driven |
| `INFORMATIONAL` | 4 | Lowest | Logging, monitoring, queries |

**Invariant:** Proposals are sorted ascending by tag value, then by timestamp.

---

## C.2 `Action`

File: `src/nomos/models.py:41`

```python
@dataclass(frozen=True)
class Action:
    index: int
    properties: Dict[str, float] = {}
    runtime_hash: Optional[str] = None
```

| Field | Type | Constraints | Semantics |
|-------|------|-------------|-----------|
| `index` | `int` | Non-negative | Unique action identifier |
| `properties` | `Dict[str, float]` | Mutable default | Capability-specific metadata (speed, power, etc.) |
| `runtime_hash` | `Optional[str]` | SHA-256 hex | Integrity hash computed at binding time |

**Invariant:** `Action` is `frozen=True` — once constructed, its fields cannot be mutated.

---

## C.3 `Proposal`

File: `src/nomos/models.py:55`

```python
@dataclass
class Proposal:
    member_id: str
    action: Any
    tag: int = PriorityTag.ROUTINE
    timestamp: float = 0.0
    metadata: Dict[str, Any] = {}
```

| Field | Type | Default | Semantics |
|-------|------|---------|-----------|
| `member_id` | `str` | Required | Proposing member identifier |
| `action` | `Any` | Required | Action to execute |
| `tag` | `int` | `PriorityTag.ROUTINE` | Priority level for agenda sorting |
| `timestamp` | `float` | `0.0` | Unix timestamp (tiebreaker for agenda order) |
| `metadata` | `Dict[str, Any]` | `{}` | Arbitrary scoring context |

**Metadata conventions:**

| Key | Type | Used By |
|-----|------|---------|
| `expected_reward` | `float` | `ExampleRewardMember.evaluate_proposal()` |
| `risk` | `float` `[0,1]` | `ExampleSafetyMember.evaluate_proposal()` |
| `identity_coherence` | `float` `[0,1]` | `ExampleIntegrityMember.evaluate_proposal()` |
| `long_term_value` | `float` | `ExamplePlanningMember.evaluate_proposal()` |

---

## C.4 `GovernanceDecision`

File: `src/nomos/models.py:72`

```python
@dataclass
class GovernanceDecision:
    action: Any
    scores: Dict[str, float] = {}
    vetoed_by: List[str] = []
    governance_meta: Dict[str, Any] = {}
```

| Field | Type | Semantics |
|-------|------|-----------|
| `action` | `Any` | The selected action (or `None` for default) |
| `scores` | `Dict[str, float]` | Per-member evaluation scores for the winning proposal |
| `vetoed_by` | `List[str]` | Members who vetoed the winning proposal |
| `governance_meta` | `Dict[str, Any]` | Execution metadata (round number, falsification counts) |

**Computed property:**

```python
@property
def is_default(self) -> bool:
    return self.governance_meta.get("is_default", False)
```

**Invariant:** `governance_meta["is_default"]` is `True` iff no proposal reached consensus after `max_rounds`.

---

## C.5 `GovernanceContext`

File: `src/nomos/models.py:91`

```python
@dataclass
class GovernanceContext:
    active_contracts: List[Any] = []
    recent_history: List[GovernanceDecision] = []
    member_statuses: Dict[str, Dict[str, Any]] = {}
    identity_vector: Optional[List[float]] = None
    ontology: Optional[Any] = None
```

| Field | Type | Semantics |
|-------|------|-----------|
| `active_contracts` | `List[UlyssesContract]` | Currently enacted contracts |
| `recent_history` | `List[GovernanceDecision]` | Last N decisions for context |
| `member_statuses` | `Dict` | Per-member runtime state (budget, falsification count) |
| `identity_vector` | `Optional[List[float]]` | Identity Layer embedding |
| `ontology` | `Optional[Any]` | Ontology graph reference |

---

## C.6 `UlyssesContract`

File: `src/nomos/contracts/contract.py`

```python
@dataclass
class UlyssesContract:
    contract_id: str
    restricted_indices: Set[int]
    enactment_threshold: float = 0.66
    revocation_threshold: float = 1.0
    is_active: bool = False
```

| Field | Type | Constraints | Semantics |
|-------|------|-------------|-----------|
| `contract_id` | `str` | Unique | Contract identifier |
| `restricted_indices` | `Set[int]` | Non-empty | Action indices the contract constrains |
| `enactment_threshold` | `float` | `[0, 1]` | Supermajority required to enact |
| `revocation_threshold` | `float` | `[0, 1]` | Supermajority required to revoke |
| `is_active` | `bool` | — | Whether the contract is currently enforced |

**Lifecycle:** `Created -> Enacted (is_active=True) -> Expired/Revoked -> Removed`

---

## C.7 `IdentityClaim`

File: `src/nomos/identity/core.py`

```python
@dataclass
class CoreCommitment:
    commitment_type: CommitmentType
    statement: str
    threshold: CommitmentThreshold
    enforcement_mode: EnforcementMode
    affected_action_indices: List[int]
```

| Field | Type | Semantics |
|-------|------|-----------|
| `commitment_type` | `CommitmentType` | `VALUE_PRINCIPLE`, `BEHAVIORAL_RULE`, `PURPOSE_BOUNDARY` |
| `statement` | `str` | Human-readable commitment description |
| `threshold` | `CommitmentThreshold` | `SIMPLE_MAJORITY`, `SUPERMAJORITY`, `UNANIMITY` |
| `enforcement_mode` | `EnforcementMode` | `INTEGRITY_VETO`, `CONTRACT_BINDING`, `CONSTITUTIONAL` |
| `affected_action_indices` | `List[int]` | Which actions this commitment constrains |

---

## C.8 `MutabilityTier`

File: `src/nomos/identity/tiers.py`

| Tier | Name | Modifiable By | Examples |
|------|------|--------------|----------|
| 0 | **Immutable** | No one (hardware fuses) | Genesis identity, constitutional contracts |
| 1 | **Constitutional** | Unanimous consensus | Core commitments |
| 2 | **Governed** | Supermajority vote | Operational parameters, contract registrations |
| 3 | **Mutable** | Simple majority | Temporary extensions, experimental features |

---

## C.9 `ExperimentReport`

File: `src/nomos/experiments/metrics.py:12`

```python
@dataclass
class ExperimentReport:
    name: str
    total_steps: int
    total_reward: float
    avg_reward_per_step: float
    deadlock_count: int
    deadlock_rate: float
    constraint_violations: int
    veto_count: int
    final_identity_drift: float
    governance_latency_avg: float
    metadata: Dict[str, Any] = {}
```

**Derived fields:**

- `avg_reward_per_step = total_reward / max(total_steps, 1)`
- `deadlock_rate = deadlock_count / max(total_steps, 1)`
