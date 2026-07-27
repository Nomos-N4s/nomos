# OSF Preregistration — Governance Layer (Nomos)

Use the following content to register the project on OSF at https://osf.io/registrations.

---

## Title
Governance Layer: A Formal Framework for Self-Governing Artificial Intelligence

## Authors
Carlos Pinto (xcoder-es) — capintobe@gmail.com

## Description
The Governance Layer is a formal theoretical framework for self-governing AI, comprising three interconnected layers:

1. **Neural Parliament** — A committee-based deliberation architecture where specialised members (Reward, Safety, Curiosity, Planning, Memory, Social, Integrity) score, veto, and vote on proposed actions through weighted range voting.

2. **Ulysses Contracts** — Smart-contract-like binding commitments with three enforcement modes (procedural inertia, timelocks, stacked enforcement) that constrain future action spaces via mask composition.

3. **Identity Layer** — A four-tier mutability model (Constitutional → Dynamic → Operational → Immutable) bootstrapped via 3-of-5 genesis multisig, with sandboxed ontology extension and runtime integrity hashes.

The framework is accompanied by a full Python reference implementation (~2800 lines across 50+ files) including experiments, benchmarks, TEE simulation, statistical analysis, and a Streamlit dashboard.

## Background / Rationale
Current AI safety research focuses heavily on alignment (training objectives), interpretability (understanding internals), and capability limitations. Less attention is given to the architectural question: how should an AI system govern its own decision-making? This framework proposes that intelligence requires not only optimisation of actions but governance of objectives, deliberation, and future decision spaces. The theory has undergone two rounds of adversarial expert review (5 + 3 rounds) with all accepted fixes executed and three residual physical-world risks acknowledged.

## Hypotheses / Predictions
The framework makes 12 formal predictions across the three layers, implemented and verified in the reference implementation:

**Chapter 2 — Neural Parliament (4 predictions):**
- P01: Budget enforcement caps proposals per member
- P02: Priority sorting places CRITICAL_SAFETY before ROUTINE
- P03: Weighted voting outcome matches formal specification
- P04: Tag falsification halves budget after 3+ offences

**Chapter 3 — Ulysses Contracts (4 predictions):**
- P05: Contract restricts action set to allowed ∩ restricted
- P06: Revocation requires higher threshold than enactment
- P07: Timelock decrements monotonically, preventing immediate revocation
- P08: Mask composition follows (allowed − restricted)

**Chapter 4 — Identity Layer (4 predictions):**
- P09: Low-coherence proposals trigger integrity veto
- P10: Tier-4 (Constitutional) requires external multisig; lower tiers do not
- P11: Genesis 3-of-5 multisig: 2 sigs insufficient, 3 sigs authorise
- P12: Deadlock breaker fires after N defaults, then resets

## Design Plan
The reference implementation tests all 12 predictions deterministically. Benchmarks compare the Governance strategy against 4 baselines (MonolithicRL, Random, StaticMasking, VetoOnly) across 4 scenarios (GridWorld, TemptationBank, DriftLab, DeadlockMaze) with 20 random seeds and 1000 steps per run (400 runs total). Statistical analysis uses bootstrap confidence intervals and Cohen's d for effect size.

## Materials
Full reference implementation: https://github.com/xcoder-es/governance-layer

## Tags
AI safety, governance, neural parliament, ulysses contracts, identity layer, formal verification, lean 4

## License
CC BY 4.0 International
