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
