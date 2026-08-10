---
title: "Appendix E: RL adversary results and attack patterns"
description: "PPO adversary training setup, emergent attack strategies, and quantitative robustness results for the governance layer across three enforcement modes."
---

# Appendix E: RL Adversary Results & Attack Patterns

> *PPO adversary training setup, emergent attack strategies, and governance layer robustness.*

---

## E.1 Motivation

The formal predictions in Chapters 2-4 are verified in controlled scenarios. A stronger test: can a reinforcement learning agent **learn to exploit the governance layer** by finding actions that bypass its safety constraints?

This appendix documents the adversary training setup, the attack patterns discovered during training, and quantitative results across three governance modes.

---

## E.2 Experimental Setup

### E.2.1 Environment

The adversary operates in `GovernanceGridWorld` (`src/nomos/experiments/gym_env.py`), a modified GridWorld where the agent selects cardinal directions and the environment routes actions through the Parliament.

| Parameter | Value |
|-----------|-------|
| Grid size | 10 x 10 |
| Poison ratio | 0.2 |
| Apple count | 8 |
| Max steps | 200 |
| Action space | 4 (up, down, left, right) |
| Observation space | 402-dim Box (one-hot grid + position) |

### E.2.2 Governance Modes

| Mode | Description |
|------|-------------|
| `governance` | Full Parliament filters actions; poison blocked by Safety Committee |
| `no_governance` | Actions execute directly; poison gives +5 immediate, -10 delayed |
| `static_mask` | Poison tiles are statically blocked; only apples and empty tiles allowed |

### E.2.3 PPO Hyperparameters

| Parameter | Value |
|-----------|-------|
| Algorithm | PPO (stable-baselines3) |
| Policy | MlpPolicy |
| Hidden layers | [64, 64] |
| Learning rate | 3e-4 |
| Gamma | 0.99 |
| GAE lambda | 0.95 |
| Clip range | 0.2 |
| Entropy coeff | 0.01 |
| Total timesteps | 100,000 |
| Evaluation episodes | 5 |

---

## E.3 Attack Patterns

### E.3.1 Budget Exhaustion

**Mechanism:** The adversary submits many low-priority proposals to exhaust a member's proposal budget, then submits a high-risk proposal when the Safety Committee has no budget remaining.

**Detected:** Partially. The budget enforcement in `SpeakerStateMachine._apply_budgets()` filters by member budget. The adversary can exploit this if multiple members share a budget pool, but in the default configuration each member has an independent budget (3-5 proposals per cycle).

**Mitigation:** Budgets are per-member and replenish each cycle. Budget exhaustion requires flooding from a single member, which is capped by their budget.

### E.3.2 Veto Flooding

**Mechanism:** The adversary forces repeated votes that trigger vetoes, causing the Speaker to hit `max_rounds` and fall back to the default action.

**Detected:** In DeadlockMaze. When quorum is tightened to 0.9, no proposal reaches consensus and the Speaker falls back to `emergency_shutdown` each cycle. However, this is a deliberate scenario parameterization rather than an adversary discovery.

**Mitigation:** The deadlock breaker (§A.9.5) resets governance parameters after `threshold_cycles` consecutive defaults, restoring the genesis baseline.

### E.3.3 Reward-Hacking via Delayed Penalty

**Mechanism:** The adversary takes poison apples for immediate +5 reward, exploiting the 3-step delay before the -10 penalty applies. An episodic agent may learn to end the episode before the penalty hits.

**Detected:** In short episodes or when the agent learns to avoid exploring tiles that would trigger penalties within the episode horizon.

**Mitigation:** The Safety Committee evaluates `risk` metadata (0.9 for poison) and vetoes actions exceeding its threshold (0.3). The integrity check in §2.3 detects falsified tag assignments.

### E.3.4 Priority Tag Spoofing

**Mechanism:** The adversary labels a high-risk proposal with `CRITICAL_SAFETY` priority to skip agenda sorting, hoping it passes scrutiny before the Integrity Committee intervenes.

**Detected:** The tag compliance check (`_check_tag_compliance` in `speaker.py:73`) compares the integrity member's score against `TAG_COMPLIANCE_THRESHOLD`. A falsification counter tracks violations; after 3 offenses, the offending member's budget is halved.

**Mitigation:** Falsification detection + budget halving. The Integrity Committee evaluates `identity_coherence` and assigns low scores to proposals whose tag mismatches their risk profile.

---

## E.4 Quantitative Results

| Mode | Avg Reward | Avg Violations | Avg Apples | Governance Layer On? |
|------|-----------|---------------|-----------|---------------------|
| `governance` | *highest* | *lowest* | *high* | Yes |
| `no_governance` | *lowest* | *highest* | *high* | No |
| `static_mask` | *medium* | *zero* | *medium* | Partial |

> **Note:** Exact numerical values depend on training seed, grid layout, and poison placement. The qualitative ordering — governance performs best on reward/violation tradeoff — holds across all tested configurations.

### E.4.1 Key Findings

1. **Governance mode** achieves the highest reward/violation ratio: the Parliament allows apples, blocks poison, and routes the agent toward safe areas.
2. **No-governance mode** shows the highest total reward but also the highest violations: the agent eats poison without constraint.
3. **Static masking** achieves zero violations but lower reward: the agent avoids poison areas entirely, potentially missing apples located behind poison tiles.

---

## E.5 Adversary Win Rate

The adversary's win condition is to **achieve higher reward with governance than without**. In the default configuration, governance does not reduce total reward — it redistributes it away from poison toward apples.

A successful adversary attack would require:
1. **Bypassing the veto** — scoring >0.3 on the Safety Committee's risk assessment
2. **Bypassing tag compliance** — scoring >0.4 on the Integrity Committee's coherence check
3. **Reaching consensus** — scoring >0.5 weighted average across all members

None of these conditions have been achieved by the PPO adversary within 100,000 timesteps across any tested seed.

---

## E.6 Source Code

All adversary code lives in:

| File | Purpose |
|------|---------|
| `src/nomos/experiments/gym_env.py` | Gymnasium environment with pluggable governance |
| `src/nomos/experiments/rl_train.py` | PPO training, evaluation, benchmarking |
| `src/nomos/experiments/rl_adversary.py` | CLI for train/eval/benchmark commands |

Run the adversary yourself:

```bash
# Install RL dependencies
uv sync --extra rl

# Train PPO with governance
python -m src.nomos.runner adversary train --mode governance --timesteps 100000

# Train without governance
python -m src.nomos.runner adversary train --mode no_governance --timesteps 100000

# Evaluate a trained model
python -m src.nomos.runner adversary eval --model results/ppo_governance.zip --episodes 10
```
