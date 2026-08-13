---
title: "Appendix F data: published verifier-frontier artifacts"
description: "Tracked home for the published epsilon-sweep curve, its pre-registration provenance, and its reproducibility manifest."
---

# Appendix F data

The **tracked** home for the published verifier-quality frontier — the curve
reported in [Appendix F](../appendix-f-verifier-frontier.md) §F.4. Working
artifacts (90 model checkpoints, per-seed JSON, per-point aggregates) live under
`results/rl_frontier/`, which is gitignored; only the small citable summary is
committed here, so the published figures are versioned with the book.

## Files

| File | Contents |
|------|----------|
| `verifier_frontier.json` | The curve: one record per (ε, arm) with mean ± 95% CI for every reported metric, the H4–H7 verdicts, the curve-shape analysis, the control brackets, and the `preregistration` provenance block. |
| `RUN.md` | The exact commands, seed set, environment, and provenance for the published run. |

## Verifying the pre-registration

The claim that the hypotheses were fixed before the runs is checkable rather than
asserted. `verifier_frontier.json` carries a `preregistration` block recording
the SHA-256 of the pre-registration and the commit that last modified it:

```bash
# The hash must match — proving the text has not moved since the run
sha256sum book/appendix-e-preregistration.md

# The commit date must precede the run timestamp in RUN.md
git log -1 --format='%H %cI' -- book/appendix-e-preregistration.md
```

`rl_validate` **fails** a frontier whose pre-registration hash is missing: a
result with no verifiable pre-registration is not a weaker result, it is an
unfalsifiable one.

## Verifying the sweep is complete

The curve is assembled from 16 independently-scheduled point jobs, so a crashed
or never-launched job would otherwise leave a hole that scoring could not see —
and if the absent point were the one that would have failed, a hypothesis could
be reported as PASS on data that never existed. The `verdicts.coverage` block
records the expected grid, how many points carried a measured value, and which
if any are absent; every affected hypothesis degrades to `null` rather than to a
verdict, and `rl_validate` rejects the artifact outright.

```bash
python -c "import json;print(json.load(open('book/appendix-f-data/verifier_frontier.json'))['verdicts']['coverage'])"
# {'expected_points': 16, 'measured_points': 16, 'missing': [], 'complete': True, ...}
```

## Reproducing

```bash
uv sync --extra rl-repro
python -m src.nomos.experiments.rl_adversary sweep \
  --timesteps 100000 --seeds 42 43 44 45 46 \
  --log-dir results/rl_frontier
# then copy the curve into the tracked location:
cp results/rl_frontier/verifier_frontier.json book/appendix-f-data/
```

Hypotheses, metrics, and thresholds are pre-registered in
[Appendix E (pre-registration) Part II](../appendix-e-preregistration.md); the
determinism and archiving policy is in
[Appendix D §D.7](../appendix-d-experiment-protocol.md).
