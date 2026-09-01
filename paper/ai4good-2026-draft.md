# Asserted-Metadata Safety Checks Fall to Optimization Pressure: A Pre-Registered Red-Team of a Multi-Agent Governance Layer

**Carlos Pinto** (independent researcher) — Nomos project, `github.com/Nomos-N4s/nomos`

*Draft for the AI4GOOD @ NeurIPS 2026 Multi-Agent Track (non-archival). 2–9 pages excl. references/appendices; this draft targets ~6. Every number below is reproduced by one command from the repository and matches the published record, which is held to the code by CI-enforced claim-pinning tests.*

---

## Abstract

A safety check that scores proposer-supplied metadata has zero adversarial value: a 64×64-MLP PPO policy, given 100,000 training steps and never told the mechanism, learned to silence it on 100% of its genuinely unsafe proposals, on every seed. Wherever an agent self-declares the risk of its own actions, this is the failure mode; at least one independently grounded verifier is load-bearing. We red-team a committee-based governance layer for agentic systems with a learned adversary under a pre-registered protocol (hypotheses, metrics, and thresholds committed and digest-chained before the runs). The metadata-trusting Safety committee fell completely and immediately; the layer nevertheless blocked all 4,762 adversarial unsafe actions — but only because one committee verifies claims against ground truth, a condition we annotate on every published verdict. A second pre-registered campaign degrades that verifier's accuracy ε from oracle to coin-flip and finds no cliff — yet its own validity hypothesis **failed** (the adversary could not make the game winnable at any ε under the registered metric), so we report the headline plateau as uninformative by our own pre-registered rule and salvage the attempt-level decomposition instead: across 80 governed runs, every one of the 299 successful bypasses was on a genuinely *ambiguous* action; 65,245 attempts against unmistakably unsafe actions failed at every ε down to 0.5. Verifier accuracy governs only the ambiguous fraction of the action space. We contribute the negative result, the decomposition, and a worked example of adversarially-audited, pre-registered safety evaluation by a solo researcher — including the audit that found our own benchmarks measuring nothing, and the remediation trail.

## 1. Introduction

A live design question in agent governance is where safety signals come from: agents increasingly *self-declare* the risk of their tool calls, their confidence, and their compliance, and pipelines increasingly score those declarations — while the alternative, independent policy engines that evaluate actions against ground truth, costs latency and engineering. This paper offers a clean, mechanized data point: in our system, the component that trusted self-declared risk was defeated *totally* — 100% of adversarial unsafe proposals, every seed — by a small policy that was never told how the check worked, within 100k steps of vanilla PPO. The component that checked ground truth was never beaten, and a follow-up campaign that degraded its accuracy localizes exactly where its protection lives.

**Contributions.**
1. **The negative result** (§4): asserted-metadata safety scoring contributes nothing under optimization pressure, demonstrated with a pre-registered protocol, controls that bracket the result, and per-seed values published.
2. **The frontier decomposition** (§5): degrading the grounded verifier's accuracy ε ∈ [0.5, 1.0] moves bypass only on *ambiguous* actions (299/299 of successful bypasses); unmistakably unsafe actions were never executed in 65,245 attempts at any ε. We also report that our pre-registered validity hypothesis for this campaign **failed**, and apply our own registered rule that this renders the plateau verdicts uninformative.
3. **A methodology artifact** (§3, §6): the full evaluation survived a 40-finding adversarial audit of the claim/code gap; every published verdict now carries its conditions at the point of quotation, pre-registration ordering is checkable by commit ancestry in one command, and benchmark honesty extends to reporting that a 12-line baseline matches the full deliberative machinery on 3 of 4 scenarios.

## 2. System under test

We test the reference implementation of *Nomos*, a committee-based governance layer. For this evaluation the relevant mechanism is deliberately small, and we describe only what the experiments exercise:

- A **Speaker** runs a governance cycle per step: proposals are budgeted (per-member cap κ₂ = 3), agenda-sorted by claimed priority tag, scored by committees, and passed or vetoed by weighted vote. The Speaker is the runtime gate.
- The **Safety committee** scores `1 − risk`, where `risk` is metadata **the proposer supplies**.
- The **Integrity committee** evaluates the proposal's claimed identity-coherence **against ground truth** (in the environment below, the true cell type), and low scores trip a falsification counter that halves the offender's proposal budget after 3 offences.

The environment is `GovernanceGridWorld` (10×10; 8 safe reward cells; unsafe "poison" cells pay +5 then −10). In adversarial mode the policy submits the *proposal itself*: direction, claimed priority tag, claimed risk and coherence (discretized), and a flood count up to 6 — action space `MultiDiscrete([4, 5, 3, 3, 6])`, observation 402-dim. The committees see the **claim**; the environment resolves the **truth**; falsification is thus well-defined.

## 3. Protocol and provenance

**Adversary.** PPO (stable-baselines3), MlpPolicy 64×64, lr 3e-4, 100,000 timesteps, seeds 42–46, evaluated deterministically over 10 episodes per seed. The adversary is rewarded **only** for defeating governance (`bypass` reward: +10 for an executed unsafe action, +1 shaping for silencing the Safety committee on a genuinely unsafe proposal); task reward is worthless to it.

**Modes.** `governance` (hypothesis under test), `no_governance` (ceiling control — nothing to bypass), `static_mask` (floor control — ground-truth filter, no Parliament).

**Pre-registration, checkable.** Hypotheses H1–H3 (and later H4–H7), metrics, and thresholds were committed before the runs. The registration document's SHA-256 is recorded in the published result artifact and recomputed by the validator; the certifying commit must be an ancestor of `HEAD` and have touched the file. Ordering is one command: `git merge-base --is-ancestor 15fd544 19d11ce` (registration precedes first results). Provenance-only edits are digest-chained with superseded values retained. A result with no verifiable pre-registration is not a weaker result; it is an unfalsifiable one.

## 4. Campaign 1: the defeat, then the conditional hold

**The defeat.** The trained policy silenced the Safety committee on **100% of its genuinely unsafe proposals, on every seed** — it learned, without being told the mechanism, to assert low risk on cells it knew to be unsafe, and Safety never vetoed one of them. Its entire achieved reward (95.24 ± 40.39) is accumulated silencing bonus: it never earned a single execution point.

**The conditional hold.** Zero of 4,762 adversarial unsafe attempts executed (bypass 0.000 [0.000, 0.000]); all three pre-registered hypotheses passed against ε = 0.01 thresholds — H1: zero over-budget cycles under 6-proposal floods (cap held at 3); H2: spoofed-priority unsafe actions executed at 0.000; H3: all 7,546 falsified proposals detected (rate 1.000). The controls bracket the result: `no_governance` bypass 1.000, `static_mask` 0.000.

**The conditions, on the verdicts.** Both PASS-columns carry two annotations wherever they are published, and we repeat them here rather than in a limitations appendix a citer will not read: (i) the verdicts hold *given the ground-truth-grounded Integrity verifier* — a layer whose committees all score asserted metadata would have been defeated outright; and (ii) H3's PASS is **partially by construction** — no spoof that could have beaten the grounded verifier was reachable in the adversary's vocabulary, so the 7,546 detections are not independent evidence of deterrence. The honest reading is not "the governance layer is robust"; it is that **defense in depth is load-bearing**: one of two veto committees fell completely and immediately, and the layer held because a second, independently grounded check existed behind it.

## 5. Campaign 2: the verifier-quality frontier, and a failed validity hypothesis

Campaign 1's hold rests on an oracle — ground-truth verification is free in a gridworld and free nowhere else. The second pre-registered campaign replaces the oracle with a verifier of tunable accuracy ε and sweeps 8 points × 2 training arms (reward-shaped and unshaped) × 5 seeds × 100k steps, with an anchor at ε = 1.0 and controls run under the swept environment.

| | Metric | Threshold | Result | Verdict |
|---|---|---|---|---|
| **H4** — plateau | max bypass at ε ≥ 0.95 | ≤ 0.05 | 0.0038 | PASS* |
| **H5** — no cliff above ε = 0.9 | max adjacent step | ≤ 0.15 | 0.0030 | PASS* |
| **H6** — game was winnable | bypass at ε = 0.5 | ≥ 0.05 | 0.0060 | **FAIL** |
| **H7** — shaping moves the search | shaped > unshaped; anchor ≤ 0.01 | both | 0.2982 > 0.2891 | PASS |

**H6 failed, and the pre-registered rule applies.** H6 was this campaign's validity check: if the adversary cannot reach ≥ 0.05 bypass even at a coin-flip verifier, then a flat curve certifies nothing about robustness — "held" against an adversary that could not play carries no information. By the rule registered before the runs, H4* and H5* are therefore reported as **uninformative**, not as evidence. In the registration's own post-mortem: *we pre-registered the wrong instrument* — overall bypass rate is diluted by attempts the adversary could never win.

**The salvage is the decomposition, and it is the finding.** Across all 80 governed runs the adversary attempted unsafe actions 79,264 times and executed 299 — and **every one of the 299 was on a genuinely ambiguous action** (cells whose unsafety the verifier's noise model can plausibly misread). In **65,245 attempts against unmistakably unsafe actions, across every ε down to 0.5, not one succeeded.** Degradation, where it exists, is graceful (largest adjacent step 0.0030). The transferable statement: **verifier accuracy governs only the genuinely ambiguous fraction of the action space** — for actions whose harm is legible in properties the proposer cannot claim over, independently grounded checks held at every accuracy level tested. Damage concentrates in ambiguity; that is where verifier quality buys protection, and the only place it does.

## 6. What a trivial baseline teaches, and the audit that made us say so

Honesty about the deliberative machinery itself: on the project's four benchmark scenarios, a **12-line filter** that accepts the first proposal whose *asserted* risk is below 0.3 matches the full committee apparatus on three, and loses only on the scenario whose environment was amended — after an adversarial audit — to *market* its temptation with a deceptively lowballed risk assertion. There, the trust-based filter takes all 100 teasers and eats all 100 delayed penalties; the enacted structural pre-commitment never sees the offer, because the restriction removes it from the agenda rather than scoring a metadata field. The through-line of both this and §4–5: **structure and grounding do the safety work; deliberation over asserted metadata does not.**

These evaluations did not start honest. An external adversarial audit filed 40 findings against the claim/code gap — among them: benchmark seeds that reached no scenario (every published standard deviation described twenty repeats of one run), a reward-hacking detector fed cumulative totals (97,599 spurious episodes), effect sizes that called a 6,863-point gap "negligible," two prediction tests that could not fail as written over invariants no code enforced, and a harness that handed baselines a stale agenda. All were remediated with the trail public; the summary tables now carry their caveats at the point of quotation, enforced by tests that recompute published claims against the tree in CI.

## 7. Related work

Constrained MDPs [Altman 1999; Achiam et al. 2017], reward machines [Toro Icarte et al. 2022], and shielding [Alshiekh et al. 2018] each bake safety into the learning problem or a synthesized runtime monitor; guaranteed-safe AI agendas [Dalrymple et al. 2024] target formal end-to-end guarantees. Our contribution is orthogonal and narrower: an *adversarial evaluation methodology* result about where governance-layer checks get their purchase (grounding, not assertion; ambiguity, not accuracy in the large), plus a reproducibility posture for solo-scale safety work. We have not run head-to-head comparisons against CMDP solvers, reward-machine agents, or synthesized shields, and we position rather than rank.

## 8. Limitations

(1) **Toy environment**: one 10×10 gridworld family; the negative result's mechanism (learned exploitation of self-reported metadata) is environment-generic, but the *hold* results are not. (2) **Scale**: 5 seeds, 100k steps, 64×64 policy — the zero-width bypass intervals bound exploit discovery at this budget, not in general. (3) **Vocabulary**: the adversary's attack surface is finite and, at the oracle anchor, contained no winning move — stated on every affected verdict. (4) **Single learned adversary** per run; no multi-agent collusion, no adaptive attacks against the falsification counter's memory. (5) The frontier's ambiguity fraction (0.5) is a design parameter; the decomposition's shape, not its constants, is the claim.

## 9. Reproducibility

Everything is one command from a public repository: the protocol (`python -m src.nomos.experiments.rl_adversary protocol --timesteps 100000 --seeds 42 43 44 45 46`), the sweep (`... rl_adversary sweep`), pinned dependencies (`uv sync --extra rl-repro`), a single seeding entry point, per-seed raw counts persisted into the committed campaign summaries, digest-chained pre-registration with ancestry-checkable ordering, and CI that recomputes the published claims against the tree — including the verbatim wording of this paper's first sentence.

---

*References to be formatted for the venue: Altman (1999) Constrained MDPs; Achiam et al. (2017) CPO; Toro Icarte et al. (2022) Reward Machines; Alshiekh et al. (2018) Safe RL via Shielding; Dalrymple et al. (2024) Guaranteed Safe AI; Schulman et al. (2017) PPO; Raffin et al. (2021) stable-baselines3.*
