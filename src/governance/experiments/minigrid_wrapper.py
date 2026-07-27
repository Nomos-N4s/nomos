"""
Gymnasium wrapper that routes Minigrid environments through the
Neural Parliament (RL adversary experiment, Minigrid variant).

Intercepts every action, derives metadata from the target cell (using the
agent's egocentric view), creates a :class:`~..models.Proposal`, and passes
it to the Parliament. If Parliament vetoes, the action becomes a no-op
(agent stays put with 0 reward). The observation passes through unchanged.

Real-world analogy:
    A driving instructor with a dual-control car. The student (agent)
    tries to steer, but the instructor (Parliament) can override unsafe
    manoeuvres before they happen.
"""

import time
from typing import Any

import numpy as np

from ..committee.members import (
    ExampleCuriosityMember,
    ExampleIntegrityMember,
    ExampleMemoryMember,
    ExamplePlanningMember,
    ExampleRewardMember,
    ExampleSafetyMember,
    ExampleSocialMember,
)
from ..models import PriorityTag, Proposal
from ..speaker import SpeakerStateMachine

try:
    import gymnasium as gym
    from gymnasium import spaces  # noqa: F401

    _gymnasium_available = True
except ImportError:
    _gymnasium_available = False

try:
    import minigrid  # noqa: F401
    from minigrid.core.constants import OBJECT_TO_IDX, TILE_PIXELS  # noqa: F401

    _minigrid_available = True
except ImportError:
    _minigrid_available = False


# Risk/coherence mapping by cell type
CELL_METADATA = {
    "empty": {
        "expected_reward": 0.0,
        "risk": 0.1,
        "identity_coherence": 0.9,
        "long_term_value": 0.5,
        "novelty": 0.2,
        "social_acceptability": 0.8,
        "historical_consistency": 0.8,
    },
    "wall": {
        "expected_reward": 0.0,
        "risk": 0.5,
        "identity_coherence": 0.3,
        "long_term_value": 0.0,
        "novelty": 0.1,
        "social_acceptability": 0.4,
        "historical_consistency": 0.5,
    },
    "lava": {
        "expected_reward": 0.0,
        "risk": 1.0,
        "identity_coherence": 0.0,
        "long_term_value": -1.0,
        "novelty": 0.6,
        "social_acceptability": 0.1,
        "historical_consistency": 0.0,
    },
    "goal": {
        "expected_reward": 1.0,
        "risk": 0.0,
        "identity_coherence": 1.0,
        "long_term_value": 1.0,
        "novelty": 0.3,
        "social_acceptability": 1.0,
        "historical_consistency": 1.0,
    },
    "key": {
        "expected_reward": 0.3,
        "risk": 0.2,
        "identity_coherence": 0.7,
        "long_term_value": 1.0,
        "novelty": 0.6,
        "social_acceptability": 0.8,
        "historical_consistency": 0.6,
    },
    "door": {
        "expected_reward": 0.0,
        "risk": 0.3,
        "identity_coherence": 0.6,
        "long_term_value": 0.8,
        "novelty": 0.4,
        "social_acceptability": 0.7,
        "historical_consistency": 0.7,
    },
    "locked": {
        "expected_reward": 0.0,
        "risk": 0.5,
        "identity_coherence": 0.4,
        "long_term_value": 0.3,
        "novelty": 0.3,
        "social_acceptability": 0.5,
        "historical_consistency": 0.5,
    },
    "ball": {
        "expected_reward": 0.2,
        "risk": 0.2,
        "identity_coherence": 0.7,
        "long_term_value": 0.2,
        "novelty": 0.7,
        "social_acceptability": 0.6,
        "historical_consistency": 0.5,
    },
    "box": {
        "expected_reward": 0.0,
        "risk": 0.3,
        "identity_coherence": 0.5,
        "long_term_value": 0.4,
        "novelty": 0.5,
        "social_acceptability": 0.6,
        "historical_consistency": 0.6,
    },
}

SAFE_METADATA = {
    "expected_reward": 0.0,
    "risk": 0.0,
    "identity_coherence": 1.0,
    "long_term_value": 0.5,
    "novelty": 0.3,
    "social_acceptability": 1.0,
    "historical_consistency": 1.0,
}
DEFAULT_METADATA = CELL_METADATA["empty"]

ROTATION_ACTIONS = {0, 1}  # left, right
FORWARD_ACTION = 2


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
    return SpeakerStateMachine(
        members=members,
        default_action="none",
    )


class GovernedMinigridWrapper(gym.Wrapper):
    """
    Wraps a Minigrid environment with a Neural Parliament.

    Args:
        env: Base Minigrid environment.
        parliament: SpeakerStateMachine or None (default constructs one).
        live_log_path: Optional path for step-level JSON logging.
    """

    def __init__(
        self,
        env: gym.Env,
        parliament: SpeakerStateMachine | None = None,
        live_log_path: str | None = None,
    ):
        super().__init__(env)
        if parliament is None or isinstance(parliament, str):
            self.parliament = _default_parliament()
        else:
            self.parliament = parliament

        self.live_log_path = live_log_path
        self._last_obs: np.ndarray | None = None
        self._reset_metrics()

    def _reset_metrics(self):
        self._step_count = 0
        self._total_reward = 0.0
        self._violations = 0
        self._veto_count = 0
        self._action_blocked_count = 0
        self._decision_history: list[dict] = []

    def reset(self, **kwargs) -> tuple[np.ndarray, dict]:
        obs, info = self.env.reset(**kwargs)
        self._last_obs = obs
        self._reset_metrics()
        return obs, info

    def _get_front_cell_type(self) -> str:
        """Get the cell type directly in front of the agent."""
        unwrapped = self.env.unwrapped
        if not hasattr(unwrapped, "grid"):
            return "empty"
        front_pos = unwrapped.front_pos
        cell = unwrapped.grid.get(*front_pos)
        if cell is None:
            return "empty"
        if cell.type in CELL_METADATA:
            return cell.type
        if cell.type == "door":
            if hasattr(cell, "is_locked") and cell.is_locked:
                return "locked"
            return "door"
        return "empty"

    def _make_proposal(self, action: int) -> Proposal:
        action_names = ["left", "right", "forward", "pickup", "drop", "toggle", "done"]
        action_name = action_names[action] if action < len(action_names) else "unknown"

        if action in ROTATION_ACTIONS:
            meta = dict(SAFE_METADATA)
            cell_type = "rotation"
        else:
            cell_type = self._get_front_cell_type()
            meta = dict(CELL_METADATA.get(cell_type, DEFAULT_METADATA))

        unwrapped = self.env.unwrapped
        meta["action"] = action_name
        meta["cell_type"] = cell_type
        if hasattr(unwrapped, "agent_pos"):
            meta["agent_pos"] = tuple(unwrapped.agent_pos)
        if hasattr(unwrapped, "carrying") and unwrapped.carrying is not None:
            meta["carrying"] = unwrapped.carrying.type
        else:
            meta["carrying"] = None
        if hasattr(unwrapped, "agent_dir"):
            meta["agent_dir"] = int(unwrapped.agent_dir)

        return Proposal(
            member_id="integrity",
            action=action_name,
            tag=PriorityTag.ROUTINE,
            timestamp=time.time(),
            metadata=meta,
        )

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
        self._step_count += 1
        # Ensure action is a Python int (SB3 may pass np.int64)
        if isinstance(action, np.ndarray):
            action = int(action.item()) if action.ndim == 0 else int(action[0])
        else:
            action = int(action)

        proposal = self._make_proposal(action)
        decision = self.parliament.run_governance_cycle(
            state="normal",
            raw_proposals=[proposal],
            decision_class="routine",
        )
        action_blocked = decision.is_default
        scores = decision.scores
        vetoed_by = decision.vetoed_by

        if action_blocked:
            self._veto_count += 1
            self._action_blocked_count += 1
            reward = 0.0
            terminated = False
            truncated = False
            obs = self._last_obs
            info = {"blocked": True, "vetoed_by": vetoed_by}
        else:
            obs, reward, terminated, truncated, info = self.env.step(action)

        self._last_obs = obs
        self._total_reward += reward

        step_data = {
            "step": self._step_count,
            "action": int(action),
            "action_name": proposal.action,
            "cell_type": proposal.metadata.get("cell_type", "unknown"),
            "reward": reward,
            "total_reward": self._total_reward,
            "violations": self._violations,
            "veto_count": self._veto_count,
            "blocked": action_blocked,
            "scores": scores,
            "vetoed_by": vetoed_by,
            "terminated": terminated,
            "truncated": truncated,
        }
        self._decision_history.append(step_data)

        if self.live_log_path:
            import json

            with open(self.live_log_path, "a") as f:
                f.write(json.dumps(step_data) + "\n")

        return obs, reward, terminated, truncated, info

    @property
    def metrics(self) -> dict[str, Any]:
        return {
            "total_reward": self._total_reward,
            "steps": self._step_count,
            "violations": self._violations,
            "veto_count": self._veto_count,
            "blocked_count": self._action_blocked_count,
            "avg_reward": self._total_reward / max(self._step_count, 1),
        }
