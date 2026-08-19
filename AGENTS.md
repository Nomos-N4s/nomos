## Objective
- Develop a formal theoretical framework for self-governing AI around the Neural Parliament, Ulysses Contracts, and an Identity Layer — now with a full reference implementation under active construction.
- Register the framework on OSF for timestamp provenance and DOI.

## Important Details
- Author: **Carlos Pinto (xcoder-es)** — solo software builder, not an academic. Repo is `Nomos-N4s/nomos` (org-owned; transferred from `xcoder-es/nomos` 2026-08-11). All inquiries to capintobe@gmail.com.
- All Mermaid diagrams and LaTeX must avoid HTML tags (`<br/>`), custom `classDef` styling, and nested `\text{}` for GitHub compatibility. Use `\mathrm{}` instead.
- **First AI-generated review panel** (5 rounds) — an AI assistant adversarially critiqued theoretical vetting across all three layers, not a human panel. All accepted fixes executed. Three residual risks acknowledged (social engineering, hardware supply chain, adaptive proxy gap) as unavoidable physical-world limits.
- **Second, harder AI-generated review panel** (2026-07-26) evaluated the implementation with grade C-. One genuine bug found (baseline decoupling in benchmarks) and fixed. Full response at `book/responses/response-to-expert-panel-harder-review.md`.
- OSF preregistration prepared — content at `osf-registration.md`. Needs manual upload to https://osf.io/ to mint DOI.
- **CLA.md** added — standard Individual Contributor License Agreement. External contributors must accept terms (PR = acceptance). CONTRIBUTING.md updated to reference it.
- Architecture: Capability → Governance → Identity. Deep learning, JEPA world models, and computer vision are Capability Layer technologies; the Governance Layer constrains them.

## Conventions
- **Package management**: uv is the project's package manager. `uv.lock` is the source of truth — never edit by hand; regenerate with `uv lock` and install with `uv sync --frozen`. Docker builds are uv-native (`--frozen`). Note: `uv` may not be on PATH in non-interactive **host/CI shells** — use `python -m uv` there. **Exception — Dockerfiles**: uv is installed as a standalone binary at `/bin/uv` (via `COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv`), it is NOT an importable Python module; always invoke it as `/bin/uv` in `RUN` steps to avoid `No module named uv` build failures.
- **Atomic commits**: commit in small, focused units with conventional prefixes (`feat:`, `fix:`, `docs:`, `chore:`, `build:`, `test:`). Frequent atomic commits keep entire.io checkpoint refs flowing — the history is the telemetry.
- **PR lifecycle — HARD RULE**: the agent may create PRs and push to their branches, but may **NEVER merge, close, or otherwise finalize any PR** without the user's explicit authorization. Wait for the user (or their AI reviewers) to merge. Always pass `--head <branch>` explicitly to `gh pr create` (head inference from local checkouts is unreliable). Always populate the PR description using all 6 required sections from `.github/PULL_REQUEST_TEMPLATE.md` (`## Description`, `## Type of Change`, `## Checklist`, `## Testing`, `## Screenshots / Output`, `## Additional Notes`) to satisfy the repository's PR template enforcer CI check (`.github/workflows/pr-template-enforcer.yml`).
- **Provision, Verify, and Destroy (Cloud Cost-Safety) — HARD RULE**: For any cloud resource provisioning (Azure, AWS, GCP), agents MUST follow a strict lifecycle to prevent unnecessary billing: (1) **Provision** resources only when explicitly authorized; (2) **Verify** operational status immediately using verification scripts and health probes; (3) **Destroy** resources immediately after verification is complete or testing concludes.

## Work State
### Completed
- **Chapters 1-5** — All written. Ch1 (motivation), Ch2 (Neural Parliament, 560 lines), Ch3 (Ulysses Contracts, 359 lines), Ch4 (Identity Layer, 573 lines), Ch5 (Related Work — positions Nomos against shielding, CMDPs, reward machines, guaranteed-safe AI, AgentSpec/MI9/AgentBound on four axes; attributes the term "bounded autonomy"; issue #255). Ch4 includes: formal tuple $\mathcal{I} = \langle \mathcal{O}, \mathcal{C}_{\mathrm{core}}, \mathcal{K}, \mathcal{P} \rangle$, four-tier mutability, genesis bootstrapping with 3-of-5 multisig, ontology extension with sandboxed isolation buffer (empirical property measurement via independent monitors), runtime integrity hashes for action bindings, liveness exception for hardware deadlock breaker, constitutional contracts.
- **Appendix A** — TEE threat model, SGX/SEV/TrustZone, hardware watchdog, constant-time execution, Merkle-tree batch verification, single-enclave architecture with multi-enclave consensus addendum, deadlock breaker cold-boot recovery (§A.9.5).
- **Response to AI-generated review panel** — `book/responses/response-to-review-panel.md`. All 5 phases documented. Phase 5.2 concedes all three Chapter 4 Identity Layer attacks: isolation buffer sandbox (§5.2 fix), runtime integrity hashes (§2.1/§6.1 fix), deadlock breaker (§A.9.5 fix).
- **MVP code** — `src/nomos/speaker.py`. Reference implementation with deterministic falsification counter. Runs successfully.
- **Full modular reference implementation** — 50+ Python files across 10 subpackages (~2800 lines total):

  | Module | Files | Key Contents |
  |---|---|---|
  | Core types | `models.py` (73 lines) | PriorityTag, Action, Proposal, GovernanceDecision, GovernanceContext |
  | Parliament | `committee/` (178 lines) | ABC + 7 concrete members (Reward, Safety, Curiosity, Planning, Memory, Social, Integrity) |
  | Identity Layer | `identity/` (383 lines) | ontology.py, core.py (commitments), tiers.py (4-tier mutability), keys.py (genesis 3-of-5), params.py (bounded envelope), extension.py (sandboxed isolation buffer) |
  | Contracts | `contracts/` (159 lines) | contract.py (tuple + lifecycle), enforcement.py (3 κ modes), merger.py (mask union/intersection) |
  | TEE Simulation | `tee/` (216 lines) | enclave.py (single-enclave sim), batch.py (Merkle root), watchdog.py (heartbeat + deadlock breaker), constant_time.py (data-oblivious loops) |
  | Speaker | `speaker.py` (191 lines) | Full state machine: budgets, agenda sorting, scoring, tag compliance, vetoes, weighted voting |
  | Experiments | `experiments/` (469 lines) | base.py (scenario ABC + metrics), grid_world.py, temptation_bank.py, drift_lab.py, deadlock_maze.py, metrics.py |
  | Benchmarks | `benchmarks/` (360+ lines) | baselines.py (4 comparison strategies), run_all.py, report.py, **analysis.py** (statistical pipeline + Cohen's d + reward-hacking detection), **figures.py** (4 publication-ready plots) |
  | CLI | `runner.py` (320 lines) | Full argparse: `--baselines`, `--strategies`, `--steps`, `--seeds`, `--csv` export, `--config` (DSL) |
| DSL | `dsl/` (5 files, ~550 lines) | Indentation-based parser, validator, models, errors |
  | Ontology | `ontology/` (246 lines) | ABC + MemoryBackend (default) + Neo4jBackend (when .env configured) |
  | Dashboard | `dashboard/` (550+ lines) | Streamlit app with 5 tabs: Formal Model, Parliament Live, Benchmarks, RL Training, Agent Traces |

- **Neo4j integration**: `Neo4jBackend` in `src/nomos/ontology/neo4j_backend.py` is fully wired into the Streamlit dashboard. When `NEO4J_URI` is present in `.env`, the dashboard auto-detects and uses Neo4j Aura for persistent ontology storage and decision logging. Falls back to `MemoryBackend` otherwise. Decision logging records each replayed step's scores, vetoes, and metadata as ontology entities. (Issue #21 — Integrated into dashboard per Option A.)

- **Phase D: AI Agent Validation completed** (epic #145, all of #138–#144 closed 2026-08-01): PydanticAI/OpenRouter adapter, governed-vs-ungoverned harness, 4 LLM-native scenarios, metrics/reports, trace viewer, repro+CI smoke, 12-prediction cross-validation.
- **Benchmark results** (19 scenario-strategy combinations × 20 seeds × 1,000 steps = 380 runs, 6.3s wall-clock; GridWorld has no `static_masking` arm — see REPRODUCIBILITY.md):
  - GridWorld: 0.65 ± 0.88 mean reward, 0 violations under governance; monolithic_rl gets -22.45 ± 12.50 on 5.25 mean violations. The `±` is the standard deviation across seeds 0-19. GridWorld is the only scenario whose world is drawn from the seed; on the other three a non-zero std appears only on the `random` arm, whose baseline draws from it. The twenty grids are far less kind than the single seed-42 grid the suite used to run: governance records 0 deadlocks on 10 of the 20 seeds and 993-1,000 on the other 10
  - TemptationBank: 1998.0 reward, 0 violations — ban_loans contract enacts by step 30, steady 2/step thereafter
  - DriftLab: 1000.0 reward, 0 violations, 0.0 identity drift — identity coherence wins via higher priority tag; MonolithicRL reaches 4249.25 reward on 1,000 violations and 0.1647 drift. The reward and drift columns were structural zeros until #294; these come from a DriftLab-only re-run at 1,000 steps (deterministic for every strategy but Random, so the 2-seed values are the 20-seed means — confirmed at `--seeds 20` in #301)
  - DeadlockMaze: 999 deadlocks — tighten_quorum passes, deadlock breaker fires, but cycle repeats
  - **Note**: All old benchmark runs were invalidated by the baseline-decoupling bug. Re-ran with fix — benchmarks now show meaningful strategy differentiation. Invalidated a second time by #301: the loop seed was stored in each report's metadata and handed to no scenario, so every std and bootstrap interval published before that fix described twenty repeats of one run. The figures above come from the re-run after it. Full outputs: `results/benchmark_results.json`, `results/benchmark_summary.csv`, `results/figures/`
- **Lean 4 formalization of the Identity Layer completed** (epic #69 closed 2026-08-10): five *Identity Layer* proof modules in `gov-budget-proof/` — IdentityTiers (Ch4 §3), IdentityGenesis (Ch4 §4), IdentityBuffer (Ch4 §5.2), IdentityHashes (Ch4 §2.1/§6.1), IdentityCoherence (Ch4 §6.1). Merged to main via stacked PRs #195–#199 (stack #200, main `f56efa4`); all CI green with `lean-build` enforced on every PR. Inventory page: `book/formal-verification-lean.md`.
- **Lean corpus, current state** (after adversarial-audit epic #287): seven proof modules plus the manifest — the five above, BudgetEnforcement and VoteAndFalsification; `Basic.lean` was deleted by #298 as an unused `lake new` template. 102 theorems, zero `sorry`, zero axioms declared by the corpus, no Mathlib or other dependency; `lake build` reports 20 jobs. **Nothing mechanically connects any of it to `src/nomos/`** — no extraction, no refinement argument, no differential test — so a green `lean-build` means the proofs compile, not that the implementation is verified (#297). Never call the *implementation* verified — `lean-build` never runs `src/nomos/`. It does verify the Lean model: the kernel re-checks every theorem, and the job then enforces no classical axiom, no corpus-declared axiom and no native decision, so "CI verifies the Lean model" is a true sentence and "CI verifies Nomos" is not. The badge reads "proofs build" because the badge is about the build. The calibrated statement lives in `book/formal-verification-lean.md` § Scope and limits and `book/chapter-05/05-related-work.md` §7.

### Active
- **Track A done (2026-08-11)**: #181 (auto-refresh → #75) and #182 (health endpoints → #163) both merged; Track J probe prerequisite unlocked.
- **Track I done (2026-08-11)**: #217/#218/#219 all merged; v0.10.0 released via release-please. GHCR publish now triggers on `release: [published]` + `workflow_dispatch` (API-created tags fire no `push` event — the original trigger never ran); v0.10.0 image backfilled (`ghcr.io/nomos-n4s/nomos:0.10.0`, `:latest`, `:with-rl`).
- **Boards+roadmap normalized** (2026-08-10): board statuses now evidence-based (Backlog/Ready/In progress/In review/Done), priorities P0/P1/P2 assigned per ROADMAP.md. 21 stale nomos-website items removed from project board.
- External contributors engaging (shree24-06 on #75/#163; RISO525 on #67). Watchful review on all PRs.
- **#71** OSF registration closed as done — AGENTS.md line above should be reconciled against https://osf.io/ status before relying on it.

### Blocked
- (none)

## Roadmap

Ordered execution plan lives in **`ROADMAP.md`** (board-backed, https://github.com/users/xcoder-es/projects/3). Execution-plan decisions 2026-08-11: Azure-first deployment (one cloud green before multi-cloud), release-please automation, deploy-first Track E reorder (#161 → first deployment → #164 → #165 → #162/#167 → #166/#168), native components evidence-gated. Tracks:

1. **Track A — DONE (2026-08-11)** — #181 (auto-refresh → #75) and #182 (health endpoints → #163 + Track J probe prerequisite) merged.
2. **Track B** — close Phase C (#58): #73 → #74 → Streamlit Cloud deploy (lite path, parallel with Track J).
3. **Track C** — Phase D dashboard narrative (#59): #77 → #76 → #78.
4. **Track D — DONE** — rebrand #86 closed 2026-08-11 (with slices #202/#203/#204 + residue sweep `8ef6e7f`).
5. **Track E** — observability (#158), deploy-first order: #161 (DONE) → #164 (tamper-evident audit, next) → Track J deployment → #165 → #162/#167 → #166 → #168.
6. **Track F** — SDK (#159): #169 → #170 → #171 → #172 → #174 → #173 (PyPI as `nomos-n4s`); #172 gates Track L.
7. **Track G (parallel)** — Lean proofs: Identity Layer done (epic #69 closed 2026-08-10, stack #200 merged); TEE isolation model (#70) next.
8. **Track H (gated)** — commercialization (#160): #175 legal gate → #176/#177; #180 anytime; #179 deferred.
9. **Track I — DONE (2026-08-11)** — release & delivery (#213): #217 GHCR publish (trigger fixed: `release: [published]` + dispatch; v0.10.0 image backfilled) → #218 release-please (v0.10.0 released) → #219 coverage gate (PR #237, 90%).
10. **Track J (P1, gate #161+#182 now OPEN)** — one-cloud Azure (#214): #220 ADR → #221 Pulumi ACA IaC → #222 verification run. GHCR artifacts available (v0.10.0).
11. **Track K (P2, gate J green)** — multi-cloud (#215): #223 AWS → #224 GCP → #225 parity matrix.
12. **Track L (P2, gates #172 + #226 evidence)** — native & performance (#216): #226 perf budget → #227 Rust feasibility → #228 Go feasibility → #229 atomicity ADR.

Phase D (validation) status: DSL ✅ (#131), AI Agent Validation ✅ (epic #145, all of #138–#144 closed 2026-08-01), website build in nomos-website repo, language-agnostic protocol = #172 (Track F).

Phase E (enterprise-readiness): plugin architecture = #173, real TEE integration = #176, expanded Lean proofs = Track G.

## Next Move
1. Track E-F4: **#164** tamper-evident audit log (the only pre-deployment E item).
2. Track J: #220 ADR → #221 Pulumi ACA → #222 verification (gate open; parallel Track B lite path #73 → #74).

## Relevant Files
- `book/chapter-01/01-why-ai-needs-a-governance-layer.md`: Chapter 1 — problem statement
- `book/chapter-02/02-neural-parliament.md`: Chapter 2 — Neural Parliament architecture (560 lines)
- `book/chapter-03/03-ulysses-contracts.md`: Chapter 3 — Ulysses Contracts formalism (359 lines)
- `book/chapter-04/04-identity-layer.md`: Chapter 4 — Identity Layer (573 lines)
- `book/chapter-05/05-related-work.md`: Chapter 5 — Related Work; four-axis comparison against the hard neighbors, honest deltas and concessions, "bounded autonomy" term attribution
- `references/bibliography.md`: living bibliography — hard-neighbor entries added 2026-08-13 (Alshiekh/Altman/Achiam/ToroIcarte/Dalrymple/Wang×2/Kaul/Ye/delaChica/Sohail/Guo)
- `book/appendix-a/tee-isolation.md`: TEE threat model, hardware watchdog, constant-time, Merkle-tree batching, single-enclave architecture, deadlock breaker
- `book/responses/response-to-review-panel.md`: all 5 phases of review responses (accepts all three Phase 5.2 fixes)
- `book/responses/response-to-expert-panel-harder-review.md`: response to second harder review (baseline bug fix, 11-point rebuttal)
- `book/formal-verification-lean.md`: Lean 4 proof inventory — the seven proof modules plus the manifest, a "Scope and limits" section on what the proofs are *not* about, and build instructions
- `gov-budget-proof/GovBudgetProof.lean`: Lean 4 manifest importing BudgetEnforcement, VoteAndFalsification, and the five Identity modules
- `gov-budget-proof/GovBudgetProof/IdentityTiers.lean`: tier mutability rules (Ch4 §3)
- `gov-budget-proof/GovBudgetProof/IdentityGenesis.lean`: 3-of-5 multisig genesis (Ch4 §4)
- `gov-budget-proof/GovBudgetProof/IdentityBuffer.lean`: sandboxed isolation buffer protocol (Ch4 §5.2)
- `gov-budget-proof/GovBudgetProof/IdentityHashes.lean`: runtime integrity hash chains, tamper evidence (Ch4 §2.1/§6.1)
- `gov-budget-proof/GovBudgetProof/IdentityCoherence.lean`: coherence threshold guard (Ch4 §6.1)
- `src/nomos/speaker.py`: Speaker state machine reference implementation
- `src/nomos/models.py`: Core data types
- `src/nomos/committee/members.py`: 7 Parliament members
- `src/nomos/identity/`: Ontology, commitments, tiers, keys, params, extension sandbox
- `src/nomos/contracts/`: Contract lifecycle, three enforcement modes, mask merger
- `src/nomos/tee/`: Simulated enclave, Merkle batch verification, watchdog, deadlock breaker
- `src/nomos/experiments/`: Grid world, temptation bank, identity drift, deadlock maze
- `src/nomos/benchmarks/baselines.py`: 4 comparison strategies (MonolithicRL, Random, StaticMasking, VetoOnly)
- `src/nomos/benchmarks/analysis.py`: Statistical pipeline — bootstrap CIs, Cohen's d, reward-hacking detection
- `src/nomos/benchmarks/figures.py`: Publication-ready plots — reward curves, violation rates, deadlock frequency, Pareto frontier
- `src/nomos/runner.py`: CLI entry point (`python -m src.nomos.runner all --baselines --steps 1000 --seeds 20`)
- `src/nomos/dsl/`: Parser (`parser.py`), validator (`validator.py`), models (`models.py`), errors (`errors.py`)
- `.gitignore`: excludes `*brainstorm.txt` and `reviews.txt`
- `examples/`: Example `.parliament` config files for all four experiment scenarios
