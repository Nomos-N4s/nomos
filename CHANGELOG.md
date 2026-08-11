# Changelog

All notable changes to the Nomos project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

> CHANGELOG.md is now maintained by release-please. Do not hand-edit this
> file — entries are generated from conventional-commit history on release.

## [0.9.0](https://github.com/Nomos-N4s/nomos/compare/v0.8.0...v0.9.0) (2026-08-11)


### Features

* /healthz, /readyz, /metrics endpoints for runner serve ([#163](https://github.com/Nomos-N4s/nomos/issues/163)) ([23ad445](https://github.com/Nomos-N4s/nomos/commit/23ad445fc4e748964787254501b1de3bf39747a6))
* auto-refresh toggle for live Colab-to-dashboard updates ([#75](https://github.com/Nomos-N4s/nomos/issues/75)) ([05f6791](https://github.com/Nomos-N4s/nomos/commit/05f6791881a61339b65233a4607cac872bbf9919))
* publish multi-arch OCI images to GHCR on version tags ([#217](https://github.com/Nomos-N4s/nomos/issues/217)) ([a04ef0d](https://github.com/Nomos-N4s/nomos/commit/a04ef0db50e4ce3d9af006657071a0f8528cb2f2))
* structured JSON logging foundation ([#161](https://github.com/Nomos-N4s/nomos/issues/161)) ([1c56550](https://github.com/Nomos-N4s/nomos/commit/1c56550ada7e795a19d688abe41d5ea796be5e3f))


### Bug Fixes

* rebrand paths in server docs, ruff-format readyz test (review [#182](https://github.com/Nomos-N4s/nomos/issues/182)) ([a4126a2](https://github.com/Nomos-N4s/nomos/commit/a4126a27da2029dcd5ffc46d0eb4f524a02f6121))
* remove duplicate changelog heading (review [#181](https://github.com/Nomos-N4s/nomos/issues/181)) ([8f2aec1](https://github.com/Nomos-N4s/nomos/commit/8f2aec1c67572955886a5b17a5e5ac6fbabcc977))


### Documentation

* add CHANGELOG entry for [#163](https://github.com/Nomos-N4s/nomos/issues/163) health endpoints ([a0b7b2b](https://github.com/Nomos-N4s/nomos/commit/a0b7b2b507bb464c044386919be6682f2d2ed472))
* add CHANGELOG entry for [#75](https://github.com/Nomos-N4s/nomos/issues/75) auto-refresh ([316dc75](https://github.com/Nomos-N4s/nomos/commit/316dc75cb4738d6498524fe0919c5fe6ce3a77e1))
* add release badge to README ([784bb8a](https://github.com/Nomos-N4s/nomos/commit/784bb8add5b7be7cd85c8d1a3679cd84a8c44cd0))
* add social preview image for repo card and link shares ([85170bd](https://github.com/Nomos-N4s/nomos/commit/85170bd0622d531e215e5779dfa8390d18e22f17))
* record uv and atomic-commit conventions in AGENTS.md ([b8bdf5d](https://github.com/Nomos-N4s/nomos/commit/b8bdf5d1a64b1a635e90b157c1cd5f7427d5b061))
* roadmap decision record - release/delivery, Azure-first deployment, native gates ([d273a3b](https://github.com/Nomos-N4s/nomos/commit/d273a3b752c80f4177d300fe550de1fb974d6271))

## [0.8.0] — 2026-08-11

### Added
- License moved to Apache-2.0 (was CC BY 4.0); LICENSE, README, CLA, and docs references aligned
- Docker build fixed: tests/ and examples/ now copied into the image, base stage is the default build target, .dockerignore added
- MkDocs Material documentation build system (`mkdocs.yml`, `docs/`)
- GitHub Actions workflow to build and deploy docs to GitHub Pages
- GitHub Project #3 for issue tracking with 4 epics (A–D)
- End-to-end pipeline integration test (mini benchmark → analysis → figures → export) (#103)
- Hypothesis property-based tests for contracts (mask merger, enforcement, timelock), Identity Layer (tier rules, multisig thresholds, ontology hashes), and TEE (watchdog, Merkle trees, constant-time ops) (#104)
- Benchmark smoke test job in CI (`benchmark-smoke` in `.github/workflows/tests.yml`) (#105)
- Formal prediction cross-validation harness (#144): 12-prediction confirmation table, adversarial edge-case catalog, sensitivity analysis, and `prove-agent` CLI subcommand
- Auto-refresh toggle for the RL Training tab: polls `results/rl/` every 30s, shows a last-updated timestamp and a "Live from Colab" indicator when new results land (#75)
- `/healthz`, `/readyz`, `/metrics` endpoints for `runner serve`: liveness, readiness (Speaker, TEE watchdog, deadlock breaker, backend), and Prometheus metrics via the optional `observability` extra (#163)

### Changed
- Aligned all four benchmark figures with analysis pipeline: reward curves use bootstrap CIs instead of parametric error; violation rate and deadlock frequency bar charts use bootstrap CI error bars instead of stdev; Pareto frontier overlay added; color palette unified across all figure types (#101)
- **Rebrand live (#86).** Package renamed `governance` → `nomos` in #205; this PR ports the docs/brand state to the published surface: `mkdocs.yml` now presents the site as **Nomos** with `site_url`/`repo_url` pointing at `xcoder-es/nomos` (repo renamed from `xcoder-es/governance-layer`, old URLs redirect). README headline, badges, and citation updated; API reference, book responses, and changelog index swept of stale `governance-layer` references; page-visible module docstrings (runner, prove, ontology) updated.

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
