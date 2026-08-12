# Roadmap

Execution order for open work, tracked on the GitHub project board
(https://github.com/users/xcoder-es/projects/3). Statuses follow the evidence
policy: **Backlog** = not started · **Ready** = queued next · **In progress** =
active branch/PR · **In review** = PR open · **Done** = closed.

Priorities: **P0** = in flight or immediate next · **P1** = next track ·
**P2** = later.

## Execution-plan decisions (2026-08-11)

1. **Azure-first deployment.** One cloud (Azure) fully green before any
   multi-cloud work — no parallel triple-IaC development (Track J gates K).
2. **release-please.** Semver/tag/changelog automation replaces manual cuts
   (Track I-F2, #218).
3. **Deploy-first Track E reorder.** #161 ships immediately; OTel/SLOs and
   dashboards land after the first deployment (Track J) so they instrument a
   live system. #164 (tamper-evident audit) moves earlier.
4. **Native components are evidence-gated.** No porting until #172 (protocol)
   and the Track L-F1 performance numbers justify it.
5. **Rebrand complete (2026-08-11).** #86 and slices #202/#203/#204 closed;
   residue sweep in `8ef6e7f`.

## Track A — Land the open PRs — DONE (2026-08-11)

1. **#181** auto-refresh toggle — MERGED 15:05Z (`77f355b`) → closes #75.
2. **#182** `/healthz`, `/readyz`, `/metrics` — MERGED 15:44Z (`a4126a2`) →
   closes #163 (Observability F3) and unlocks the Track J probe prerequisite.

## Track B — Close Phase C (#58)

3. **#73** dashboard cloud-compatible (`st.secrets`, relative paths).
4. **#74** deploy to Streamlit Community Cloud (parallel with Track J as the
   lite path).
   → Epic #58 Done (Phase C complete: #72, #75 done).

## Track C — Phase D: Dashboard Narrative (#59)

5. **#77** statistical annotations (CIs, Cohen's d) on charts.
6. **#76** interpretation panels ("What This Means" per section).
7. **#78** dynamic side-by-side comparison mode.
   → Epic #59 Done (#79 already done).

## Track D — Rebrand to Nomos (#86) — DONE

Rebrand complete 2026-08-11: repo `Nomos-N4s/nomos` (org, transferred from `xcoder-es/nomos`), package `src/nomos`,
Pages URL live, all three slices (#202/#203/#204) and epic #86 closed after a
checkbox-by-checkbox audit + residue sweep (`8ef6e7f`).

## Track E — Observability (#158) — deploy-first order

8. **#161** structured JSON logging (F1) — **DONE** (merged 2026-08-11), also
   consumed by Track J (Log Analytics) and Track F.
9. *(Track J deployment happens after #164 — the #161+#182 gate is now OPEN.)*
10. **#164** tamper-evident hash-chained audit log (F4) — **NEXT** (P1, moved
    earlier: core value, no deployment needed).
11. **#165** SLOs + alerting (F5) — after first deployment; consumes the
    E2 verification run's metrics handoff (Track J-F3, #222).
12. **#162** OpenTelemetry instrumentation (F2) && **#167** observability CI
    smoke suite (F7) — after a live system exists to instrument.
13. **#166** trace viewer unification (F6) — depends on #162.
14. **#168** Grafana dashboards + ops runbooks (F8) — last.
    → Epic #158 Done (#163 already done via Track A).

## Track F — SDK & distribution (#159)

15. **#169** packaging hardening (F1).
16. **#170** PyPI trusted publishing `nomos-n4s` (F2).
17. **#171** public API stabilization (F3).
18. **#172** language-agnostic governance protocol (F4) — **also gates
    Track L** (native feasibility).
19. **#174** SDK docs & DX (F6).
20. **#173** plugin architecture (F5) — Phase E item, land last.
    → Epic #159 Done.

## Track G — Lean proofs (#69 done, #70 next) — parallel track

Independent of all tracks; can be picked up any time. Extends the proven
budget/threshold invariants (#43/#44) to the Identity Layer (#69) and the TEE
isolation model (#70).

- **#69 Identity Layer — DONE (2026-08-10).** Five Lean 4 modules merged to
  `main` via stacked PRs #195-#199 (stack #200, commit `f56efa4`):
  IdentityTiers (Ch4 §3), IdentityGenesis (Ch4 §4), IdentityBuffer (Ch4 §5.2),
  IdentityHashes (Ch4 §2.1/§6.1), IdentityCoherence (Ch4 §6.1). Sub-issues
  #190-#194 and epic #69 closed; `lean-build` CI job enforced on every PR.
- **#70 TEE isolation model — next.** Formalize Appendix A (enclave
  invariants, Merkle batch verification, watchdog, deadlock breaker). Also a
  gate input for Track L-F2 (Rust TEE feasibility).

## Track H — Commercialization (#160) — gated

21. **#175** licensing & legal (F1) — **gate for everything else** (lawyer
    review required).
22. **#176** enterprise tier scope (F2) — after #175.
23. **#177** enterprise distribution (F3) — after #175.
24. **#180** funding readiness (F6) — anytime (OSF traction, metrics).
25. **#179** Nomos Cloud (F5) — **DEFERRED** until funding/legal signal.

## Track I — Release & delivery (#213) — DONE (2026-08-11)

Pushes to `main` trigger release-please, which opens a release PR for
releasable changes (multiple merges may batch into one PR); the version is
minted when that release PR merges. The multi-arch image publishes only on
release (`release: [published]`) or manual dispatch — never on tag push (see
#217). Track J consumes GHCR images instead of building in-cluster.

26. **#217** CI: publish multi-arch Docker image to GHCR on tag push (F1) —
    MERGED; trigger reworked to `release: [published]` + `workflow_dispatch`
    (release-please creates tags via the REST API, which fires no `push`
    event — the original trigger never ran, zero images until 2026-08-11).
    v0.10.0 backfilled via dispatch; artifacts live at
    `ghcr.io/nomos-n4s/nomos` (`0.10.0`, `latest`, `with-rl`).
27. **#218** adopt release-please for semver/tag/changelog automation (F2) —
    MERGED; v0.10.0 released, release PRs auto-created.
28. **#219** code coverage gate in CI (F3) — MERGED via PR #237 (gate at 90%,
    report-only until 2026-09-11).
    → Epic #213 Done.

## Track J — One-cloud deployment: Azure-first (#214) — P1

Gate: **#161 + #182 merged** (probes + structured logs) — both landed
2026-08-11, gate is **OPEN**. GHCR artifacts exist (v0.10.0 backfilled).
Runs parallel with Track B (Streamlit Cloud = lite path). Reference IaC for
Track K forks. Starts after #164.

29. **#220** ADR: modular-monolith topology + atomic governance gate (F1) —
    **DONE (2026-08-12)** — `docs/adr/0001-modular-monolith-and-atomic-governance-gate.md`.
30. **#221** Pulumi IaC: Azure Container Apps (F2) — **NEXT**; consumes GHCR
    artifacts, Key Vault secrets, ACA probes, Log Analytics.
31. **#222** deployment verification run (F3) — 5-item checklist + metrics
    handoff to #165.
    → Epic #214 Done when verification receipts are posted.

## Track K — Multi-cloud extension: AWS & GCP (#215) — P2

Gate: **Track J fully green** (decision #1 — no parallel IaC development).

32. **#223** Pulumi: AWS (ECS Fargate) + parity checklist (F1).
33. **#224** Pulumi: GCP (Cloud Run) + parity checklist (F2).
34. **#225** cross-cloud parity matrix + docs (F3).
    → Epic #215 Done (feeds #160 enterprise fleet narrative).

## Track L — Native components & performance (#216) — P2, gated

Gate: **#172 (protocol) merged + evidence from #226.** No core port without
this epic's sign-off (decision #4).

35. **#226** performance budget & profiling harness (F1) — the evidence gate.
36. **#227** feasibility: Rust for TEE-critical runtime (F2) — spike + decision
    doc; ties to #176 and #70.
37. **#228** feasibility: Go for service plane (F3) — spike; ties to #172.
38. **#229** ADR: atomicity & service-split criteria (F4) — permanent
    "no microservices" guardrail.
    → Epic #216 Done.

## Next move

1. Track J-F2: **#221** Pulumi ACA IaC (ADR #220 done — topology is the modular monolith).
2. Track B in parallel (lite path): #73 → #74 Streamlit Cloud deploy.
3. Track J-F3: **#222** verification run after deploy.
4. Rest of Track E after the first deployment: #165 → #162/#167 → #166 → #168.