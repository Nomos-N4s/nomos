# Benchmark Results

## Artifacts

| File | Description |
|------|-------------|
| `prove_results.json` | Formal prediction verification (12 predictions from Ch2-4) |
| `benchmark_results.json` | Aggregated benchmark statistics: per-strategy-scenario means, std, 95% CI, Cohen's d, reward-hacking episodes |
| `benchmark_summary.csv` | Flat CSV of aggregates: strategy, scenario, num_seeds, mean_reward, std_reward, mean_deadlocks, mean_violations, ci_lower, ci_upper |
| `benchmark_raw.csv` | Per-step raw records: timestamp, scenario, strategy, seed, step, reward, violations, deadlocks, runtime_ms |
| `figures/reward_curves.png` | Reward over time (mean ± 95% CI shaded) — governance vs baselines |
| `figures/reward_curves.svg` | Same, vector format |
| `figures/violation_rates.png` | Constraint violation rate bar chart per scenario |
| `figures/violation_rates.svg` | Same, vector format |
| `figures/deadlock_frequency.png` | Deadlock rate grouped bar chart per scenario |
| `figures/deadlock_frequency.svg` | Same, vector format |
| `figures/pareto_frontier.png` | Pareto frontier: cumulative reward vs safety violations |
| `figures/pareto_frontier.svg` | Same, vector format |

## Experimental Protocol

- **4 scenarios**: GridWorld, TemptationBank, DriftLab, DeadlockMaze
- **5 strategies**: governance, monolithic_rl, random, static_masking, veto_only
- **20 random seeds** per strategy-scenario pair
- **1,000 steps** per run
- **Total**: 4 × 5 × 20 = 400 experiment runs (6.3s wall-clock)

## Key Metrics

- **GridWorld**: All strategies achieve ~3.0 reward with 0 violations (apples collected before poison spawns at 30% rate offset grid sparsity).
- **TemptationBank**: 1998.0 reward across all strategies (2/step steady work; ban_loans contract enacts by step 30).
- **DriftLab**: 0 reward, 0 violations, 0 deadlocks across all strategies (identity coherence proposals win via higher priority tag).
- **DeadlockMaze**: 999 deadlocks across all strategies (tighten_quorum passes -> empty proposal list -> deadlock breaker fires, but resets produce same cycle).
