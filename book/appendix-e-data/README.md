---
title: "Appendix E data: published RL adversary artifacts"
description: "Tracked home for the published RL adversary result summary and its reproducibility manifest."
---

# Appendix E data

This directory is the **tracked** home for the published RL adversary result —
the numbers reported in [Appendix E](../appendix-e-rl-adversary.md) §E.4/§E.5.
Working artifacts (model checkpoints, per-seed JSON, logs) live under
`results/rl_adversary/`, which is gitignored; only the small, citable summary is
committed here so the published figures are versioned with the book.

## Files

| File | Contents |
|------|----------|
| `adversary_protocol.json` | The aggregate result: per-mode mean ± 95% CI for each canonical metric and per-hypothesis (H1/H2/H3) pass/fail verdict, plus the `protocol` (seeds, timesteps, hyperparameters) and `environment` (library versions) blocks used. |
| `RUN.md` | The exact command line, seed set, timestamp, and machine notes for the published run. |

## Reproducing the published run

```bash
uv sync --extra rl-repro
python -m src.nomos.experiments.rl_adversary protocol \
  --timesteps 100000 --seeds 42 43 44 45 46 \
  --log-dir results/rl_adversary
# then copy the aggregate into the tracked location:
cp results/rl_adversary/adversary_protocol.json book/appendix-e-data/
```

The hypotheses, metrics, and thresholds are pre-registered in
[appendix-e-preregistration.md](../appendix-e-preregistration.md); the
determinism and archiving policy is in
[appendix-d-experiment-protocol.md](../appendix-d-experiment-protocol.md) §D.7.
