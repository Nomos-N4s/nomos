# Governance Layer

**A Formal Framework for Self-Governing AI**

*Created by Carlos Pinto (xcoder-es)*

The Governance Layer is a reference implementation of a formal framework for constraining AI agents through a Neural Parliament, Ulysses Contracts, and an Identity Layer. It ensures that autonomous systems remain safe, aligned, and corrigible — even under optimization pressure.

## Quick Start

```bash
pip install -e ".[rl,minigrid]"
python -m src.governance.runner speaker
python -m src.governance.runner all --baselines --steps 1000 --seeds 5
```

## Key Concepts

- **Neural Parliament** — Seven specialized committees (Reward, Safety, Curiosity, Planning, Memory, Social, Integrity) that score and vote on agent proposals using weighted range voting.
- **Ulysses Contracts** — Pre-commitment mechanisms that restrict the agent's future action space. Enacted by supermajority, revoked only by unanimity.
- **Identity Layer** — Formal ontology + core commitments + mutability tiers + genesis 3-of-5 multisig + bounded parameter envelope.
- **Gradient Barrier** — The governance decision's gradient with respect to any member's proposal function is zero, preventing gradient-based attacks.
- **κ₂ Budget Enforcement** — No member may submit more proposals than their allocated budget in a single governance cycle.

## Formal Verification

The framework includes Lean 4 proofs of core invariants:

- `budget_invariant_holds`: Budget enforcement (κ₂) preserved across all governance cycles
- `vote_resolution_deterministic`: Vote outcomes are deterministic
- `budget_preserves_positive`: Falsification mechanism never drops budget below 1
- `falsification_params_are_immutable`: Falsification threshold and cutoff are immutable-tier

## Dashboard

```bash
streamlit run src/governance/dashboard/app.py
```

Provides interactive visualization of:
- Formal model state (Identity tuple, predictions)
- Parliament voting (step-by-step replay)
- Benchmark comparisons (effect sizes, CIs)
- RL training results (governed vs ungoverned)

## Citation

```bibtex
@software{governance_layer,
  author = {Carlos Pinto (xcoder-es)},
  title = {The Governance Layer: A Formal Framework for Self-Governing AI},
  year = {2026},
  url = {https://github.com/xcoder-es/governance-layer}
}
```

## License

This work is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
