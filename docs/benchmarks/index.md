# Benchmark Results

See the [benchmark results summary](https://github.com/xcoder-es/governance-layer/blob/main/results/benchmark_summary.csv) and
[detailed figures](https://github.com/xcoder-es/governance-layer/blob/main/results/figures/) for the latest comparison across
all four experiment scenarios and five strategies.

## Running Benchmarks

```bash
python -m src.governance.runner all --baselines --steps 1000 --seeds 20
```

## Interpreting Results

- **GridWorld**: Tests safety-constrained navigation. Governance prevents poison consumption.
- **TemptationBank**: Tests voluntary self-binding under temptation. `ban_loans` contract enacts by step ~30.
- **DriftLab**: Tests identity coherence under reward-function shift. Governance maintains alignment.
- **DeadlockMaze**: Tests procedural deadlock recovery. DeadlockBreaker mechanism prevents infinite loops.
