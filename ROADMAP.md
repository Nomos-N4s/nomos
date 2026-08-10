# Roadmap

Execution order for open work, tracked on the GitHub project board
(https://github.com/users/xcoder-es/projects/3). Statuses follow the evidence
policy: **Backlog** = not started · **Ready** = queued next · **In progress** =
active branch/PR · **In review** = PR open · **Done** = closed.

Priorities: **P0** = in flight or immediate next · **P1** = next track ·
**P2** = later.

## Track A — Land the open PRs (now)

1. **#181** auto-refresh toggle → PR #181 in review (maintainer change requests
   outstanding) → closes #75.
2. **#182** `/healthz`, `/readyz`, `/metrics` → PR #182 in review (change
   requests outstanding) → closes #163 (Observability F3).

Gate: nothing else starts until these merge — they touch `runner.py`,
`pyproject.toml`, and `CHANGELOG.md` (merge-conflict risk).

## Track B — Close Phase C (#58)

3. **#73** dashboard cloud-compatible (`st.secrets`, relative paths).
4. **#74** deploy to Streamlit Community Cloud.
   → Epic #58 Done (Phase C complete: #72, #75 done).

## Track C — Phase D: Dashboard Narrative (#59)

5. **#77** statistical annotations (CIs, Cohen's d) on charts.
6. **#76** interpretation panels ("What This Means" per section).
7. **#78** dynamic side-by-side comparison mode.
   → Epic #59 Done (#79 already done).

## Track D — Rebrand to Nomos (#86)

8. **#86** rename repo/package `governance-layer` → `nomos` (`src/nomos`,
   imports, docs, mkdocs `site_url`, pyproject). Do this **before** the SDK
   and remaining observability features land, so new PRs are written against
   the final namespace and nothing publishes under the old name (blocks
   `nomos-n4s` PyPI release in Track F).

## Track E — Observability (#158)

9. **#161** structured JSON logging (F1).
10. **#162** OpenTelemetry instrumentation (F2).
11. **#167** observability CI smoke suite (F7) — lands with F1/F2.
12. **#166** trace viewer unification (F6) — depends on #162.
13. **#164** tamper-evident hash-chained audit log (F4).
14. **#165** SLOs + alerting (F5).
15. **#168** Grafana dashboards + ops runbooks (F8).
    → Epic #158 Done (#163 already done via Track A).

## Track F — SDK & distribution (#159)

16. **#169** packaging hardening (F1) — after #86 (name).
17. **#170** PyPI trusted publishing `nomos-n4s` (F2).
18. **#171** public API stabilization (F3).
19. **#172** language-agnostic governance protocol (F4).
20. **#174** SDK docs & DX (F6).
21. **#173** plugin architecture (F5) — Phase E item, land last.
    → Epic #159 Done.

## Track G — Lean proofs (#69, #70) — parallel track

Independent of all tracks; can be picked up any time. Extends the proven
budget/threshold invariants (#43/#44) to the Identity Layer (#69) and the TEE
isolation model (#70).

## Track H — Commercialization (#160) — gated

22. **#175** licensing & legal (F1) — **gate for everything else** (lawyer
    review required).
23. **#176** enterprise tier scope (F2) — after #175.
24. **#177** enterprise distribution (F3) — after #175.
25. **#180** funding readiness (F6) — anytime (OSF traction, metrics).
26. **#179** Nomos Cloud (F5) — **DEFERRED** until funding/legal signal.

## Next move

Track A: merge #181 and #182 after the authors address the inline change
requests, then start #73/#77/#161 in parallel (P0 items).
