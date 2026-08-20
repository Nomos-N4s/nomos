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

20 fixed seeds per scenario-strategy combination (19 combinations × 20
seeds = 380 individual experiment runs). Four scenarios × five strategies
is 20 combinations; GridWorld has no `static_masking` arm, for the reason
given below the results table. Each experiment uses a
deterministic seed for the RNG — same seed always produces identical
results. The seed list covers a diverse range to detect sensitivity.

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
| Governance | 3.0 reward, 0 violations | 1998.0 reward, 0 violations | 1000.0 reward, 0 violations, 0.0 drift | 999 deadlocks |
| MonolithicRL | — | — | — | — |
| Random | — | — | — | — |
| StaticMasking | not applicable | 2000.0 reward, 0 violations | 1000.0 reward, 0 violations, 0.0 drift | 1000 deadlocks (total inaction — see below) |
| VetoOnly | — | — | — | — |

*Dash entries are filled after the full 20-seed run completes.*

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

DriftLab never consults its RNG and the governed path is deterministic, so
every strategy except Random reports identical values on both seeds; Random
is given per seed. Drift is a function of how many commitment violations a
strategy actually executed, which is why Random lands between the fully
compliant and fully adversarial strategies.

## Formal Predictions

```bash
# Verify all 12 formal predictions pass
python -m src.nomos.runner prove --all
```

Expected output: `12/12 PASS`

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
