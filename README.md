# Governance Layer

> **An architectural specification and reference implementation for self-governing artificial intelligence.**
> The Neural Parliament, Ulysses Contracts, and Identity Layer — with a full reference implementation.

**Created by Carlos Pinto (xcoder-es).**

**Maturity: Pre-alpha research prototype.** The theoretical framework has undergone 5 rounds of adversarial review by an independent expert panel (see [`book/responses/`](book/responses/)). The reference implementation is under active construction. Claims about security, formal verification, and production readiness are aspirational.

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](LICENSE)
[![Changelog](https://img.shields.io/badge/Changelog-CHANGELOG.md-blue)](CHANGELOG.md)
[![Security](https://img.shields.io/badge/Security-SECURITY.md-blue)](SECURITY.md)
[![Tests](https://github.com/xcoder-es/governance-layer/actions/workflows/tests.yml/badge.svg)](https://github.com/xcoder-es/governance-layer/actions/workflows/tests.yml)
[![Docs](https://github.com/xcoder-es/governance-layer/actions/workflows/docs.yml/badge.svg)](https://github.com/xcoder-es/governance-layer/actions/workflows/docs.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)

---

## Quick Start

```bash
# Run the Neural Parliament speaker demo
python -m src.governance.runner speaker

# Run all governance experiments
python -m src.governance.runner all

# Full benchmark: all strategies, 1000 steps, 20 seeds
python -m src.governance.runner all --baselines --steps 1000 --seeds 20
```

---

## For Researchers

The Governance Layer proposes that intelligence is not solely optimization of actions, but also the **governance of objectives, deliberation, and future decision spaces**. This repository contains both the formal theory and a complete reference implementation.

### Theory (The Book)

| Chapter | Topic | Lines |
|---------|-------|-------|
| [Chapter 1](book/chapter-01/01-why-ai-needs-a-governance-layer.md) | Why AI needs a governance layer | Motivation |
| [Chapter 2](book/chapter-02/02-neural-parliament.md) | Neural Parliament architecture | 560 |
| [Chapter 3](book/chapter-03/03-ulysses-contracts.md) | Ulysses Contracts formalism | 359 |
| [Chapter 4](book/chapter-04/04-identity-layer.md) | Identity Layer | 573 |
| [Appendix A](book/appendix-a/tee-isolation.md) | TEE threat model & hardware isolation | SGX/SEV/TrustZone |

The theory was vetted through 5 rounds of adversarial review by an independent panel. Three residual physical-world risks are acknowledged (social engineering, hardware supply chain, adaptive proxy gap).

### Testable Predictions

12 formal predictions (4 per chapter) are implemented and verified in `src/governance/prove/`. Results in [`results/prove_results.json`](results/prove_results.json).

### Benchmark Results

4 scenarios &times; 5 strategies &times; 20 seeds &times; 1000 steps = 400 runs:

| Scenario | Governance | MonolithicRL | Random | StaticMasking | VetoOnly |
|----------|-----------|-------------|--------|--------------|----------|
| **GridWorld** | 3.0 / 0 viol | 3.0 / 0 | 3.0 / 0 | 3.0 / 0 | 3.0 / 0 |
| **TemptationBank** | 1998.0 / 0 | 1998.0 / 0 | 1998.0 / 0 | 1998.0 / 0 | 1998.0 / 0 |
| **DriftLab** | 0.0 / 0 | 0.0 / 0 | 0.0 / 0 | 0.0 / 0 | 0.0 / 0 |
| **DeadlockMaze** | 0.0 / 999 dlock | 0.0 / 999 | 0.0 / 999 | 0.0 / 999 | 0.0 / 999 |

Full analysis: [`results/benchmark_summary.csv`](results/benchmark_summary.csv) &middot; [`results/benchmark_results.json`](results/benchmark_results.json) &middot; [`results/figures/`](results/figures/)

---

## For Developers

### Architecture

The reference implementation follows the formal theory layer by layer:

```
                    ┌──────────────────────┐
                    │       Speaker         │
                    │  (State Machine)      │
                    └──────┬───────┬────────┘
                  ┌────────┘       └────────┐
          ┌───────▼──────┐          ┌───────▼──────┐
          │   Parliament  │          │   Contracts   │
          │  7 Members    │          │  3 κ Modes    │
          │  Budget/Veto  │          │  Mask Ops     │
          └───────┬───────┘          └───────┬───────┘
                  └────────┬─────────────────┘
                           ▼
                    ┌──────────────┐
                    │  Identity    │
                    │  Layer       │
                    │  4 Tiers     │
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │  TEE Enclave │
                    │  (Simulated) │
                    └──────────────┘
```

### Project Structure

```
src/governance/
├── models.py          # Core data types
├── speaker.py         # Neural Parliament Speaker state machine
├── runner.py          # CLI entry point
├── committee/         # 7 Parliament member implementations
├── contracts/         # Ulysses Contracts lifecycle & enforcement
├── identity/          # Ontology, commitments, tiers, keys
├── ontology/          # Storage: MemoryBackend (default) + Neo4jBackend (optional)
├── tee/               # Simulated enclave, watchdog, Merkle batching
├── experiments/       # 4 experimental scenarios
├── benchmarks/        # Baselines, analysis, figures
└── dashboard/         # Streamlit UI: Formal Model, Parliament Live, Benchmarks
```

### Ontology Backend

The dashboard supports two ontology storage backends:

- **MemoryBackend** (default): in-memory dicts, no dependencies, ephemeral
- **Neo4jBackend** (optional): persistent storage via Neo4j Aura

To enable Neo4j, create a `.env` file in the project root:

```bash
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
```

The dashboard auto-detects Neo4j credentials and uses them for ontology entity storage and decision logging. Falls back to `MemoryBackend` when unavailable.

### Implementation Properties

- **Fully algorithmic** — no neural networks, no gradients, no learned parameters
- **Deterministic** — same inputs always produce same outputs
- **Gradient barrier** — discrete protocol operations break backpropagation
- **SDoS-resistant** — proposal budgets and priority tags prevent flooding

### Running Experiments

```bash
# Single scenario
python -m src.governance.runner gridworld --steps 1000

# With baselines
python -m src.governance.runner all --baselines

# Selective strategies
python -m src.governance.runner all --baselines --strategies governance,random,veto_only

# Multi-seed benchmark with CSV export
python -m src.governance.runner all --baselines --steps 1000 --seeds 20 --csv

# Formal prediction verification
python -m src.governance.runner prove --all
python -m src.governance.runner prove --ch2 --json results/ch2.json
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Citation

```bibtex
@software{governance_layer,
  author    = {Carlos Pinto (xcoder-es)},
  title     = {The Governance Layer: An Architectural Specification for Self-Governing AI},
  year      = {2026},
  url       = {https://github.com/xcoder-es/governance-layer},
  note      = {OSF preregistration pending},
}
```

---

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 1 &mdash; Evidence | Benchmarks, CLI, analysis, figures | ✅ Complete |
| 2 &mdash; OSF Preregistration | DOI, abstract, preregistration | 📋 Deferred — preregistration must precede experiments for scientific credibility; current benchmarks are development validation only |
| 3 &mdash; Interface Polish | README, docs polish | ▶ In progress |
| 4 &mdash; Book Completion | Appendices B-E | ✅ Complete |
| 5 &mdash; Robustness | Tests, package exports, cleanup | ✅ Complete |

See the [GitHub Project Board](https://github.com/xcoder-es/governance-layer/projects) for detailed tracking.

---

## License

This work is licensed under [CC BY 4.0](LICENSE).
