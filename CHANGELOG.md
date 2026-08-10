# Changelog

All notable changes to the Governance Layer project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- MkDocs Material documentation build system (`mkdocs.yml`, `docs/`)
- GitHub Actions workflow to build and deploy docs to GitHub Pages
- GitHub Project #3 for issue tracking with 4 epics (A–D)
- End-to-end pipeline integration test (mini benchmark → analysis → figures → export) (#103)
- Hypothesis property-based tests for contracts (mask merger, enforcement, timelock), Identity Layer (tier rules, multisig thresholds, ontology hashes), and TEE (watchdog, Merkle trees, constant-time ops) (#104)
- Benchmark smoke test job in CI (`benchmark-smoke` in `.github/workflows/tests.yml`) (#105)
- Formal prediction cross-validation harness (#144): 12-prediction confirmation table, adversarial edge-case catalog, sensitivity analysis, and `prove-agent` CLI subcommand

### Changed
- Aligned all four benchmark figures with analysis pipeline: reward curves use bootstrap CIs instead of parametric error; violation rate and deadlock frequency bar charts use bootstrap CI error bars instead of stdev; Pareto frontier overlay added; color palette unified across all figure types (#101)

## [0.7.0] — 2026-07-26

### Added
- RL Training Results dashboard tab (Tab 4) with governed vs ungoverned comparison
- Neo4j `rl_run` entity logging for MLflow-like experiment tracking
- Lean 4 formal proofs for budget enforcement (κ₂) and vote threshold invariants

### Fixed
- Baseline decoupling bug in benchmarks (all prior results invalidated; re-ran)

## [0.6.0] — 2026-07-20

### Added
- Property-based test suite for Speaker state machine (Hypothesis, ~1000 cases)
- TEE module tests for enclave, batch verification, watchdog, constant_time
- Fuzzing tests for edge cases and extreme inputs
- PPO training script for GovernanceGridWorld (`scripts/train_governance_grid_world.py`)
- RL comparison plots script (`scripts/rl_comparison_plots.py`)
- Minigrid environment wrapping with Neural Parliament governance
- Safety-constrained environments (Safety-Gymnasium-based)
- Colab GPU training notebook with Minigrid + Safety-Gymnasium

### Fixed
- MRO crash on Colab for GovernanceGridWorld (gym/gymnasium dual-inheritance)
- Robust Safety-Gymnasium install in Colab notebook

## [0.5.0] — 2026-07-15

### Added
- Comprehensive Mermaid architecture diagrams in book chapters
- Neo4j integration: `Neo4jBackend` in ontology package wired to Streamlit dashboard
- Decision logging records each replayed step as ontology entities
- Multi-enclave consensus addendum in Appendix A

## [0.4.0] — 2026-07-10

### Added
- Full modular reference implementation (~2100 lines):
  - Core types (`models.py`), 7 Parliament members, Identity Layer (383 lines)
  - Ulysses Contracts lifecycle, 3 enforcement modes, mask merger
  - TEE simulation (enclave, Merkle batch, watchdog, constant-time, deadlock breaker)
  - Speaker state machine with budgets, agenda sorting, scoring, vetoes, weighted voting
- Benchmark suite (4 scenarios × 5 strategies × 20 seeds):
  - `baselines.py`, `run_all.py`, `report.py`, `analysis.py`, `figures.py`
- CLI entry point (`runner.py` with `--baselines`, `--strategies`, `--steps`, `--seeds`, `--csv`)
- Streamlit dashboard (3-tab: Formal Model, Parliament Live, Benchmarks)
- Colab notebook (`notebooks/01-prove-tutorial.ipynb`)
- `prove.py`: 12 formal predictions from Chapters 2–4, all PASS

## [0.3.0] — 2026-07-01

### Added
- Appendix B: DSL Grammar for Parliament Configuration
- Appendix C: Data Types Reference
- Appendix D: Experiment Protocol & Reproducibility Checklist
- Appendix E: RL Adversary Results & Attack Patterns
- CSV export and steps/seeds validation in CLI
- PyTest test suite (unit + integration)

### Changed
- Rewrote README with hero section, quick-start, researcher/dev guide

## [0.2.0] — 2026-06-20

### Added
- Phase 1 benchmark suite: CLI, scaling, analysis, figures
- Gym environment (`GovernanceGridWorld`) with PPO training harness
- RL adversary CLI for testing governance robustness
- Ontology backends: abstract + in-memory + Neo4j
- Dashboard auto-detection of Neo4j from `.env`
- Final review panel response (Phase 5.2) with three fixes

### Changed
- Speaker state machine initialization to resolve sentinel-string bug

## [0.1.0] — 2026-06-10

### Added
- Theoretical framework: Chapters 1–4 and Appendix A
- Responses to first review panel (5 rounds, all fixes accepted)
- Reference implementation: Speaker state machine (deterministic falsification counter)
- Project setup: `pyproject.toml` (uv), `.env.example`, `results/` directory

## [0.0.1] — 2026-06-01

### Added
- Initial repository setup with README
- Chapter 1: problem statement and motivation
- Living bibliography system with 19 seed entries
