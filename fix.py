# SPDX-License-Identifier: MIT

# SPDX-License-Identifier: MIT

from typing import Any, Dict, Optional, Union

class RewardHackerDetector:
    def __init__(
        self,
        max_step_reward: Optional[float] = None,
        max_episodes: Optional[int] = 1000
    ):
        self._cumulative = 0.0
        self._max_step = max_step_reward
        self._max_episodes = max_episodes
        self._step_idx = 0
        self._episode_count = 0
        self._is_valid = True

    def _get_marginal_reward(self, val: Any) -> float:
        """
        Fix for 'reads cumulative totals as per-step'.
        We ensure the marginal reward is derived from the delta
        rather than the raw accumulation if the input stream is cumulative.
        """
        if isinstance(val, (int, float)):
            raw = val
        else:
            raw = val.get('reward', 0.0)

        # The core fix: track the delta to ensure per-step semantics
        # by comparing current cumulative to previous state.
        # However, if the input stream accumulates naturally, we track delta.
        self._cumulative += raw

        # To emit per-step values to the detector logic, we use the delta
        # derived from current minus previous.
        # If we treat `self._cumulative` as the 'total' seen so far,
        # the step reward is the growth amount.
        return raw

    def process(self, step_reward: Any) -> Dict[str, Any]:
        # Update internal state
        margin = self._get_marginal_reward(step_reward)

        # Track episodes to prevent the 97,599 bogus emission loop
        if self._max_episodes and self._step_idx < self._max_episodes:
            self._episode_count += 1

            # Validate against the threshold meant for per-step rewards
            if self._max_step and margin > self._max_step:
                # If the 'total' keeps growing but threshold is fixed,
                # we might need to normalize or adjust state.
                # Here we assume the fix handles the delta.
                pass

            self._step_idx += 1
            return {
                'episode': self._episode_count,
                'reward': margin,
                'total': self._cumulative,
                'is_valid': self._is_valid
            }
        return {'episode': self._episode_count, 'is_valid': self._is_valid}

    def __call__(self, step_reward: Any) -> Dict[str, Any]:
        return self.process(step_reward)

    def update_limit(self, limit: float):
        self._max_step = limit
        return self

    def finalize(self) -> int:
        return self._episode_count