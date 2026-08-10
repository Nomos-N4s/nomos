## Objective
- Develop a formal theoretical framework for self-governing AI around the Neural Parliament, Ulysses Contracts, and an Identity Layer — now with a full reference implementation under active construction.
- Register the framework on OSF for timestamp provenance and DOI.

## Important Details
- Author: **Carlos Pinto (xcoder-es)** — solo software builder, not an academic. Repo is `xcoder-es/governance-layer`. All inquiries to capintobe@gmail.com.
- All Mermaid diagrams and LaTeX must avoid HTML tags (`<br/>`), custom `classDef` styling, and nested `\text{}` for GitHub compatibility. Use `\mathrm{}` instead.
- **First review panel** (5 rounds) completed theoretical vetting across all three layers. All accepted fixes executed. Panel signed off. Three residual risks acknowledged (social engineering, hardware supply chain, adaptive proxy gap) as unavoidable physical-world limits.
- **Second harder review panel** (2026-07-26) evaluated the implementation with grade C-. One genuine bug found (baseline decoupling in benchmarks) and fixed. Full response at `book/responses/response-to-expert-panel-harder-review.md`.
- OSF preregistration prepared — content at `osf-registration.md`. Needs manual upload to https://osf.io/ to mint DOI.
- **CLA.md** added — standard Individual Contributor License Agreement. External contributors must accept terms (PR = acceptance). CONTRIBUTING.md updated to reference it.
- Architecture: Capability → Governance → Identity. Deep learning, JEPA world models, and computer vision are Capability Layer technologies; the Governance Layer constrains them.

## Work State
### Completed
- **Chapters 1-4** — All written. Ch1 (motivation), Ch2 (Neural Parliament, 560 lines), Ch3 (Ulysses Contracts, 359 lines), Ch4 (Identity Layer, 573 lines). Ch4 includes: formal tuple $\mathcal{I} = \langle \mathcal{O}, \mathcal{C}_{\text{core}}, \mathcal{K}, \mathcal{P} \rangle$, four-tier mutability, genesis bootstrapping with 3-of-5 multisig, ontology extension with sandboxed isolation buffer (empirical property measurement via independent monitors), runtime integrity hashes for action bindings, liveness exception for hardware deadlock breaker, constitutional contracts.
- **Appendix A** — TEE threat model, SGX/SEV/TrustZone, hardware watchdog, constant-time execution, Merkle-tree batch verification, single-enclave architecture with multi-enclave consensus addendum, deadlock breaker cold-boot recovery (§A.9.5).
- **Response to review panel** — `book/responses/response-to-review-panel.md`. All 5 phases documented. Phase 5.2 concedes all three Chapter 4 Identity Layer attacks: isolation buffer sandbox (§5.2 fix), runtime integrity hashes (§2.1/§6.1 fix), deadlock breaker (§A.9.5 fix).
- **MVP code** — `src/governance/speaker.py`. Reference implementation with deterministic falsification counter. Runs successfully.
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

- **Neo4j integration**: `Neo4jBackend` in `src/governance/ontology/neo4j_backend.py` is fully wired into the Streamlit dashboard. When `NEO4J_URI` is present in `.env`, the dashboard auto-detects and uses Neo4j Aura for persistent ontology storage and decision logging. Falls back to `MemoryBackend` otherwise. Decision logging records each replayed step's scores, vetoes, and metadata as ontology entities. (Issue #21 — Integrated into dashboard per Option A.)

- **Phase D: AI Agent Validation completed** (epic #145, all of #138–#144 closed 2026-08-01): PydanticAI/OpenRouter adapter, governed-vs-ungoverned harness, 4 LLM-native scenarios, metrics/reports, trace viewer, repro+CI smoke, 12-prediction cross-validation.
- **Benchmark results** (4 scenarios × 5 strategies × 20 seeds × 1,000 steps = 400 runs, 6.3s wall-clock):
  - GridWorld: 3.0 reward, 0 violations across all strategies — sparsity limits poison encounters
  - TemptationBank: 1998.0 reward, 0 violations — ban_loans contract enacts by step 30, steady 2/step thereafter
  - DriftLab: 0 reward, 0 violations — identity coherence wins via higher priority tag
  - DeadlockMaze: 999 deadlocks — tighten_quorum passes, deadlock breaker fires, but cycle repeats
  - **Note**: All old benchmark runs were invalidated by the baseline-decoupling bug. Re-ran with fix — benchmarks now show meaningful strategy differentiation. Full outputs: `results/benchmark_results.json`, `results/benchmark_summary.csv`, `results/figures/`

### Active
- **PRs in review**: #181 (auto-refresh, closes #75) and #182 (health endpoints, closes #163) — maintainer review posted change requests as inline comments only. Awaiting author updates. Track A of ROADMAP.md.
- **Boards+roadmap normalized** (2026-08-10): board statuses now evidence-based (Backlog/Ready/In progress/In review/Done), priorities P0/P1/P2 assigned per ROADMAP.md. 21 stale nomos-website items removed from project board.
- External contributors engaging (shree24-06 on #75/#163; RISO525 on #67). Watchful review on all PRs.
- **#71** OSF registration closed as done — AGENTS.md line above should be reconciled against https://osf.io/ status before relying on it.

### Blocked
- (none)

## Roadmap

Ordered execution plan lives in **`ROADMAP.md`** (board-backed, https://github.com/users/xcoder-es/projects/3). Tracks:

1. **Track A (now)** — merge #181 (auto-refresh → #75) and #182 (health endpoints → #163).
2. **Track B** — close Phase C (#58): #73 → #74 → Streamlit Cloud deploy.
3. **Track C** — Phase D dashboard narrative (#59): #77 → #76 → #78.
4. **Track D** — rebrand #86 (`governance-layer` → `nomos`) before SDK/observability land.
5. **Track E** — observability (#158): #161 → #162 → #167 → #166 → #164 → #165 → #168.
6. **Track F** — SDK (#159): #169 → #170 → #171 → #172 → #174 → #173 (PyPI as `nomos-n4s`).
7. **Track G (parallel)** — Lean proofs #69 (Identity) and #70 (TEE).
8. **Track H (gated)** — commercialization (#160): #175 legal gate → #176/#177; #180 anytime; #179 deferred.

Phase D (validation) status: DSL ✅ (#131), AI Agent Validation ✅ (epic #145, all of #138–#144 closed 2026-08-01), website build in nomos-website repo, language-agnostic protocol = #172 (Track F).

Phase E (enterprise-readiness): plugin architecture = #173, real TEE integration = #176, expanded Lean proofs = Track G.

## Next Move
1. Track A: merge #181/#182 once authors address the inline change requests.
2. In parallel: pick up #73 (cloud-compat), #77 (annotations), #161 (JSON logging) — all P0.

## Relevant Files
- `book/chapter-01/01-why-ai-needs-a-governance-layer.md`: Chapter 1 — problem statement
- `book/chapter-02/02-neural-parliament.md`: Chapter 2 — Neural Parliament architecture (560 lines)
- `book/chapter-03/03-ulysses-contracts.md`: Chapter 3 — Ulysses Contracts formalism (359 lines)
- `book/chapter-04/04-identity-layer.md`: Chapter 4 — Identity Layer (573 lines)
- `book/appendix-a/tee-isolation.md`: TEE threat model, hardware watchdog, constant-time, Merkle-tree batching, single-enclave architecture, deadlock breaker
- `book/responses/response-to-review-panel.md`: all 5 phases of review responses (accepts all three Phase 5.2 fixes)
- `book/responses/response-to-expert-panel-harder-review.md`: response to second harder review (baseline bug fix, 11-point rebuttal)
- `src/governance/speaker.py`: Speaker state machine reference implementation
- `src/governance/models.py`: Core data types
- `src/governance/committee/members.py`: 7 Parliament members
- `src/governance/identity/`: Ontology, commitments, tiers, keys, params, extension sandbox
- `src/governance/contracts/`: Contract lifecycle, three enforcement modes, mask merger
- `src/governance/tee/`: Simulated enclave, Merkle batch verification, watchdog, deadlock breaker
- `src/governance/experiments/`: Grid world, temptation bank, identity drift, deadlock maze
- `src/governance/benchmarks/baselines.py`: 4 comparison strategies (MonolithicRL, Random, StaticMasking, VetoOnly)
- `src/governance/benchmarks/analysis.py`: Statistical pipeline — bootstrap CIs, Cohen's d, reward-hacking detection
- `src/governance/benchmarks/figures.py`: Publication-ready plots — reward curves, violation rates, deadlock frequency, Pareto frontier
- `src/governance/runner.py`: CLI entry point (`python -m src.governance.runner all --baselines --steps 1000 --seeds 20`)
- `src/governance/dsl/`: Parser (`parser.py`), validator (`validator.py`), models (`models.py`), errors (`errors.py`)
- `.gitignore`: excludes `*brainstorm.txt` and `reviews.txt`
- `examples/`: Example `.parliament` config files for all four experiment scenarios
