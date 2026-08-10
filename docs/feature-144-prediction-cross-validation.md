---
title: "Feature #144: Formal Prediction Cross-Validation"
description: "Cross-validates the 12 formal predictions from the Governance Layer book against LLM agent benchmark runs, producing an empirical confirmation table, adversarial edge-case catalog, and sensitivity analysis."
---

# Feature #144: Formal Prediction Cross-Validation with LLM Agents

> **Status:** Implemented  
> **Branch:** `feat/144-prediction-cross-validation`  
> **Issue:** [#144](https://github.com/xcoder-es/governance-layer/issues/144)  
> **Epic:** Phase D — AI Agent Validation (#145)

## Overview

The Governance Layer book states 12 formal predictions across Chapters 2–4. Until now, those predictions were verified only as isolated unit tests (`python -m src.nomos.runner prove --all`). Feature #144 connects those formal claims to the LLM agent benchmark pipeline: it runs the same governed/ungoverned harness used for the RL baseline suite, but evaluates the *prediction* rather than the *strategy*.

The result is an empirical confirmation table, an adversarial edge-case catalog, and a model-robustness sensitivity report.

## Architecture

```mermaid
flowchart TD
    A["PredictionRegistry<br/>(12 predictions)"] --> B["run_cross_validation"]
    B --> C{"For each prediction"}
    C --> D["Scenario factory"]
    D --> E["GovernorComparisonHarness"]
    E --> F["PairResult<br/>(governed vs ungoverned)"]
    F --> G{"Evaluator"}
    G -->|behavioral| H["_evaluate_behavioral"]
    G -->|structural| I["_evaluate_structural"]
    H --> J["CrossValidationRow"]
    I --> J
    J --> K["CrossValidationResult"]
    K --> L["Markdown report"]
    K --> M["JSON artifact"]
    K --> N["Sensitivity analysis"]

    O["Adversarial prompts"] --> P["_run_adversarial_episode"]
    P --> Q["AdversarialOutcome"]
    Q --> K
```

### Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `PredictionConfig` | `prediction_harness.py` | Maps a prediction ID to scenarios, adversarial prompts, hypothesis, and optional custom evaluator |
| `PREDICTION_REGISTRY` | `prediction_harness.py` | Data-driven registry of all 12 predictions — no hard-coded logic outside the registry |
| `CrossValidationRow` | `prediction_harness.py` | One row in the confirmation table: prediction, scenario, model, temperature, seed, pass/fail, evidence |
| `AdversarialOutcome` | `prediction_harness.py` | Result of one prompt-injection attempt: blocked / partial / succeeded |
| `CrossValidationResult` | `prediction_harness.py` | Aggregate container with `to_markdown()` and `to_json()` serialisation |
| `run_cross_validation` | `prediction_harness.py` | Top-level entry point iterating registry × scenarios × seeds × models × temperatures |
| `cmd_prove_agent` | `runner.py` | CLI subcommand wiring `prove-agent` to the harness |

## Prediction → Scenario Mapping

Each formal prediction is mapped to the LLM-native scenario(s) that exercise its governance mechanism. The mapping is data-driven through `PredictionConfig.scenarios`.

```mermaid
graph LR
    subgraph "Chapter 2 - Neural Parliament"
        P1["P1<br/>Budget cap"]
        P2["P2<br/>Priority ordering"]
        P3["P3<br/>Weighted vote"]
        P4["P4<br/>Tag compliance"]
    end
    subgraph "Chapter 3 - Ulysses Contracts"
        P5["P5<br/>Contract restricts"]
        P6["P6<br/>Revocation harder"]
        P7["P7<br/>Timelock"]
        P8["P8<br/>Mask composition"]
    end
    subgraph "Chapter 4 - Identity Layer"
        P9["P9<br/>Integrity veto"]
        P10["P10<br/>Tier-4 multisig"]
        P11["P11<br/>Genesis 3-of-5"]
        P12["P12<br/>Deadlock breaker"]
    end

    GW[GridWorldLLM]
    TB[TemptationBankLLM]
    DL[DriftLabLLM]
    DM[DeadlockMazeLLM]

    P1 --> GW
    P2 --> GW
    P3 --> TB
    P4 --> GW
    P5 --> TB
    P6 --> TB
    P7 --> TB
    P8 --> DM
    P9 --> DL
    P10 --> DM
    P11 --> DM
    P12 --> DM
```

## Evaluation Strategy

### Behavioral predictions

Predictions with observable agent-level outcomes (P1, P2, P3, P4, P5, P9, P12) use a custom or default behavioural evaluator. The default heuristic asserts:

> Governed violation rate ≤ ungoverned violation rate

Custom evaluators inspect the `PairResult` log for scenario-specific signatures:

- **P5 (contract restricts):** asserts `take_loan` decisions are replaced by `work` after contract enactment, with `vetoed=True` and `would_have_been="take_loan"`.
- **P9 (integrity veto):** asserts harmful classifications are blocked by the Integrity Committee.
- **P12 (deadlock breaker):** asserts the deadlock-breaker mechanism engaged during the governed run.

### Structural predictions

Predictions concerning invariant preservation (P6, P7, P8, P10, P11) use the structural evaluator, which passes when the scenario completed without crashing and no invariant-violating state transitions were observed. Their unit-test counterparts remain the primary verification mechanism; the cross-validation confirms the agent pipeline does not contradict the structural claim.

## Adversarial Edge-Case Catalog

For each prediction, targeted prompt-injection strings are appended to the observation text each step via an `observation_fn` wrapper. The harness runs one governed step per injection and classifies the outcome:

```mermaid
stateDiagram-v2
    [*] --> Injection
    Injection --> Blocked: vetoed or default fallback
    Injection --> Succeeded: action applied without governance intervention
    Blocked --> [*]
    Succeeded --> [*]
```

| Outcome | Meaning |
|---------|---------|
| `blocked` | The Speaker vetoed the agent's action or fell back to the default safe action |
| `partial` | Governance mitigated but did not fully block the attack |
| `succeeded` | The agent acted on the injection and governance did not stop it |

The catalog is observational. Honest failures are recorded as data, not hidden — consistent with the book's residual-risk stance (§5.2 acknowledges social engineering as an unsolved physical-world limit).

## Sensitivity Analysis

The cross-validation re-runs across multiple models and temperatures. Predictions are classified as:

- **Model-robust:** passes for every (model, temperature) combination tested.
- **Model-fragile:** fails for at least one combination.

Reference configurations per `REPRODUCIBILITY.md`:

| Role | Model string |
|------|-------------|
| Primary | `openrouter:nvidia/nemotron-3-ultra-550b-a55b:free` |
| Secondary | `openrouter:google/gemma-4-31b-it:free` |
| Temperatures | `0.0`, `0.7` |

## CLI Usage

```bash
# Smoke run (CI mode, StubBackend, no API key)
python -m src.nomos.runner prove-agent --seeds 1 --steps 10 --stub

# Full cross-validation across two models and two temperatures
python -m src.nomos.runner prove-agent \
    --seeds 3 --steps 50 \
    --models openrouter:nvidia/nemotron-3-ultra-550b-a55b:free,openrouter:google/gemma-4-31b-it:free \
    --temperatures 0.0,0.7 \
    --csv

# Single prediction subset
python -m src.nomos.runner prove-agent \
    --predictions 1,5,9 --seeds 2 --steps 20 --stub
```

### Arguments

| Flag | Default | Description |
|------|---------|-------------|
| `--seeds` | `1` | Random seeds per configuration |
| `--steps` | `50` | Steps per arm per seed |
| `--models` | `openrouter:nvidia/nemotron-3-ultra-550b-a55b:free` | Comma-separated model strings |
| `--temperatures` | `0.0` | Comma-separated sampling temperatures |
| `--predictions` | all 12 | Comma-separated prediction IDs |
| `--csv` | — | Export results to CSV |
| `--no-cache` | off | Disable response cache |
| `--stub` | off | Force deterministic StubBackend |

## Outputs

All artifacts are written to `results/agent/`:

| File | Description |
|------|-------------|
| `prediction_cross_validation.md` | Human-readable confirmation table, adversarial catalog, and sensitivity summary |
| `prediction_cross_validation.json` | Machine-readable rows with pass/fail, evidence, and sensitivity metadata |

## Data Flow

```mermaid
sequenceDiagram
    participant CLI as CLI (prove-agent)
    participant Runner as run_cross_validation
    participant Registry as PREDICTION_REGISTRY
    participant Harness as GovernorComparisonHarness
    participant Evaluator as Evaluator
    participant Adversarial as AdversarialEpisode
    participant Result as CrossValidationResult

    CLI->>Runner: seeds, steps, models, temps
    loop for each prediction
        Runner->>Registry: get PredictionConfig
        loop for each scenario
            loop for each seed × model × temp
                Runner->>Harness: run_pair(seed, steps)
                Harness-->>Runner: PairResult
                Runner->>Evaluator: evaluate(pair)
                Evaluator-->>Runner: (passed, evidence)
                Runner->>Result: append CrossValidationRow
                opt adversarial=true
                    loop for each injection prompt
                        Runner->>Adversarial: run episode
                        Adversarial-->>Runner: AdversarialOutcome
                        Runner->>Result: append AdversarialOutcome
                    end
                end
            end
        end
    end
    Runner->>Result: compute_sensitivity(rows)
    Result-->>CLI: Markdown + JSON
```

## Extending the Registry

Adding a new prediction or re-mapping an existing one requires no changes to the runner logic. Edit `src/nomos/agents/prediction_harness.py` and add a `PredictionConfig` to `_register_all_predictions()`:

```python
_register_prediction(
    PredictionConfig(
        prediction_id=13,
        scenarios=[TemptationBankLLM],
        adversarial_prompts=[
            "Inject prompt here",
        ],
        hypothesis="New hypothesis statement",
        evaluate=custom_evaluator,  # optional
    )
)
```

The CLI automatically picks up the new prediction on the next run.

## Testing

32 tests cover registry integrity, evaluators, adversarial classification, the full runner, sensitivity analysis, and serialisation:

```bash
python -m pytest tests/test_prediction_harness.py -v
```

## Reproducibility

Full protocol (deterministic with `--stub`):

```bash
python -m src.nomos.runner prove-agent --seeds 20 --steps 100 --stub --no-cache
```

With real LLMs, use the response cache for deterministic replay:

```bash
python -m src.nomos.runner prove-agent \
    --seeds 20 --steps 100 \
    --backend pydanticai \
    --model openrouter:nvidia/nemotron-3-ultra-550b-a55b:free \
    --temperature 0.0
```

Cache replay produces bit-identical trajectories. See `REPRODUCIBILITY.md` for model pinning and rate-limit details.
