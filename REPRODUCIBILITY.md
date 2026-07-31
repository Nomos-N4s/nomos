# Reproducibility Protocol

All benchmark results in the Governance Layer reference implementation
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
git clone https://github.com/xcoder-es/governance-layer.git
cd governance-layer
pip install -e .

# 2. Run the full benchmark suite
python -m src.governance.runner all --baselines --steps 1000 --seeds 20
```

### Expected Runtime

- **Reference hardware** (single core, 2.5 GHz): ~6 seconds wall-clock
- All 400 runs (4 scenarios × 5 strategies × 20 seeds × 1,000 steps)
  complete in under 10 seconds on any modern CPU.

### Seed Strategy

20 fixed seeds per scenario-strategy combination (80 combinations × 20
seeds = 1,600 individual experiment runs). Each experiment uses a
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

| Strategy | GridWorld | TemptationBank | DriftLab | DeadlockMaze |
|---|---|---|---|---|
| Governance | 3.0 reward, 0 violations | 1998.0 reward, 0 violations | 0 reward, 0 violations | 999 deadlocks |
| MonolithicRL | — | — | — | — |
| Random | — | — | — | — |
| StaticMasking | — | — | — | — |
| VetoOnly | — | — | — | — |

*Dash entries are filled after the full 20-seed run completes.*

## Formal Predictions

```bash
# Verify all 12 formal predictions pass
python -m src.governance.runner prove --all
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
python -m src.governance.runner agent --seeds 1 --steps 30 --backend stub
```

The stub backend is deterministic and exercises the identical pipeline
(4 scenarios × 2 arms × 1 seed) without any model call. CI runs this
plus the artifact contract check:

```bash
python -m src.governance.agents.schema check results/agent
```

### Full protocol run

```bash
python -m src.governance.runner agent --seeds 20 --steps 100 \
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
python -m src.governance.runner agent --seeds 20 --steps 100 --backend pydanticai

# 2. Check the committed manifest against the cache directory
python -m src.governance.agents.schema check results/agent

# 3. Manual digest comparison (Linux/macOS)
(cd results/agent && sha256sum -c cache_manifest.json 2>/dev/null || true)
```

The cache manifest (`results/agent/cache_manifest.json`) maps every
entry to its SHA-256 digest and is committed with full runs, so
reviewers can verify replay determinism. The cache directory itself is
git-ignored.

### Artifact contract

The committed reference for the agent artifacts is the schema contract
in `src/governance/agents/schema.py`. CI compares new runs against
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

Expected output: 12/12 built successfully (Lean 4).

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
@software{governance_layer,
  author    = {Carlos Pinto (xcoder-es)},
  title     = {The Governance Layer: A Formal Framework for Self-Governing AI},
  year      = {2026},
  url       = {https://github.com/xcoder-es/governance-layer},
  doi       = {<OSF DOI pending>},
}
```
