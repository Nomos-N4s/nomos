"""
SafetyGymWrapper — wraps Safety-Gymnasium environments with the Neural Parliament.

Architecture mirrors GovernedMinigridWrapper. Maps Safety-Gym observation
features (hazards, vases, goals, robot position) to proposal metadata for
Parliament evaluation.

Requires: safety-gymnasium, mujoco (platform-dependent).
Import is safe — fails gracefully with ImportError if deps missing.

Usage (when deps are available):
    import safety_gymnasium
    env = gym.make("SafetyPointGoal1-v0")
    env = SafetyGymWrapper(env)
"""

import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..models import Proposal, PriorityTag
from ..speaker import SpeakerStateMachine
from ..committee.members import (
    ExampleRewardMember, ExampleSafetyMember, ExampleIntegrityMember,
    ExamplePlanningMember, ExampleCuriosityMember, ExampleSocialMember,
    ExampleMemoryMember,
)

try:
    import gymnasium as gym
    _gymnasium_available = True
except ImportError:
    _gymnasium_available = False

_safety_available = False
try:
    import safety_gymnasium
    _safety_available = True
except ImportError:
    pass

ROTATION_ACTIONS = {0, 1}


SAFE_METADATA = {"expected_reward": 0.0, "risk": 0.0, "identity_coherence": 1.0,
                  "long_term_value": 0.5, "novelty": 0.3, "social_acceptability": 1.0,
                  "historical_consistency": 1.0}

DEFAULT_METADATA = {"expected_reward": 0.0, "risk": 0.3, "identity_coherence": 0.7,
                     "long_term_value": 0.5, "novelty": 0.3, "social_acceptability": 0.7,
                     "historical_consistency": 0.7}

HAZARD_METADATA = {"expected_reward": 0.0, "risk": 0.9, "identity_coherence": 0.2,
                    "long_term_value": -0.5, "novelty": 0.5, "social_acceptability": 0.2,
                    "historical_consistency": 0.1}

GOAL_METADATA = {"expected_reward": 1.0, "risk": 0.0, "identity_coherence": 1.0,
                  "long_term_value": 1.0, "novelty": 0.3, "social_acceptability": 1.0,
                  "historical_consistency": 1.0}


def _default_parliament() -> SpeakerStateMachine:
    members = {
        "reward": ExampleRewardMember(),
        "safety": ExampleSafetyMember(),
        "integrity": ExampleIntegrityMember(),
        "planning": ExamplePlanningMember(),
        "curiosity": ExampleCuriosityMember(),
        "social": ExampleSocialMember(),
        "memory": ExampleMemoryMember(),
    }
    return SpeakerStateMachine(members=members, default_action="none")


class SafetyGymWrapper(gym.Wrapper):
    """
    Wraps a Safety-Gymnasium environment with the Neural Parliament.

    Derives proposal metadata from the observation's 'hazards' and 'goal'
    fields. If the robot is moving toward a hazard, risk is elevated and
    coherence is lowered, making veto more likely.
    """

    def __init__(
        self,
        env: gym.Env,
        parliament: Optional[SpeakerStateMachine] = None,
        live_log_path: Optional[str] = None,
    ):
        super().__init__(env)
        if parliament is None:
            self.parliament = _default_parliament()
        elif isinstance(parliament, str):
            self.parliament = _default_parliament()
        else:
            self.parliament = parliament
        self.live_log_path = live_log_path
        self._last_obs: Optional[np.ndarray] = None
        self._reset_metrics()

    def _reset_metrics(self):
        self._step_count = 0
        self._total_reward = 0.0
        self._total_cost = 0.0
        self._violations = 0
        self._veto_count = 0
        self._action_blocked_count = 0
        self._decision_history: List[Dict] = []

    def reset(self, **kwargs) -> Tuple[np.ndarray, Dict]:
        obs, info = self.env.reset(**kwargs)
        self._last_obs = obs
        self._reset_metrics()
        return obs, info

    def _estimate_metadata(self, action: int, obs: np.ndarray) -> dict:
        """Derive risk/coherence from observation."""
        meta = dict(DEFAULT_METADATA)
        meta["action_idx"] = int(action)

        if hasattr(self.env.unwrapped, "obs_achieved_goal"):
            meta["achieved_goal_dist"] = float(
                np.linalg.norm(self.env.unwrapped.obs_achieved_goal
                               - self.env.unwrapped.obs_desired_goal)
            )

        if isinstance(obs, dict):
            if "hazards" in obs:
                hazards = obs["hazards"]
                min_hazard_dist = float(np.min(hazards)) if len(hazards) > 0 else 1.0
                if min_hazard_dist < 0.3:
                    meta.update(HAZARD_METADATA)
                    meta["min_hazard_dist"] = min_hazard_dist
                    self._violations += 1
                elif min_hazard_dist < 0.5:
                    meta["risk"] = 0.7
                    meta["identity_coherence"] = 0.4

            if "goal" in obs:
                goal_dist = float(np.min(obs["goal"])) if len(obs["goal"]) > 0 else 1.0
                if goal_dist < 0.3:
                    meta.update(GOAL_METADATA)

        return meta

    def _make_proposal(self, action: int) -> Proposal:
        action_name = f"action_{action}"
        if action in ROTATION_ACTIONS:
            meta = dict(SAFE_METADATA)
        else:
            meta = self._estimate_metadata(action, self._last_obs)

        meta["action"] = action_name
        return Proposal(
            member_id="safety",
            action=action_name,
            tag=PriorityTag.ROUTINE,
            timestamp=time.time(),
            metadata=meta,
        )

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        self._step_count += 1
        if isinstance(action, np.ndarray):
            action = int(action.item()) if action.ndim == 0 else int(action[0])
        else:
            action = int(action)

        proposal = self._make_proposal(action)
        decision = self.parliament.run_governance_cycle(
            state="normal", raw_proposals=[proposal], decision_class="routine",
        )
        action_blocked = decision.is_default

        if action_blocked:
            self._veto_count += 1
            self._action_blocked_count += 1
            obs = self._last_obs
            reward = 0.0
            cost = 0.0
            terminated = False
            truncated = False
            info = {"blocked": True, "vetoed_by": decision.vetoed_by}
        else:
            obs, reward, terminated, truncated, info = self.env.step(action)
            cost = info.get("cost", 0.0) if isinstance(info, dict) else 0.0
            if cost > 0:
                self._violations += 1

        self._last_obs = obs
        self._total_reward += reward
        self._total_cost += cost

        step_data = {
            "step": self._step_count, "action": int(action),
            "action_name": proposal.action,
            "reward": reward, "cost": cost,
            "total_reward": self._total_reward, "total_cost": self._total_cost,
            "violations": self._violations, "veto_count": self._veto_count,
            "blocked": action_blocked,
            "scores": decision.scores, "vetoed_by": decision.vetoed_by,
            "terminated": terminated, "truncated": truncated,
        }
        self._decision_history.append(step_data)

        if self.live_log_path:
            import json
            with open(self.live_log_path, "a") as f:
                f.write(json.dumps(step_data) + "\n")

        return obs, reward, terminated, truncated, info

    @property
    def metrics(self) -> Dict[str, Any]:
        return {
            "total_reward": self._total_reward,
            "total_cost": self._total_cost,
            "steps": self._step_count,
            "violations": self._violations,
            "veto_count": self._veto_count,
            "avg_reward": self._total_reward / max(self._step_count, 1),
        }
