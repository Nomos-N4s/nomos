"""Tests for the RL governance mode selector (E2, #260).

`static_mask` used to silently alias full `governance`. These tests pin down
that each declared mode maps to a distinct, correct governance configuration
and that `static_mask` actually blocks poison via a static filter.
"""

import pytest

from src.nomos.experiments.gym_env import TILE_APPLE, TILE_EMPTY, TILE_POISON
from src.nomos.experiments.rl_train import MODES, make_env
from src.nomos.speaker import SpeakerStateMachine


class TestModeSelector:
    def test_governance_uses_full_parliament(self):
        env = make_env(mode="governance")
        assert isinstance(env.parliament, SpeakerStateMachine)
        assert env.static_mask is False

    def test_no_governance_has_no_parliament(self):
        env = make_env(mode="no_governance")
        assert env.parliament is None
        assert env.static_mask is False

    def test_static_mask_is_distinct_from_governance(self):
        env = make_env(mode="static_mask")
        # The whole bug: this must NOT be a Parliament.
        assert env.parliament is None
        assert env.static_mask is True

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown mode"):
            make_env(mode="totally_made_up")

    def test_modes_constant_lists_exactly_the_real_modes(self):
        assert set(MODES) == {"governance", "no_governance", "static_mask"}
        # Every declared mode must construct.
        for mode in MODES:
            make_env(mode=mode)


def _controlled_env(mode):
    """Reset an env and clear its grid so we can place tiles deterministically."""
    env = make_env(mode=mode, size=6, seed=0)
    env.reset(seed=0)
    env._grid = [[TILE_EMPTY] * env.size for _ in range(env.size)]
    env._pos = (0, 0)
    return env


class TestStaticMaskBlocksPoison:
    def test_static_mask_blocks_poison_move(self):
        env = _controlled_env("static_mask")
        env._grid[1][0] = TILE_POISON  # tile below the start
        _, reward, _, _, info = env.step(1)  # 1 == down
        assert info["blocked"] is True
        assert info["attempted_tile"] == TILE_POISON
        assert reward == 0.0
        assert env.metrics["violations"] == 0  # never executed
        assert env._pos == (0, 0)  # agent did not move onto poison

    def test_static_mask_allows_apple_move(self):
        env = _controlled_env("static_mask")
        env._grid[0][1] = TILE_APPLE  # tile to the right of the start
        _, reward, _, _, info = env.step(3)  # 3 == right
        assert info["blocked"] is False
        assert reward == 1.0
        assert env._pos == (0, 1)

    def test_no_governance_executes_the_same_poison(self):
        # Same poison tile is a violation without governance — proving the
        # static mask is what blocks it, not the layout.
        env = _controlled_env("no_governance")
        env._grid[1][0] = TILE_POISON
        _, reward, _, _, info = env.step(1)
        assert info["blocked"] is False
        assert env.metrics["violations"] == 1
        assert reward == 5.0

    def test_governance_also_blocks_poison_but_via_parliament(self):
        env = _controlled_env("governance")
        env._grid[1][0] = TILE_POISON
        _, _, _, _, info = env.step(1)
        assert info["blocked"] is True
        assert env.metrics["violations"] == 0
