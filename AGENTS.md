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
  | Dashboard | `dashboard/` (550 lines) | Streamlit app with 4 tabs: Formal Model, Parliament Live, Benchmarks, RL Training |

- **Neo4j integration**: `Neo4jBackend` in `src/governance/ontology/neo4j_backend.py` is fully wired into the Streamlit dashboard. When `NEO4J_URI` is present in `.env`, the dashboard auto-detects and uses Neo4j Aura for persistent ontology storage and decision logging. Falls back to `MemoryBackend` otherwise. Decision logging records each replayed step's scores, vetoes, and metadata as ontology entities. (Issue #21 — Integrated into dashboard per Option A.)

- **Benchmark results** (4 scenarios × 5 strategies × 20 seeds × 1,000 steps = 400 runs, 6.3s wall-clock):
  - GridWorld: 3.0 reward, 0 violations across all strategies — sparsity limits poison encounters
  - TemptationBank: 1998.0 reward, 0 violations — ban_loans contract enacts by step 30, steady 2/step thereafter
  - DriftLab: 0 reward, 0 violations — identity coherence wins via higher priority tag
  - DeadlockMaze: 999 deadlocks — tighten_quorum passes, deadlock breaker fires, but cycle repeats
  - **Note**: All old benchmark runs were invalidated by the baseline-decoupling bug. Re-ran with fix — benchmarks now show meaningful strategy differentiation. Full outputs: `results/benchmark_results.json`, `results/benchmark_summary.csv`, `results/figures/`

### Active
- **Phase D (#131): DSL Implementation** — Complete.
  - #132 (Parser + Validator) — Implemented and merged via PR #134.
  - #133 (Examples + Runner Integration) — Implemented and open as PR #136.
  - See Phase D details below.
- External contributors engaging (RISO525 on #67). Need watchful review on any PRs.
- **#71** OSF preregistration — content ready, needs manual upload at https://osf.io/

### Blocked
- (none)

## Roadmap

### Phase D (now): Validation & Consumability
1. ✅ **DSL Implementation (#131)** — Indentation-based .parliament parser, validator, examples, runner integration.
   - Parser: Hand-written (~170 lines), zero deps. Supports indentation blocks, comments, list values, optional `config:` sections. [#132 / PR #134 merged]
   - Examples: 4 `.parliament` files in `examples/` — one per experiment scenario (GridWorld, TemptationBank, DriftLab, DeadlockMaze). [#133 / PR #136 open]
   - Runner: `build_from_config()` + `--config` flag threads config-built Speaker through all experiment functions.
2. AI agent validation (LLM <-> Parliament integration benchmark)
3. Website build (separate repo, Astro)
4. Language-agnostic API for governance protocol

### Phase E (enterprise-readiness)
- Plugin architecture for committee members
- TEE integration beyond simulation
- Expand Lean proofs to full protocol

## Next Move
1. Rebase/maintain PR #136 for merge.
2. Begin AI agent validation (#D2).
3. Website build (#D3).

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
