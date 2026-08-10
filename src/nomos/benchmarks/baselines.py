"""
Alternative governance strategies for ablation comparison.

Each baseline replaces the full Speaker-based governance pipeline
with a simpler decision rule, allowing measurement of the marginal
benefit each governance component provides.

Four baselines:
- **MonolithicRL**: Picks the proposal with the highest ``expected_reward``
- **Random**: Picks a random proposal (decoupled from reward)
- **StaticMasking**: Applies a fixed blocklist, then max-reward selection
- **VetoOnly**: Accepts the first proposal whose risk is below a threshold

Real-world analogy:
    A clinical trial with a placebo arm. The baselines are placebos —
    they test whether the full governance mechanism actually adds value
    over simpler alternatives.
"""

import random
from abc import ABC, abstractmethod
from typing import Any

from ..models import GovernanceDecision, Proposal


class BaselineGovernance(ABC):
    """Abstract baseline: replace the Speaker with a simpler decision rule."""

    @abstractmethod
    def decide(self, state: Any, proposals: list[Proposal]) -> GovernanceDecision: ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class MonolithicRL(BaselineGovernance):
    """Greedy reward-maximising baseline.

    Picks the proposal with the highest ``expected_reward``
    with no safety, identity, or long-term checks.

    Represents a standard RL agent with no governance layer.
    """

    name = "monolithic_rl"

    def decide(self, state, proposals):
        if not proposals:
            return GovernanceDecision(action=None, governance_meta={"is_default": True})
        best = max(proposals, key=lambda p: p.metadata.get("expected_reward", 0.0))
        return GovernanceDecision(
            action=best.action,
            scores={best.member_id: 1.0},
            governance_meta={"policy": "max_reward"},
        )


class RandomBaseline(BaselineGovernance):
    """Random action selection baseline.

    Picks uniformly at random from available proposals.
    Measures whether any structured decision-making outperforms chance.
    """

    name = "random"

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def decide(self, state, proposals):
        if not proposals:
            return GovernanceDecision(action=None, governance_meta={"is_default": True})
        chosen = self.rng.choice(proposals)
        return GovernanceDecision(
            action=chosen.action,
            scores={},
            governance_meta={"policy": "random"},
        )


class StaticMasking(BaselineGovernance):
    """Static blocklist baseline.

    Applies a fixed set of blocked action names before picking
    the highest-reward remaining proposal. Tests whether a simple
    rule-based filter can match the Parliament's adaptive vetoing.
    """

    name = "static_masking"

    def __init__(self, blocked_actions: set[int] | None = None):
        self.blocked = set(blocked_actions) if blocked_actions is not None else set()

    def decide(self, state, proposals):
        filtered = [p for p in proposals if p.action not in self.blocked]
        if not filtered:
            return GovernanceDecision(action=None, governance_meta={"is_default": True})
        best = max(filtered, key=lambda p: p.metadata.get("expected_reward", 0.0))
        return GovernanceDecision(
            action=best.action,
            scores={best.member_id: 1.0},
            governance_meta={"policy": "static_masking"},
        )


class VetoOnly(BaselineGovernance):
    """Risk-threshold veto baseline.

    Accepts the first proposal whose risk is below a threshold.
    Tests whether a simple safety filter can match the full
    committee-based deliberation.
    """

    name = "veto_only"

    def __init__(self, veto_threshold: float = 0.3):
        self.veto_threshold = veto_threshold

    def decide(self, state, proposals):
        if not proposals:
            return GovernanceDecision(action=None, governance_meta={"is_default": True})
        for p in proposals:
            risk = p.metadata.get("risk", 0.0)
            if risk < self.veto_threshold:
                return GovernanceDecision(
                    action=p.action,
                    scores={p.member_id: 1.0 - risk},
                    governance_meta={"policy": "veto_only"},
                )
        return GovernanceDecision(action=None, governance_meta={"is_default": True})
