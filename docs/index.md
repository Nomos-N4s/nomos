---
title: "Governance Layer: bounded autonomy for autonomous AI"
description: "Governance Layer is a formal framework that bounds autonomous AI with a Neural Parliament, Ulysses Contracts, and a verifiable Identity Layer."
---

# Governance Layer

## Provably Bounded Governance for Autonomous AI

**Created by Carlos Pinto (xcoder-es)**

Neural Parliament • Ulysses Contracts • Identity Layer

A formal framework for bounded autonomous decision-making.

**Explore**

- [Theory](book/00-preface.md)
- [API](api/index.md)
- [Benchmarks](benchmarks/index.md)
- [GitHub](https://github.com/xcoder-es/governance-layer)

---

## Why

Optimization pressure erodes constraints that are not formally enforced. Governance Layer bounds autonomous behavior through deliberation, contracts, and a verifiable identity model before actions are executed.

## Architecture at a Glance

```mermaid
flowchart LR
    A[Proposal] --> B{Neural Parliament}
    B -->|Approve| C[Ulysses Contract]
    C --> D[Identity Layer]
    D --> E[Bounded Action]
    B -->|Reject| F[Discard]
```

## Key Numbers

| Feature | Value |
|---------|------:|
| Parliament members | **7** |
| κ modes | **3** |
| Mutability tiers | **4** |
| Verified predictions | **12** |

## Quick Start

```bash
pip install -e ".[rl,minigrid]"
python -m src.governance.runner speaker
```

---

## Explore More

- [Theory](book/00-preface.md)
- [API](api/index.md)
- [Benchmarks](benchmarks/index.md)
- [GitHub](https://github.com/xcoder-es/governance-layer)

## License

Licensed under the [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) license.