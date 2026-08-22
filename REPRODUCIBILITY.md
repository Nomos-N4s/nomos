# Reproducibility Protocol

All benchmark results in the Nomos reference implementation
are fully reproducible. This document specifies the exact procedure.

## Quick Start (Containerized)

```bash
make reproduce
```

This builds the Docker image and runs the full benchmark suite inside
a container, eliminating environment differences.

## Manual Reproduction

### Requirements

- **OS**: Linux, macOS, or Windows (WSL2 recommended on Windows)
- **CPU**: Any x86-64 or ARM64 processor (no GPU required)
- **Python**: 3.10 or later
- **RAM**: 512 MB minimum
- **Disk**: 100 MB for results

### Steps

```bash
# 1. Clone and install
git clone https://github.com/Nomos-N4s/nomos.git
cd nomos
pip install -e .

# 2. Run the full benchmark suite
python -m src.nomos.runner all --baselines --steps 1000 --seeds 20
```

### Expected Runtime

- **Reference hardware** (single core, 2.5 GHz): ~6 seconds wall-clock
- All 380 runs (19 scenario-strategy combinations × 20 seeds × 1,000
  steps) complete in under 10 seconds on any modern CPU.

### Seed Strategy

Seeds 0-19 are run for every scenario-strategy combination (19
combinations × 20 seeds = 380 individual experiment runs). Four scenarios
× five strategies is 20 combinations; GridWorld has no `static_masking`
arm, for the reason given below the results table. Every run is
deterministic given its seed — the same seed always produces identical
results — so the table below reproduces exactly, not approximately.

**The seed does not move every cell, because most cells hold nothing for
it to move.** Two components consume it:

- The **scenario**, when it declares `ExperimentScenario.SEEDED`. GridWorld
  is the only one that does: its `reset()` rolls walls, poison and apples
  per tile, so each seed is a different grid.
- The **`random` strategy**, whose `RandomBaseline` draws its choice from
  the seed.

TemptationBank, DriftLab and DeadlockMaze hold no RNG at all — their
agendas, rewards and timers are constants. That is deliberate rather than
an oversight. Each exists to demonstrate one mechanism (a Ulysses Contract
binding, identity coherence holding under a drifting reward function, a
deadlock breaker firing), and injecting noise would change what is being
demonstrated instead of strengthening it. They are documented as
deterministic rather than advertised as replicated.

So GridWorld's four arms, plus the `random` arm on TemptationBank and on
DriftLab, draw a fresh sample per seed. Every other combination returns
the same number twenty times — including DeadlockMaze's `random` arm,
because that scenario proposes exactly one action and a random chooser has
nothing to choose between. For those cells `std_reward` is 0.0 and the
bootstrap interval sits on the mean, since there is nothing to resample.
Read them as exact values, not as twenty samples that happened to agree.

Until #301 the loop seed was written into each report's metadata and
handed to no scenario at all, while GridWorld's constructor kwargs pinned
it to 42. Every cell but two therefore published a standard deviation,
bootstrap interval and `n` taken over twenty repeats of a single run.
The exceptions are the `random` arms on TemptationBank and DriftLab: the
baseline drew from the loop seed then exactly as it does now, so those
two were genuine 20-draw statistics, and the table below republishes
their figures unchanged by the fix.

## Output

| File | Description |
|---|---|
| `results/benchmark_results.json` | Raw per-run data (reward, violations, deadlocks) |
| `results/benchmark_summary.csv` | Aggregated means, stds, and 95% bootstrap CIs |
| `results/figures/reward_curves.svg` | Reward curves across all 4 scenarios |
| `results/figures/violation_rates.svg` | Constraint violation rates by strategy |
| `results/figures/deadlock_frequency.svg` | Deadlock counts (DeadlockMaze scenario) |
| `results/figures/pareto_frontier.svg` | Reward vs. violations Pareto frontier |
| `results/agent/agent_report.md` | Agent validation human-readable summary |
| `results/agent/agent_benchmark_results.json` | Per-pair and aggregate agent metrics |
| `results/agent/agent_benchmark_summary.csv` | One row per agent seed pair |
| `results/agent/cache_manifest.json` | SHA-256 digests of every cache entry |

## Verifying Results

Compare your `results/benchmark_summary.csv` against the published
table below. Mean rewards should match within ±0.1.

The identity-drift figure in the DriftLab column is the one exception:
`export_summary_csv` writes no drift column, and neither does
`benchmark_results.json`. `final_identity_drift` is a per-run field, so
verify it from the `Identity drift:` line the runner prints for each run
(see [DriftLab Identity Drift](#driftlab-identity-drift) below).

| Strategy | GridWorld | TemptationBank | DriftLab | DeadlockMaze |
|---|---|---|---|---|
| Governance | 0.65 ± 0.88 reward, 0 violations | 1998.0 reward, 0 violations | 1000.0 reward, 0 violations, 0.0 drift | 0.0 reward, 999 deadlocks |
| MonolithicRL | -22.45 ± 12.50 reward, 5.25 violations | -4865.0 reward, 1000 violations | 4249.25 reward, 1000 violations, 0.1647 drift | 0.0 reward, 0 deadlocks |
| Random | -34.90 ± 14.99 reward, 8.65 violations | 1990.30 ± 11.78 reward, 1.1 violations | 2621.41 ± 45.98 reward, 499.35 violations, 0.0777 drift | 0.0 reward, 0 deadlocks |
| StaticMasking | not applicable | 2000.0 reward, 0 violations | 1000.0 reward, 0 violations, 0.0 drift | 0.0 reward, 1000 deadlocks (total inaction — see below) |
| VetoOnly | 0.65 ± 0.88 reward, 0 violations | 2000.0 reward, 0 violations | 1000.0 reward, 0 violations, 0.0 drift | 0.0 reward, 0 deadlocks |

Every entry is a mean over the 20 seeds. `±` is the standard deviation
across seeds and is shown only where it is not zero; the cells without one
are the deterministic combinations described under [Seed
Strategy](#seed-strategy), where the mean is a single exact value. Reward
and violation figures come from `results/benchmark_summary.csv`; the drift
column comes from the DriftLab command in [DriftLab Identity
Drift](#driftlab-identity-drift) below, run at `--seeds 20`, because the
CSV carries no drift column.

The CSV also carries a 95% bootstrap interval per cell (10,000 resamples
from a `random.Random(42)`, so it is reproducible). Only the six sampling
combinations have an interval wider than a point: GridWorld Governance
[0.30, 1.05], MonolithicRL [-27.80, -17.10], Random [-41.20, -28.40] and
VetoOnly [0.30, 1.05]; TemptationBank Random [1984.70, 1994.50]; DriftLab
Random [2602.22, 2641.92]. For the other thirteen the interval is the mean
twice over, because resampling twenty copies of one number returns that
number.

GridWorld's `governance` and `veto_only` arms return identical rewards on
every seed, which is why those two cells match. They part company on
deadlocks — steps where no proposal cleared the vote and the Speaker's
default was returned. Across the 20 grids `governance` records 0 deadlocks
on 10 seeds and 993-1,000 on the other 10 (mean 498.3), while `veto_only`
records 0 on 19 seeds and 1,000 on seed 4 (mean 50.0). The single grid the
suite ran before #301, seed 42, was one of the quiet ones: 3.0 reward and
no deadlocks at all under governance. Half of GridWorld's seeds gridlock
the Parliament, and the old table could not show it.

StaticMasking is not run on GridWorld. The scenario declares no static
blocklist (Appendix D.4): its actions are bare directions and the poison is
in the target tile, so no fixed set of action names expresses the
constraint. With an empty blocklist the arm would reproduce MonolithicRL's
numbers under a second name, so the runner omits it.

StaticMasking's DeadlockMaze cell does not measure the same thing as
Governance's neighbouring 999. `tighten_quorum` is the only action the
scenario ever proposes, and it is the one action the blocklist forbids, so
the arm selects nothing on all 1,000 steps. `deadlock_count` counts default
(no-decision) outcomes, so the 1,000 is total inaction: the quorum is never
tightened and the gridlock the scenario studies never occurs. Governance's
999 is genuine gridlock. The arm is kept because a blanket ban is a real
ablation result for a single-action scenario, but it is not comparable
step-for-step with the rows above it.

### DriftLab Identity Drift

DriftLab's `final_identity_drift` used to be 0.0 for every strategy by
construction, and its reward 0.0 by construction — the identity vector was
a constant list that nothing in the run could move, and the step reward was
hard-coded. Both are now live signals, so the Governance row's 0.0 drift is
earned rather than structural: the honest proposal is tagged `HIGH_IMPACT`
and the harmful one `ROUTINE`, so agenda ordering puts the honest action to
the vote first and it passes — the harmful proposal is never reached, and
`veto_count` is 0 across all 1,000 steps. Nothing degrades a commitment
because nothing violates one.

The Identity Layer is not the mechanism doing the blocking here. Scored
directly, the harmful action's Integrity value stays above that member's
0.8 veto threshold until drift passes 0.222; below that it is Safety
(0.2) and Planning (-0.5) that would veto it.

Measured with the DriftLab scenario alone, at two seeds rather than the 20
the table above calls for:

```bash
python -m src.nomos.runner drift --baselines --steps 1000 --seeds 2
```

`--baselines` is what selects all five strategies. Driven from Python,
`run_drift_experiments(steps=1000, seeds=2)` defaults to
`strategies=["governance"]` and emits the Governance row only, so the
strategy list has to be passed explicitly:
`run_drift_experiments(steps=1000, seeds=2, strategies=["governance",
"monolithic_rl", "random", "static_masking", "veto_only"])`.

| Strategy | Reward | Violations | Identity drift |
|---|---|---|---|
| Governance | 1000.0 | 0 | 0.0 |
| VetoOnly | 1000.0 | 0 | 0.0 |
| Random | 2639.4 / 2584.5 | 503 / 485 | 0.0785 / 0.0746 |
| MonolithicRL | 4249.25 | 1000 | 0.1647 |
| StaticMasking | 1000.0 | 0 | 0.0 |

StaticMasking matches Governance here rather than MonolithicRL because
DriftLab declares `classify_harmful_as_safe` in its static blocklist, so the
arm never executes the violating action. Before per-scenario blocklists it
ran with an empty set and reproduced MonolithicRL's row exactly, which is
the defect that made this arm meaningless.

DriftLab holds no RNG and the governed path is deterministic, so every
strategy except Random reports identical values on both seeds; Random is
given per seed. At `--seeds 20` the deterministic rows are unchanged and
Random's mean reward is 2621.41 with mean drift 0.0777 (per-seed drift
ranges 0.0713 to 0.0852), which is the DriftLab column of the table
above. Drift is a function of how many commitment violations a
strategy actually executed, which is why Random lands between the fully
compliant and fully adversarial strategies.

## Formal Predictions

```bash
# Run the 12 prediction tests over src/nomos/
python -m src.nomos.runner prove --all
```

Expected output: `12/12 PASS`, under the banner `Formal Prediction Tests
(Python)` and above a footer repeating that no Lean proof is checked by the
run. The predictions are Python asserts; this command invokes no Lean
toolchain and compiles nothing in `gov-budget-proof/`. Which of them have a
theorem of the Lean model behind them, and which have no counterpart there at
all, is in
[Prediction coverage](book/formal-verification-lean.md#prediction-coverage).

## Agent Benchmark (LLM) Protocol

The governed/ungoverned LLM agent validation run follows its own
reproducibility protocol. LLM sampling is non-deterministic by nature;
this protocol makes full runs reproducible through **deterministic
prompt rendering**, **temperature 0**, and a **content-addressed
response cache**.

### Quick smoke run (CI, no API key)

```bash
python -m src.nomos.runner agent --seeds 1 --steps 30 --backend stub
```

The stub backend is deterministic and exercises the identical pipeline
(4 scenarios × 2 arms × 1 seed) without any model call. CI runs this
plus the artifact contract check:

```bash
python -m src.nomos.agents.schema check results/agent
```

### Full protocol run

```bash
python -m src.nomos.runner agent --seeds 20 --steps 100 \
    --backend pydanticai \
    --model openrouter:nvidia/nemotron-3-ultra-550b-a55b:free \
    --temperature 0.0
```

- **Pinned models**: the model string is recorded in every cache entry
  and must be pinned exactly. The default reference model is
  `openrouter:nvidia/nemotron-3-ultra-550b-a55b:free` (NVIDIA Nemotron 3
  Ultra 550B — the most capable **free** model on OpenRouter as of
  2026-07-31). All reference models are OpenRouter `:free` variants
  (official convention: append `:free` to any model ID — see
  https://openrouter.ai/docs/guides/routing/model-variants/free), so
  full runs cost nothing. Do not use the `openrouter/free` router alias
  for reference runs: it resolves to different models over time, which
  breaks pinning.
- **Sensitivity pins** (2+ models): `openai/gpt-oss-20b:free`
  (131k context, small/fast) and `google/gemma-4-31b-it:free`
  (262k context) are the recommended second/third pins. Results across
  different model pins are not directly comparable.
- **Free-model rate limits** (official FAQ): 50 requests/day without
  credits, 1,000 requests/day once $10 of credits have been purchased.
  The response cache absorbs this: cached replays perform zero model
  calls, so only first runs consume the budget.
- **Temperature**: `0.0` (the default) makes sampling deterministic
  on the provider side; the rendered prompt carries no timestamps, so
  identical prompts are always identical strings.
- **API key**: set `GOVERNANCE_LLM_MODEL` to override the model; the
  provider key comes from PydanticAI's standard env config
  (`OPENROUTER_API_KEY` for OpenRouter).

### Response cache and replay determinism

Every validated response is stored under a content address
(`results/agent/cache/{sha256}.json`) keyed by
`(model, prompt_hash, temperature)` where `prompt_hash` is the SHA-256
of the full rendered prompt (system prompt + observation). Re-running
the protocol with the same cache directory performs **zero model
calls**: every step replays the stored response, so trajectories are
bit-identical.

Verification steps:

```bash
# 1. Re-run with the same cache; expect "Cache: {'hits': N, 'misses': 0}"
python -m src.nomos.runner agent --seeds 20 --steps 100 --backend pydanticai

# 2. Check the committed manifest against the cache directory
python -m src.nomos.agents.schema check results/agent

# 3. Manual digest comparison (Linux/macOS)
(cd results/agent && sha256sum -c cache_manifest.json 2>/dev/null || true)
```

The cache manifest (`results/agent/cache_manifest.json`) maps every
entry to its SHA-256 digest and is committed with full runs, so
reviewers can verify replay determinism. The cache directory itself is
git-ignored.

### Artifact contract

The committed reference for the agent artifacts is the schema contract
in `src/nomos/agents/schema.py`. CI compares new runs against
this contract (keys, types, non-emptiness) — **never values**, which
change when model versions change. Schema stability is the CI
contract; a run may also be rejected on a digest mismatch against the
committed manifest.

## Output

## Lean Proofs

```bash
cd gov-budget-proof
lake build
```

Expected output: `Build completed successfully (20 jobs).` (Lean 4, toolchain
pinned in `gov-budget-proof/lean-toolchain`).

What this reproduces is that **the proofs compile**: every theorem in
`gov-budget-proof/` is re-checked by the Lean kernel, with no `sorry` and no
axiom declared by the corpus. It does not verify the reference implementation.
Nothing extracts the Lean model from `src/nomos/`, and no refinement argument
connects the two, so a green `lake build` says nothing about `speaker.py`. See
[Scope and limits](book/formal-verification-lean.md#scope-and-limits) and
[Chapter 5 §7](book/chapter-05/05-related-work.md#7-where-to-attack-this-chapter).

## Versioning

Each benchmark run logs the git commit hash in the metadata.
Run the following to associate results with the exact code version:

```bash
git log --oneline -1
```

Results are committed to the repository under `results/` and tagged
with the release version (e.g., `v0.1.0`).

## Citation

```bibtex
@software{nomos,
  author    = {Carlos Pinto (xcoder-es)},
  title     = {The Governance Layer: A Formal Framework for Self-Governing AI},
  year      = {2026},
  url       = {https://github.com/Nomos-N4s/nomos},
  doi       = {<OSF DOI pending>},
}
```
