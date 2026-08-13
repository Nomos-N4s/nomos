---
title: "Published verifier-frontier run manifest"
description: "Exact commands, seeds, environment, and pre-registration provenance for the epsilon-sweep reported in Appendix F."
---

# Published run manifest

Provenance for the curve in [Appendix F §F.4](../appendix-f-verifier-frontier.md).
The curve itself is [`verifier_frontier.json`](verifier_frontier.json) in this
directory.

## Commands

```bash
uv sync --extra rl-repro

# The full sweep, as a single sequential invocation
python -m src.nomos.experiments.rl_adversary sweep \
  --epsilons 1.0 0.99 0.95 0.9 0.8 0.7 0.6 0.5 \
  --arms unshaped shaped \
  --seeds 42 43 44 45 46 \
  --timesteps 100000 \
  --size 10 \
  --eval-episodes 10 \
  --log-dir results/rl_frontier
```

The published run executed the 16 grid points and the control block as
**concurrent processes** (five at a time, `OMP_NUM_THREADS=2`) rather than the
single sequential invocation above, then reassembled the curve:

```bash
# one process per point
python -m src.nomos.experiments.rl_adversary sweep --point <arm> <epsilon> \
  --timesteps 100000 --seeds 42 43 44 45 46 --log-dir results/rl_frontier
python -m src.nomos.experiments.rl_adversary sweep --controls-only \
  --timesteps 100000 --seeds 42 43 44 45 46 --log-dir results/rl_frontier
# then
python -m src.nomos.experiments.rl_adversary sweep --assemble --log-dir results/rl_frontier
```

This is a scheduling detail only. Each `(mode, seed)` run is independently seeded
through `nomos.experiments.rl_seeding.seed_everything`, so the sequential command
reproduces the same work. `--assemble` **refuses** to combine points that
disagree about their run configuration, so a curve cannot be silently stitched
together from differently-configured points.

## Protocol

| Field | Value |
|-------|-------|
| ε grid | 1.0, 0.99, 0.95, 0.9, 0.8, 0.7, 0.6, 0.5 |
| Arms | `unshaped`, `shaped` (evaluation unshaped in both) |
| Seeds | 42, 43, 44, 45, 46 |
| Runs | 80 governed + 10 control = 90 × 100,000 timesteps |
| Mode | `governance`; controls at ε = 1.0 |
| Ambiguity ratio | 0.5 |
| Spoof region | enabled (graded falsification severity) |
| Claim resolution | 17 buckets |
| Verifier | parametric ε dial |
| Evaluation | 10 episodes, deterministic policy |
| PPO | MlpPolicy, lr 3e-4, n_steps 2048, batch 64, epochs 10, γ 0.99, GAE λ 0.95, clip 0.2, ent 0.01 |

## Environment

| Component | Version |
|-----------|---------|
| Python | 3.14.6 |
| torch | 2.13.0+cpu |
| stable-baselines3 | 2.9.0 |
| gymnasium | 0.29.1 |
| numpy | 2.5.1 |
| Platform | Windows 11, CPU only (12 cores) |

Same pinned `rl-repro` environment as the Appendix E campaign; determinism
caveats are in [Appendix D §D.7](../appendix-d-experiment-protocol.md) and in
`nomos/experiments/rl_seeding.py`.

## Pre-registration provenance

Two commits matter, and both are recorded because quoting only one would be
misleading in opposite directions.

| Event | Commit | Timestamp (UTC) |
|-------|--------|-----------------|
| **Hypotheses H4–H7, thresholds, ε grid, arms, seeds committed** | `c0356ea` | 2026-08-13T10:03:41Z |
| Reporting addendum added (no threshold changed) | `6fde9c9` | 2026-08-13T10:14:29Z |
| **First training run started** | — | 2026-08-13T10:14:58Z |

The second commit lands 29 seconds before the run, which is exactly the kind of
timing that should invite scrutiny — so here is what it contains. Between
`c0356ea` and `6fde9c9` the pre-registration gained **one paragraph and nothing
else**: an addendum recording that the bypass rate restricted to ambiguous tiles
would be reported beside H6, because an engineering timing run had shown the
overall rate is diluted by attempt composition. No hypothesis, metric, or
threshold changed. Verify it directly:

```bash
git diff c0356ea 6fde9c9 -- book/appendix-e-preregistration.md
```

The `preregistration` block inside `verifier_frontier.json` records the SHA-256
of the file as it stood at run time (`c6ea78a0…`) and the commit that last
modified it, so the text can be proved not to have moved since.

## Artifacts

Working artifacts are written to `results/rl_frontier/` and are **not** tracked
(`.gitignore`). Only the curve below is committed, so the published figures are
versioned with the book.

| Artifact | Path | Tracked |
|----------|------|---------|
| Model checkpoints (90) | `results/rl_frontier/<arm>_eps<ε>/ppo_governance_seed<seed>.zip` | no |
| Per-seed results (90) | `results/rl_frontier/<arm>_eps<ε>/result_governance_seed<seed>.json` | no |
| Per-point aggregates (16) | `results/rl_frontier/point_<arm>_eps<ε>.json` | no |
| Control block | `results/rl_frontier/controls.json` | no |
| **Published curve** | `book/appendix-f-data/verifier_frontier.json` | **yes** |
| **Published figures** | `docs/benchmarks/verifier_frontier{,_panels}.{png,svg}` | **yes** |
