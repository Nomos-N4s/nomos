---
title: "Benchmark results across four governance scenarios"
description: "Summary of benchmark results and figures comparing five strategies across GridWorld, TemptationBank, DriftLab, and DeadlockMaze governance scenarios."
---

# Benchmark Results

See the [benchmark results summary](https://github.com/Nomos-N4s/nomos/blob/main/results/benchmark_summary.csv) and
[detailed figures](https://github.com/Nomos-N4s/nomos/blob/main/results/figures/) for the latest comparison across
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

## RL Adversary Results

A PPO adversary trained to **defeat** the governance layer (not to solve the task),
with the attack surface to forge priority tags, mis-report risk, and flood the
agenda. 100,000 timesteps × 5 seeds × 3 modes, hypotheses pre-registered before
the run.

| Mode | Governance bypass rate | Violations / episode | H1 | H2 | H3 |
|------|-----------------------|----------------------|----|----|----|
| `governance` | **0.000** [0.000, 0.000] | 0.000 ± 0.000 | PASS | PASS | PASS |
| `no_governance` (ceiling control) | 1.000 [1.000, 1.000] | 1.500 ± 0.614 | n/a | n/a | n/a |
| `static_mask` (floor control) | 0.000 [0.000, 0.000] | 0.000 ± 0.000 | n/a | n/a | n/a |

Zero of 4,762 adversarial poison attempts executed. The adversary did, however,
silence the Safety committee on 100% of its proposals — it was stopped by the
Integrity committee's ground-truth check, not by Safety. The headline is that
**defense in depth is load-bearing**, not that the layer is unbreakable.

H1–H3 carry no verdict for the control modes because they are claims about
Parliament mechanisms those modes do not have; the controls bracket the result
instead. See [Appendix E](/book/appendix-e-rl-adversary) for per-seed values and
limitations, and the [pre-registration](/book/appendix-e-preregistration) for the
metrics and thresholds.

```bash
uv sync --extra rl-repro
python -m src.nomos.experiments.rl_adversary protocol --timesteps 100000 --seeds 42 43 44 45 46
```

## Statistical Reporting

`compute_effect_sizes()` compares governance against each baseline per scenario and returns one record per pair. Each record includes:

- **Cohen's d** with a 95% confidence interval (Delta method) and a qualitative `interpretation` label (`negligible`, `small`, `medium`, `large`).
- **Mann-Whitney U** with an exact p-value when the larger group has 8 or fewer samples, and an asymptotic p-value otherwise.
- **Raw, Bonferroni-corrected, and Holm-Bonferroni-corrected p-values** across the full family of governance-vs-baseline comparisons, with `significant` and `significant_holm` flags. Prefer `significant_holm` as the primary decision — Holm is uniformly more powerful than Bonferroni while controlling the same family-wise error rate.
- **`normality_warning`** — set when the pooled sample fails a Shapiro-Wilk test. When present, treat Cohen's d CIs as approximate and lean on the Mann-Whitney U result.
- **`paired`** — `true` when the design heuristic detects repeated measures across strategies (e.g., matched seeds).

See [Appendix D §D.5](/book/appendix-d-experiment-protocol) for the full pre-registered analysis plan.
