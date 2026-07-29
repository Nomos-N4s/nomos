---
title: "Appendix B: Parliament configuration DSL grammar"
description: "Indentation-based grammar for the .parliament DSL that declaratively configures members, budgets, veto thresholds, contract bindings, and Speaker parameters."
---

# Appendix B: DSL Grammar for Parliament Configuration

> *Formal grammar for defining Neural Parliament compositions, budgets, veto rules, and contract bindings.*

---

## B.1 Overview

The Parliament DSL allows declarative configuration of a `SpeakerStateMachine` instance without writing Python code. A `.parliament` file defines:

- Which members compose the Parliament
- Each member's budget allocation and veto threshold
- Contract registrations and enforcement modes
- Speaker parameters (thresholds, max rounds, default action)

The format is **indentation-based** (like Python): nesting level determines block structure. No braces, no semicolons.

---

## B.2 Grammar

```
parliament  = "parliament:" _NL
              { member_def } { contract_def } speaker_def

member_def  = "member", identifier, ":" _NL
              _INDENT "class:" _ value _NL
                      "budget:" _ integer _NL
                      "veto_threshold:" _ float _NL
                      "weight:" _ float _NL
                      [ "config:" _NL
                        _INDENT { key_value _NL } _DEDENT ]
              _DEDENT

contract_def = "contract", identifier, ":" _NL
               _INDENT "restricted_indices:" _ list _NL
                       "enactment_threshold:" _ float _NL
                       "revocation_threshold:" _ float _NL
                       "enforcement_mode:" _ ("soft" | "hard" | "constitutional") _NL
               _DEDENT

speaker_def = "speaker:" _NL
              _INDENT "default_action:" _ value _NL
                      "majority_threshold:" _ float _NL
                      "supermajority_threshold:" _ float _NL
                      "max_rounds:" _ integer _NL
              _DEDENT

key_value   = identifier ":" _ value
value       = string | integer | float | identifier
list        = "[" [ value { "," value } ] "]"
_INDENT     = increased indentation (2 spaces)
_DEDENT     = decreased indentation
_NL         = newline
_           = whitespace (ignored)
```

### Primitives

| Token | Matches | Example |
|-------|---------|---------|
| `identifier` | `[a-zA-Z_][a-zA-Z0-9_]*` | `reward`, `poison_ban` |
| `integer` | `-?[0-9]+` | `100`, `-1` |
| `float` | `-?[0-9]+\.[0-9]+` | `0.5`, `0.66` |
| `string` | `"..."` or `'...'` | `"RewardMember"` |
| `list` | `[item, ...]` | `[0, 1, 2]` |

Unquoted values matching integer or float patterns are parsed as numbers. All others are treated as strings.

---

## B.3 Semantic Constraints

1. Each member must have a unique `identifier`.
2. `budget` must be a positive integer (max proposals per cycle).
3. `veto_threshold` must be in `[0.0, 1.0]`.
4. `weight` must be in `[0.0, 1.0]`.
5. `enactment_threshold` and `revocation_threshold` must be in `[0.0, 1.0]`.
6. `restricted_indices` refers to action indices in the ontology.
7. `max_rounds` must be a positive integer.
8. Comments start with `#` and extend to end of line.

---

## B.4 Example: GridWorld Parliament

```python
parliament:
  member reward:
    class: RewardMember
    budget: 3
    veto_threshold: 0.0
    weight: 1.0
    config:
      expected_reward_key: expected_reward

  member safety:
    class: SafetyMember
    budget: 5
    veto_threshold: 0.3
    weight: 1.2
    config:
      risk_threshold: 0.7

  member integrity:
    class: IntegrityMember
    budget: 3
    veto_threshold: 0.2
    weight: 1.0
    config:
      coherence_weight: 0.9

  member planning:
    class: PlanningMember
    budget: 2
    veto_threshold: 0.1
    weight: 0.8
    config:
      horizon: 10

  contract poison_ban:
    restricted_indices: [2]
    enactment_threshold: 0.66
    revocation_threshold: 1.0
    enforcement_mode: hard

  speaker:
    default_action: emergency_shutdown
    majority_threshold: 0.5
    supermajority_threshold: 0.66
    max_rounds: 3
```

---

## B.5 Reference Implementation

The DSL parser (hand-written, no external dependencies) maps directly to `SpeakerStateMachine` construction:

```python
speaker = SpeakerStateMachine(
    members=members,
    default_action="emergency_shutdown",
    majority_threshold=0.5,
    supermajority_threshold=0.66,
    max_rounds=3,
)
```

Each member maps to a `ParliamentMember` subclass with its budget, veto threshold, and weight set from the config.

---

## B.6 Design Rationale

The format was designed to be **Pythonic**: indentation-delimited blocks, colon-separated key-value pairs, no braces or semicolons. This keeps `.parliament` files concise and familiar to Python developers while remaining language-agnostic.

Key design choices:

- **Indentation over braces**: Reduces visual noise, enforces consistent structure.
- **No semicolons**: Each field is its own line — natural, scannable.
- **Minimal quoting**: String values don't need quotes unless they contain special characters.
- **`#` for comments**: Familiar from Python, shell, and many config formats.

---

## B.7 Grammar Summary

| Production | Description |
|-----------|-------------|
| `parliament` | Root config: members + contracts + speaker |
| `member_def` | Single committee member with budget, veto, weight |
| `contract_def` | Ulysses Contract with indices, thresholds, mode |
| `speaker_def` | Speaker state machine parameters |
