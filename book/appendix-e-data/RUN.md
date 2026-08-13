---
title: "Published RL adversary run manifest"
description: "Exact command line, seeds, environment, and provenance for the RL adversary results reported in Appendix E."
---

# Published run manifest

Provenance for the numbers in [Appendix E §E.4/§E.5](../appendix-e-rl-adversary.md).
The aggregate itself is [`adversary_protocol.json`](adversary_protocol.json) in
this directory.

## Command

```bash
uv sync --extra rl-repro
python -m src.nomos.experiments.rl_adversary protocol \
  --modes governance no_governance static_mask \
  --seeds 42 43 44 45 46 \
  --timesteps 100000 \
  --size 10 \
  --eval-episodes 10 \
  --reward-mode bypass \
  --log-dir results/rl_adversary
```

The published run executed the three modes as three parallel processes (one per
mode, `OMP_NUM_THREADS=4`) rather than the single sequential invocation above.
That is a scheduling detail only: each `(mode, seed)` run is independently
seeded through `nomos.experiments.rl_seeding.seed_everything`, so the sequential
command reproduces the same work.

## Protocol

| Field | Value |
|-------|-------|
| Modes | `governance`, `no_governance`, `static_mask` |
| Seeds | 42, 43, 44, 45, 46 |
| Timesteps per (mode, seed) | 100,000 |
| Reward mode | `bypass` (adversarial) |
| Attack surface | enabled (`adversarial=True`) |
| Evaluation | 10 episodes, deterministic policy |
| ε (bypass threshold) | 0.01 |
| Budget cap (H1) | 3 |
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

The `rl-repro` extra pins torch, stable-baselines3, and gymnasium exactly on
every supported interpreter. numpy is marker-split: the published run used
2.5.1, which requires Python ≥ 3.12, so interpreters below that resolve to
2.2.6. Determinism caveats are documented in
[Appendix D §D.7](../appendix-d-experiment-protocol.md) and in
`nomos/experiments/rl_seeding.py`.

## Artifacts

Working artifacts are written to `results/rl_adversary/` and are **not** tracked
(`.gitignore`). Only the aggregate below is committed, so the published figures
are versioned with the book.

| Artifact | Path | Tracked |
|----------|------|---------|
| Model checkpoints (15) | `results/rl_adversary/<mode>/ppo_<mode>_seed<seed>.zip` | no |
| Per-seed results (15) | `results/rl_adversary/<mode>/result_<mode>_seed<seed>.json` | no |
| Aggregate | `results/rl_adversary/adversary_protocol.json` | no |
| **Published aggregate** | `book/appendix-e-data/adversary_protocol.json` | **yes** |

## Provenance notes

- Hypotheses, metrics, and thresholds were committed in
  [the pre-registration](../appendix-e-preregistration.md) before the run.
- The H1–H3 applicability scoping (control modes carry no verdict) was added
  after an adversarial review of the harness and before any result was
  published. It changed no threshold and did not affect the `governance`
  verdict. See the pre-registration for the full note.
- Evaluation was re-run from the saved checkpoints after four measurement
  defects were corrected (`0/0` rates published as `0.0`). Training was not
  affected by those defects and was not repeated; see §E.5.2.
