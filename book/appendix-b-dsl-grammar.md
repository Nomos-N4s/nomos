---
title: "Appendix B: Parliament configuration DSL grammar"
description: "EBNF grammar for the .parliament DSL that declaratively configures members, budgets, veto thresholds, contract bindings, and Speaker parameters."
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

---

## B.2 EBNF Grammar

```
(* Top-level configuration *)
parliament   = "parliament", "{", { member_def }, { contract_def },
               speaker_config, "}";

(* Member definitions *)
member_def   = "member", identifier, "{",
               "class", ":", string, ";",
               "budget", ":", integer, ";",
               "veto_threshold", ":", float, ";",
               "weight", ":", float, ";",
               "config", "{", { key_value }, "}", ";",
               "}";

(* Contract definitions *)
contract_def = "contract", identifier, "{",
               "restricted_indices", ":", "[", { integer }, "]", ";",
               "enactment_threshold", ":", float, ";",
               "revocation_threshold", ":", float, ";",
               "enforcement_mode", ":", ("soft" | "hard" | "constitutional"), ";",
               "}";

(* Speaker configuration *)
speaker_config = "speaker", "{",
                 "default_action", ":", string, ";",
                 "majority_threshold", ":", float, ";",
                 "supermajority_threshold", ":", float, ";",
                 "max_rounds", ":", integer, ";",
                 "}";

(* Primitives *)
identifier    = letter, { letter | digit | "_" };
string        = '"', { character }, '"';
integer       = digit, { digit };
float         = integer, ".", digit, { digit };
key_value     = identifier, ":", (string | integer | float);
letter        = "A" | ... | "Z" | "a" | ... | "z";
digit         = "0" | ... | "9";
character     = ? all printable ASCII ?;
```

---

## B.3 Semantic Constraints

1. Each member must have a unique `identifier`.
2. `budget` must be a positive integer (max proposals per cycle).
3. `veto_threshold` must be in `[0.0, 1.0]`.
4. `weight` must be in `[0.0, 1.0]`.
5. `enactment_threshold` and `revocation_threshold` must be in `[0.0, 1.0]`.
6. `restricted_indices` refers to action indices in the ontology.
7. `max_rounds` must be a positive integer.

---

## B.4 Example: GridWorld Parliament

```
parliament {
  member reward {
    class: "ExampleRewardMember";
    budget: 3;
    veto_threshold: 0.0;
    weight: 1.0;
    config { expected_reward_key: "expected_reward"; }
  }

  member safety {
    class: "ExampleSafetyMember";
    budget: 5;
    veto_threshold: 0.3;
    weight: 1.2;
    config { risk_threshold: 0.7; }
  }

  member integrity {
    class: "ExampleIntegrityMember";
    budget: 3;
    veto_threshold: 0.2;
    weight: 1.0;
    config { coherence_weight: 0.9; }
  }

  member planning {
    class: "ExamplePlanningMember";
    budget: 2;
    veto_threshold: 0.1;
    weight: 0.8;
    config { horizon: 10; }
  }

  contract poison_ban {
    restricted_indices: [2];
    enactment_threshold: 0.66;
    revocation_threshold: 1.0;
    enforcement_mode: "hard";
  }

  speaker {
    default_action: "emergency_shutdown";
    majority_threshold: 0.5;
    supermajority_threshold: 0.66;
    max_rounds: 3;
  }
}
```

---

## B.5 Reference Implementation

The DSL parser maps directly to `SpeakerStateMachine` construction:

```
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

## B.6 Grammar Summary

| Production | Description |
|-----------|-------------|
| `parliament` | Root config: members + contracts + speaker |
| `member_def` | Single committee member with budget, veto, weight |
| `contract_def` | Ulysses Contract with indices, thresholds, mode |
| `speaker_config` | Speaker state machine parameters |
