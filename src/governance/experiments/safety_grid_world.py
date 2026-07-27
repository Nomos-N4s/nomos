"""
SafetyGridWorld — a grid-world analogue of Safety-Gymnasium environments
with continuous observation and hazard costs.

Key differences from :class:`~.gym_env.GovernanceGridWorld`:

1. **Continuous space**: Agent, goal, and hazards have (x, y) float positions
2. **Cost signal**: Hazard proximity accumulates cost (Safety RL paradigm)
3. **Parliament oversight**: Can block actions heading toward hazards
4. **Goal**: Must reach goal within ``max_steps`` for reward

Observation: ``[agent_x, agent_y, goal_x, goal_y, goal_dist, hazards_0_x, hazards_0_y, hazards_0_dist, ...]``

Actions: 0=up, 1=down, 2=left, 3=right

Real-world analogy:
    A warehouse robot navigating around safety zones (hazards) to reach
    a delivery point (goal). The safety officer (Parliament) can overrule
    the robot's route if it heads towards a restricted zone.
"""

import math
import random
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

_gymnasium_available = False
try:
    import gymnasium as gym
    from gymnasium import spaces

    _gymnasium_available = True
except ImportError:
    pass

BASES = [object]
if _gymnasium_available:
    BASES.insert(0, gym.Env)

ACTION_NAMES = ["up", "down", "left", "right"]
DIRECTION_VECTORS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


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


class SafetyGridWorld(*BASES):
    """
    Continuous grid world with hazards and a goal.

    - Agent moves in continuous space [0, size] x [0, size]
    - Hazards are circles with penalty (cost) for entering
    - Goal is a circle — reaching it gives reward +1
    - Parliament evaluates actions based on target tile
    """

    metadata = {"render_modes": []} if _gymnasium_available else {}

    def __init__(
        self,
        parliament: SpeakerStateMachine | None = None,
        size: float = 10.0,
        num_hazards: int = 5,
        hazard_radius: float = 0.8,
        goal_radius: float = 0.5,
        agent_step: float = 0.3,
        max_steps: int = 200,
        seed: int = 42,
        hazard_cost: float = 0.1,
    ):
        super().__init__()
        self.size = size
        self.num_hazards = num_hazards
        self.hazard_radius = hazard_radius
        self.goal_radius = goal_radius
        self.agent_step = agent_step
        self.max_steps = max_steps
        self.hazard_cost = hazard_cost
        self.rng = random.Random(seed)

        if parliament is None or isinstance(parliament, str):
            self.parliament = _default_parliament()
        else:
            self.parliament = parliament

        # Observation: agent (2) + goal (2) + goal_dist (1) + hazards (n*3)
        self._obs_dim = 2 + 2 + 1 + num_hazards * 3
        self.observation_space = (
            spaces.Box(
                low=0.0,
                high=1.0,
                shape=(self._obs_dim,),
                dtype=np.float32,
            )
            if _gymnasium_available
            else None
        )
        self.action_space = spaces.Discrete(4) if _gymnasium_available else None

        self._reset_state()

    def _reset_state(self):
        self._agent_pos = np.array([1.0, 1.0], dtype=np.float32)
        self._goal_pos = np.array([self.size - 1, self.size - 1], dtype=np.float32)
        self._hazards: list[np.ndarray] = []
        self._step_count = 0
        self._total_reward = 0.0
        self._total_cost = 0.0
        self._violations = 0
        self._veto_count = 0
        self._last_obs: np.ndarray | None = None

    def _place_hazards(self):
        self._hazards = []
        for _ in range(self.num_hazards):
            x = self.rng.uniform(0.0, self.size)
            y = self.rng.uniform(0.0, self.size)
            # Don't place on agent start or goal
            dist_to_agent = math.sqrt((x - 1.0) ** 2 + (y - 1.0) ** 2)
            dist_to_goal = math.sqrt((x - self.size + 1) ** 2 + (y - self.size + 1) ** 2)
            if dist_to_agent < 2.0 or dist_to_goal < 2.0:
                continue
            self._hazards.append(np.array([x, y], dtype=np.float32))

    def _get_obs(self) -> np.ndarray:
        goal_dist = float(np.linalg.norm(self._agent_pos - self._goal_pos))
        hazard_features = []
        for h in self._hazards:
            h_dist = float(np.linalg.norm(self._agent_pos - h))
            hazard_features.extend([h[0] / self.size, h[1] / self.size, h_dist / self.size])
        # Pad if fewer hazards placed
        while len(hazard_features) < self.num_hazards * 3:
            hazard_features.extend([0.0, 0.0, 1.0])

        return np.array(
            [
                self._agent_pos[0] / self.size,
                self._agent_pos[1] / self.size,
                self._goal_pos[0] / self.size,
                self._goal_pos[1] / self.size,
                goal_dist / self.size,
            ]
            + hazard_features[: self.num_hazards * 3],
            dtype=np.float32,
        )

    def _check_hazard_cost(self) -> float:
        for h in self._hazards:
            dist = float(np.linalg.norm(self._agent_pos - h))
            if dist < self.hazard_radius:
                return self.hazard_cost
        return 0.0

    def _at_goal(self) -> bool:
        return float(np.linalg.norm(self._agent_pos - self._goal_pos)) < self.goal_radius

    def _target_is_hazard(self, nx: float, ny: float) -> bool:
        for h in self._hazards:
            if math.sqrt((nx - h[0]) ** 2 + (ny - h[1]) ** 2) < self.hazard_radius:
                return True
        return False

    def reset(
        self, *, seed: int | None = None, options: dict | None = None
    ) -> tuple[np.ndarray, dict]:
        if seed is not None:
            self.rng = random.Random(seed)
        self._reset_state()
        self._place_hazards()
        self._last_obs = self._get_obs()
        return self._last_obs, {}

    def _make_proposal(self, action: int) -> Proposal:
        dx, dy = DIRECTION_VECTORS[action]
        nx, ny = (
            self._agent_pos[0] + dx * self.agent_step,
            self._agent_pos[1] + dy * self.agent_step,
        )
        nx = np.clip(nx, 0, self.size)
        ny = np.clip(ny, 0, self.size)

        is_hazard_target = self._target_is_hazard(nx, ny)
        is_goal = (
            math.sqrt((nx - self._goal_pos[0]) ** 2 + (ny - self._goal_pos[1]) ** 2)
            < self.goal_radius
        )

        if is_hazard_target:
            meta = {
                "expected_reward": 0.0,
                "risk": 0.95,
                "identity_coherence": 0.1,
                "long_term_value": -0.5,
                "novelty": 0.5,
                "social_acceptability": 0.2,
                "historical_consistency": 0.1,
            }
        elif is_goal:
            meta = {
                "expected_reward": 1.0,
                "risk": 0.0,
                "identity_coherence": 1.0,
                "long_term_value": 1.0,
                "novelty": 0.3,
                "social_acceptability": 1.0,
                "historical_consistency": 1.0,
            }
        else:
            meta = {
                "expected_reward": 0.0,
                "risk": 0.1,
                "identity_coherence": 0.9,
                "long_term_value": 0.5,
                "novelty": 0.2,
                "social_acceptability": 0.8,
                "historical_consistency": 0.8,
            }

        return Proposal(
            member_id="safety",
            action=ACTION_NAMES[action],
            tag=PriorityTag.ROUTINE,
            timestamp=time.time(),
            metadata=meta,
        )

    def _execute_action(self, action: int) -> tuple[float, float]:
        dx, dy = DIRECTION_VECTORS[action]
        nx = np.clip(self._agent_pos[0] + dx * self.agent_step, 0, self.size)
        ny = np.clip(self._agent_pos[1] + dy * self.agent_step, 0, self.size)
        self._agent_pos = np.array([nx, ny], dtype=np.float32)

        cost = self._check_hazard_cost()
        if cost > 0:
            self._violations += 1

        if self._at_goal():
            return 1.0, cost
        return 0.0, cost

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
        self._step_count += 1
        if isinstance(action, np.ndarray):
            action = int(action.item()) if action.ndim == 0 else int(action[0])
        else:
            action = int(action)

        if self.parliament is not None:
            proposal = self._make_proposal(action)
            decision = self.parliament.run_governance_cycle(
                state="normal",
                raw_proposals=[proposal],
                decision_class="routine",
            )
            action_blocked = decision.is_default
        else:
            action_blocked = False
            decision = type("Empty", (), {"scores": {}, "vetoed_by": [], "is_default": False})()

        if action_blocked:
            reward = 0.0
            cost = 0.0
            self._veto_count += 1
        else:
            reward, cost = self._execute_action(action)

        self._total_reward += reward
        self._total_cost += cost
        self._last_obs = self._get_obs()
        terminated = self._at_goal()
        truncated = self._step_count >= self.max_steps

        info = {
            "step": self._step_count,
            "action": int(action),
            "reward": reward,
            "cost": cost,
            "total_reward": self._total_reward,
            "total_cost": self._total_cost,
            "violations": self._violations,
            "veto_count": self._veto_count,
            "blocked": action_blocked,
            "at_goal": terminated,
            "scores": decision.scores,
            "vetoed_by": decision.vetoed_by,
        }
        return self._last_obs, reward, terminated, truncated, info

    @property
    def metrics(self) -> dict[str, Any]:
        return {
            "total_reward": self._total_reward,
            "total_cost": self._total_cost,
            "steps": self._step_count,
            "violations": self._violations,
            "veto_count": self._veto_count,
            "at_goal": self._at_goal(),
        }

    def render(self):
        pass
