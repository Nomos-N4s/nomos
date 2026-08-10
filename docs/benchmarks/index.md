---
title: "Benchmark results across four governance scenarios"
description: "Summary of benchmark results and figures comparing five strategies across GridWorld, TemptationBank, DriftLab, and DeadlockMaze governance scenarios."
---

# Benchmark Results

See the [benchmark results summary](https://github.com/xcoder-es/governance-layer/blob/main/results/benchmark_summary.csv) and
[detailed figures](https://github.com/xcoder-es/governance-layer/blob/main/results/figures/) for the latest comparison across
all four experiment scenarios and five strategies.

## Running Benchmarks

```bash
python -m src.nomos.runner all --baselines --steps 1000 --seeds 20
```

## Interpreting Results

- **GridWorld**: Tests safety-constrained navigation. Governance prevents poison consumption.
- **TemptationBank**: Tests voluntary self-binding under temptation. `ban_loans` contract enacts by step ~30.
- **DriftLab**: Tests identity coherence under reward-function shift. Governance maintains alignment.
- **DeadlockMaze**: Tests procedural deadlock recovery. DeadlockBreaker mechanism prevents infinite loops.

## Statistical Reporting

`compute_effect_sizes()` compares governance against each baseline per scenario and returns one record per pair. Each record includes:

- **Cohen's d** with a 95% confidence interval (Delta method) and a qualitative `interpretation` label (`negligible`, `small`, `medium`, `large`).
- **Mann-Whitney U** with an exact p-value when the larger group has 8 or fewer samples, and an asymptotic p-value otherwise.
- **Raw, Bonferroni-corrected, and Holm-Bonferroni-corrected p-values** across the full family of governance-vs-baseline comparisons, with `significant` and `significant_holm` flags. Prefer `significant_holm` as the primary decision — Holm is uniformly more powerful than Bonferroni while controlling the same family-wise error rate.
- **`normality_warning`** — set when the pooled sample fails a Shapiro-Wilk test. When present, treat Cohen's d CIs as approximate and lean on the Mann-Whitney U result.
- **`paired`** — `true` when the design heuristic detects repeated measures across strategies (e.g., matched seeds).

See [Appendix D §D.5](/book/appendix-d-experiment-protocol) for the full pre-registered analysis plan.
