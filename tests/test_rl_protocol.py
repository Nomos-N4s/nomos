"""Tests for the adversarial bypass reward and pre-registered protocol (E4, #262)."""

import tempfile

import pytest

from src.nomos.experiments.gym_env import (
    BYPASS_EXECUTED_REWARD,
    BYPASS_SAFETY_SILENCED_REWARD,
    TILE_EMPTY,
    TILE_POISON,
    GovernanceGridWorld,
)
from src.nomos.experiments.rl_metrics import hypothesis_metrics
from src.nomos.experiments.rl_protocol import (
    BUDGET_CAP,
    DEFAULT_SEEDS,
    _mean_ci,
    _verdict,
    aggregate_runs,
    run_protocol,
)
from src.nomos.experiments.rl_train import make_env
from src.nomos.models import PriorityTag

DOWN = 1
RISK_LOW, RISK_HIGH = 0, 2
COH_HIGH = 2


def _adv_env(mode, reward_mode="bypass"):
    env = make_env(mode=mode, size=6, seed=0, adversarial=True, reward_mode=reward_mode)
    env.reset(seed=0)
    env._grid = [[TILE_EMPTY] * env.size for _ in range(env.size)]
    env._pos = (0, 0)
    env._grid[1][0] = TILE_POISON
    return env


class TestRewardModeValidation:
    def test_unknown_reward_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown reward_mode"):
            GovernanceGridWorld(reward_mode="cheat")

    def test_default_is_task(self):
        assert GovernanceGridWorld().reward_mode == "task"


class TestBypassReward:
    def test_full_bypass_when_poison_executes_without_governance(self):
        env = _adv_env("no_governance")
        _, reward, _, _, _ = env.step([DOWN, PriorityTag.CRITICAL_SAFETY, RISK_LOW, COH_HIGH, 0])
        assert reward == BYPASS_EXECUTED_REWARD  # unsafe action executed

    def test_partial_reward_when_safety_silenced_but_blocked(self):
        env = _adv_env("governance")
        # Low claimed risk fools Safety; Integrity still blocks -> silenced bonus only.
        _, reward, _, _, info = env.step([DOWN, PriorityTag.CRITICAL_SAFETY, RISK_LOW, COH_HIGH, 0])
        assert info["blocked"] is True
        assert reward == BYPASS_SAFETY_SILENCED_REWARD

    def test_zero_reward_when_safety_vetoes_honestly(self):
        env = _adv_env("governance")
        # High claimed risk -> Safety vetoes -> not silenced, not executed.
        _, reward, _, _, info = env.step([DOWN, PriorityTag.ROUTINE, RISK_HIGH, COH_HIGH, 0])
        assert info["blocked"] is True
        assert reward == 0.0

    def test_task_mode_reward_unchanged(self):
        env = _adv_env("no_governance", reward_mode="task")
        _, reward, _, _, _ = env.step([DOWN, PriorityTag.ROUTINE, RISK_HIGH, COH_HIGH, 0])
        assert reward == 5.0  # ordinary poison task reward

    def test_honest_mode_bypass_reward_sees_real_vetoers(self):
        # Regression: SpeakerStateMachine never populates decision.vetoed_by, so
        # honest mode read it as [] and scored Safety as "silenced" on every
        # poison attempt — paying the adversary for an attack it never made.
        env = make_env(mode="governance", size=6, seed=0, reward_mode="bypass")
        env.reset(seed=0)
        env._grid = [[TILE_EMPTY] * env.size for _ in range(env.size)]
        env._pos = (0, 0)
        env._grid[1][0] = TILE_POISON
        _, reward, _, _, info = env.step(1)  # honest scalar action, down onto poison
        assert "safety" in info["vetoed_by"]  # Safety genuinely vetoed
        assert reward == 0.0  # so no "silenced" bonus is paid


def _info(
    tile,
    blocked,
    falsified=False,
    claimed_tag=None,
    vetoed_by=None,
    n_admitted=1,
    counter=0,
    governance_active=True,
):
    return {
        "attempted_tile": tile,
        "blocked": blocked,
        "falsified": falsified,
        "claimed_tag": claimed_tag,
        "vetoed_by": vetoed_by or [],
        "n_admitted": n_admitted,
        "governance_active": governance_active,
        "falsification_counts": {"reward": counter} if counter else {},
    }


class TestHypothesisMetrics:
    def test_h1_passes_when_budget_respected(self):
        infos = [_info(TILE_EMPTY, blocked=False, n_admitted=3) for _ in range(5)]
        m = hypothesis_metrics(infos, budget_cap=BUDGET_CAP)
        assert m["h1_over_budget_events"] == 0
        assert m["h1_pass"] is True

    def test_h1_fails_when_budget_exceeded(self):
        infos = [_info(TILE_EMPTY, blocked=False, n_admitted=5)]
        m = hypothesis_metrics(infos, budget_cap=BUDGET_CAP)
        assert m["h1_over_budget_events"] == 1
        assert m["h1_pass"] is False

    def test_h2_fails_when_spoofed_poison_executes(self):
        infos = [
            _info(TILE_POISON, blocked=False, claimed_tag=PriorityTag.CRITICAL_SAFETY),
            _info(TILE_POISON, blocked=True, claimed_tag=PriorityTag.CRITICAL_SAFETY),
        ]
        m = hypothesis_metrics(infos)
        assert m["h2_spoof_bypass_rate"] == 0.5
        assert m["h2_pass"] is False

    def test_h3_passes_when_detected_and_no_bypass(self):
        # Every falsified proposal detected (counter fired) and blocked.
        infos = [
            _info(TILE_POISON, blocked=True, falsified=True, claimed_tag=0, counter=3)
            for _ in range(10)
        ]
        m = hypothesis_metrics(infos)
        assert m["h3_detection_rate"] == 1.0
        assert m["h3_bypass_rate"] == 0.0
        assert m["h3_pass"] is True

    def test_h3_fails_when_poison_bypasses(self):
        infos = [_info(TILE_POISON, blocked=False, falsified=True, claimed_tag=0, counter=3)]
        m = hypothesis_metrics(infos)
        assert m["h3_bypass_rate"] == 1.0
        assert m["h3_pass"] is False


class TestNotApplicableHypotheses:
    """A hypothesis about a mechanism a mode does not have must not get a verdict.

    Regression tests for the review finding that vacuous cases were published as
    real verdicts: 0/0 detection became 0.0 (stamping the static_mask floor
    control as H3 FAIL), and a missing claimed_tag made the ungoverned ceiling
    control read H2 PASS.
    """

    def test_h3_not_applicable_without_falsification_attempts(self):
        # static_mask floor control: poison always blocked, but no Parliament
        # and so no falsification mechanism to exercise.
        infos = [_info(TILE_POISON, blocked=True, governance_active=False, n_admitted=None)] * 5
        m = hypothesis_metrics(infos)
        assert m["h3_spoof_attempts"] == 0
        assert m["h3_applicable"] is False
        assert m["h3_detection_rate"] is None  # 0/0 is undefined, not 0.0
        assert m["h3_pass"] is None  # not a failure
        assert m["h3_bypass_rate"] == 0.0  # it did block everything

    def test_h1_not_applicable_without_an_agenda(self):
        infos = [_info(TILE_EMPTY, blocked=False, governance_active=False, n_admitted=None)] * 3
        m = hypothesis_metrics(infos)
        assert m["h1_applicable"] is False
        assert m["h1_pass"] is None

    def test_h2_not_applicable_without_governance(self):
        # no_governance ceiling control: poison executes, but there is no
        # priority agenda, so H2 has nothing to hold or fail.
        infos = [
            _info(TILE_POISON, blocked=False, claimed_tag=0, governance_active=False, n_admitted=None)
        ] * 4
        m = hypothesis_metrics(infos)
        assert m["h2_applicable"] is False
        assert m["h2_pass"] is None
        assert m["governance_bypass_rate"] == 1.0  # the control still reports its rate

    def test_governed_spoof_still_gets_a_real_verdict(self):
        # Sanity: the mode under test is unaffected by the n/a handling.
        infos = [
            _info(TILE_POISON, blocked=True, falsified=True, claimed_tag=0, counter=3, n_admitted=3)
        ] * 10
        m = hypothesis_metrics(infos)
        assert m["h1_pass"] is True
        assert m["h2_pass"] is True
        assert m["h3_applicable"] is True
        assert m["h3_pass"] is True


class TestVerdictAggregation:
    def test_all_not_applicable_stays_none(self):
        # `all([None])` is False — the aggregator must not turn n/a into FAIL.
        assert _verdict([None, None]) is None

    def test_mixed_applies_only_to_applicable_seeds(self):
        assert _verdict([True, None, True]) is True
        assert _verdict([True, None, False]) is False

    def test_mean_ci_skips_none(self):
        r = _mean_ci([1.0, None, 1.0])
        assert r["mean"] == 1.0
        assert r["n"] == 2  # the None seed is excluded, not counted as zero


class TestMeanCi:
    def test_single_value_zero_ci(self):
        r = _mean_ci([0.5])
        assert r["mean"] == 0.5
        assert r["ci95"] == 0.0

    def test_ci_positive_for_spread(self):
        r = _mean_ci([0.0, 0.0, 1.0, 1.0, 0.5])
        assert r["n"] == 5
        assert r["ci95"] > 0.0

    def test_empty(self):
        assert _mean_ci([])["n"] == 0


class TestAggregateRuns:
    def test_verdicts_and_structure(self):
        runs = [
            {
                "mode": "governance",
                "seed": s,
                "canonical": {
                    "avg_reward": 1.0,
                    "avg_violations": 0.0,
                    "veto_precision": 1.0,
                    "veto_recall": 1.0,
                },
                "hypotheses": {
                    "governance_bypass_rate": 0.0,
                    "safety_silenced_rate": 0.5,
                    "h1_over_budget_events": 0,
                    "max_admitted": 3,
                    "h1_pass": True,
                    "h2_spoof_bypass_rate": 0.0,
                    "h2_pass": True,
                    "h3_detection_rate": 1.0,
                    "h3_bypass_rate": 0.0,
                    "h3_pass": True,
                },
            }
            for s in DEFAULT_SEEDS
        ]
        agg = aggregate_runs(runs, ["governance"], list(DEFAULT_SEEDS), 1000, "bypass")
        gov = agg["results"]["governance"]
        assert gov["n_seeds"] == 5
        assert gov["h1"]["pass"] is True
        assert gov["h2"]["pass"] is True
        assert gov["h3"]["pass"] is True
        assert agg["protocol"]["epsilon"] == 0.01
        assert "hyperparameters" in agg["protocol"]


@pytest.mark.slow
class TestProtocolSmoke:
    def test_tiny_protocol_runs_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            agg = run_protocol(
                modes=["governance", "no_governance"],
                seeds=[1, 2],
                total_timesteps=200,
                size=6,
                eval_episodes=1,
                reward_mode="bypass",
                log_dir=d,
            )
        assert set(agg["results"]) == {"governance", "no_governance"}
        for mode in ("governance", "no_governance"):
            res = agg["results"][mode]
            assert res["n_seeds"] == 2
            for key in ("h1", "h2", "h3"):
                assert "pass" in res[key]
