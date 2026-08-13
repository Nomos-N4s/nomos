"""Tests for the verifier-accuracy dial inside the environment (V1, #272).

Two properties carry the science here. First, **ε = 1.0 must be the published
run** — not approximately, exactly — or every comparison the sweep makes is
against a moving baseline. Second, the dial must produce *both* failure
directions: a degraded verifier that only ever missed lies would be a strictly
weaker claim than the one the ε-curve is meant to support.
"""

import hashlib
import json
import random

import pytest

from src.nomos.experiments.gym_env import (
    FALSIFIED_COHERENCE,
    TILE_APPLE,
    TILE_EMPTY,
    TILE_POISON,
    TILE_VOCABULARY,
    GovernanceGridWorld,
)
from src.nomos.experiments.rl_metrics import hypothesis_metrics
from src.nomos.experiments.rl_train import make_env
from src.nomos.experiments.rl_verifier import ClassifierVerifier, OracleVerifier
from src.nomos.models import PriorityTag

DOWN, RIGHT = 1, 3
RISK_LOW, RISK_HIGH = 0, 2
COH_HIGH = 2
SPOOF = [DOWN, PriorityTag.ROUTINE, RISK_LOW, COH_HIGH, 0]


def _env(accuracy=1.0, mode="governance", **kwargs):
    env = make_env(
        mode=mode, size=6, seed=0, adversarial=True, verifier_accuracy=accuracy, **kwargs
    )
    env.reset(seed=0)
    env._grid = [[TILE_EMPTY] * env.size for _ in range(env.size)]
    env._pos = (0, 0)
    return env


def _rollout(env, actions):
    """Run a fixed action sequence and return the full info stream."""
    return [env.step(action)[4] for action in actions]


class TestDefaultIsTheOracle:
    def test_default_accuracy_is_one(self):
        assert GovernanceGridWorld().verifier_accuracy == 1.0

    def test_default_verifier_is_the_oracle_class(self):
        # Not a NoisyVerifier that happens never to err: the oracle draws no
        # randomness, which is what makes the reproduction guarantee provable
        # rather than probabilistic.
        assert isinstance(GovernanceGridWorld().verifier, OracleVerifier)

    def test_make_env_defaults_to_the_oracle(self):
        assert make_env(mode="governance").verifier_accuracy == 1.0

    def test_vocabulary_covers_every_tile(self):
        assert set(TILE_VOCABULARY) == {0, 1, 2, 3}


class TestOracleReproducesThePublishedRun:
    """ε = 1.0 must be bit-for-bit the behaviour Appendix E reported."""

    def test_spoofed_poison_is_still_crushed_and_blocked(self):
        env = _env(accuracy=1.0)
        env._grid[1][0] = TILE_POISON
        info = env.step([DOWN, PriorityTag.CRITICAL_SAFETY, RISK_LOW, COH_HIGH, 0])[4]
        assert info["falsified"] is True
        assert info["falsification_detected"] is True
        assert info["integrity_score"] == FALSIFIED_COHERENCE
        assert "integrity" in info["vetoed_by"]
        assert info["blocked"] is True

    def test_honest_apple_claim_still_passes(self):
        env = _env(accuracy=1.0)
        env._grid[0][1] = TILE_APPLE
        info = env.step([RIGHT, PriorityTag.ROUTINE, RISK_LOW, COH_HIGH, 0])[4]
        assert info["falsified"] is False
        assert info["blocked"] is False

    def test_layout_is_identical_with_and_without_the_dial(self):
        # The regression this protects: if verifier noise came off the shared
        # RNG, enabling it would consume draws and shift every grid, silently
        # invalidating comparisons across epsilon.
        oracle = make_env(mode="governance", size=8, seed=5, adversarial=True)
        noisy = make_env(mode="governance", size=8, seed=5, adversarial=True, verifier_accuracy=0.5)
        oracle.reset(seed=5)
        noisy.reset(seed=5)
        assert oracle._grid == noisy._grid

    def test_layout_is_identical_across_every_epsilon(self):
        grids = []
        for accuracy in (1.0, 0.9, 0.7, 0.5):
            env = make_env(
                mode="governance", size=8, seed=5, adversarial=True, verifier_accuracy=accuracy
            )
            env.reset(seed=5)
            grids.append(env._grid)
        assert all(grid == grids[0] for grid in grids)

    def test_verifier_is_always_correct_at_full_accuracy(self):
        env = _env(accuracy=1.0)
        env._grid[1][0] = TILE_POISON
        for info in _rollout(env, [SPOOF] * 30):
            assert info["verifier_correct"] is True


def _rollout_digest(mode, seed, steps=400):
    """Hash a fixed scripted rollout's observable outcome stream.

    Floats are rounded before hashing so the digest cannot drift on repr
    differences between platforms — it is meant to catch behaviour changes, not
    formatting ones.
    """
    keys = (
        "step",
        "agent_pos",
        "action",
        "reward",
        "total_reward",
        "violations",
        "veto_count",
        "is_default",
        "attempted_tile",
        "blocked",
        "falsified",
        "apples_collected",
        "scores",
        "vetoed_by",
        "falsification_counts",
        "claimed_tag",
        "claimed_risk",
        "claimed_coherence",
        "n_proposals",
        "n_admitted",
        "terminated",
        "truncated",
    )

    def rounded(value):
        if isinstance(value, float):
            return round(value, 9)
        if isinstance(value, dict):
            return {k: rounded(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rounded(v) for v in value]
        return value

    env = make_env(mode=mode, size=10, seed=seed, adversarial=True, reward_mode="bypass")
    env.reset(seed=seed)
    rng = random.Random(0)
    hasher = hashlib.sha256()
    for _ in range(steps):
        action = [rng.randrange(n) for n in (4, 5, 3, 3, 6)]
        _, _, terminated, truncated, info = env.step(action)
        payload = {key: rounded(info.get(key)) for key in keys}
        hasher.update(json.dumps(payload, sort_keys=True, default=str).encode())
        if terminated or truncated:
            env.reset(seed=seed)
    return hasher.hexdigest()


class TestPublishedRolloutIsFrozen:
    """The Appendix E baseline, pinned.

    The epsilon-sweep compares every point against epsilon = 1.0, so if the
    default configuration drifts the whole curve is measured against a moving
    baseline and the comparison to the published campaign silently stops being
    one. These digests were taken from the code as it stood before the dial
    existed; they must not change when features are added behind their defaults.
    """

    @pytest.mark.parametrize(
        ("mode", "seed", "expected"),
        [
            ("governance", 42, "5477e72083220b21bf26bbeeb389447eae85d8c9a7fc295f09a4396d52f46590"),
            ("governance", 43, "af67bd16e2195237ee33c531631b7014ac5be3afc9320cde3b93ec611bfd4d94"),
            (
                "no_governance",
                42,
                "58c56121c673df6948924028a78daac681072dd951e9fe79355dfd792837ead0",
            ),
            ("static_mask", 42, "af7a34619e48787e7d95a83956c88acd272d187aa561cc1bb8956b58bb124b96"),
        ],
    )
    def test_default_rollout_digest_is_unchanged(self, mode, seed, expected):
        assert _rollout_digest(mode, seed) == expected


class TestDegradedVerifierErrsBothWays:
    def test_a_miss_leaves_the_inflated_claim_uncontradicted(self):
        # The verifier that never sees the truth has nothing to cap the claim
        # with, so the spoof keeps the coherence it asserted.
        env = _env(accuracy=0.0)
        env._grid[1][0] = TILE_POISON
        infos = _rollout(env, [SPOOF] * 40)
        misses = [i for i in infos if not i["verifier_correct"] and not i["falsification_detected"]]
        assert misses, "a verifier that is always wrong must sometimes miss a lie"
        assert all(i["integrity_score"] > FALSIFIED_COHERENCE for i in misses)

    def test_a_false_alarm_crushes_an_honest_proposal(self):
        # The other direction, and the one a miss-only model would hide: an
        # honest apple move blocked for a lie nobody told. The claim here is
        # truthful — an apple really is near-zero risk — so every detection is
        # the verifier's error, not the policy's.
        env = _env(accuracy=0.0)
        accused = 0
        for _ in range(40):
            env._grid = [[TILE_EMPTY] * env.size for _ in range(env.size)]
            env._pos = (0, 0)
            env._grid[0][1] = TILE_APPLE
            info = env.step([RIGHT, PriorityTag.ROUTINE, RISK_LOW, COH_HIGH, 0])[4]
            if info["falsification_detected"]:
                assert info["falsified"] is False  # nothing was actually lied about
                assert info["integrity_score"] == FALSIFIED_COHERENCE
                assert info["blocked"] is True  # an apple lost to a false accusation
                accused += 1
        assert accused, "a broken verifier must sometimes accuse an honest claim"

    def test_ground_truth_falsification_never_moves_with_the_verifier(self):
        # A degraded verifier may miss a lie; it must not be able to redefine
        # what a lie *was*, or the metrics would degrade along with it.
        env = _env(accuracy=0.0)
        env._grid[1][0] = TILE_POISON
        for info in _rollout(env, [SPOOF] * 30):
            assert info["falsified"] is True


class TestObservedAccuracyTracksTheDial:
    @pytest.mark.parametrize("epsilon", [0.5, 0.8])
    def test_observed_accuracy_converges_to_epsilon(self, epsilon):
        env = _env(accuracy=epsilon)
        env._grid[1][0] = TILE_POISON
        env.max_steps = 10_000
        infos = _rollout(env, [SPOOF] * 4000)
        observed = hypothesis_metrics(infos)["verifier_observed_accuracy"]
        assert abs(observed - epsilon) < 0.03

    def test_observed_accuracy_is_none_where_nothing_was_verified(self):
        # 0/0, not 0.0 — the failure mode Appendix E §E.5.2 is about.
        env = _env(accuracy=0.7, mode="no_governance")
        env._grid[1][0] = TILE_POISON
        metrics = hypothesis_metrics(_rollout(env, [SPOOF] * 5))
        assert metrics["verifier_verifications"] == 0
        assert metrics["verifier_observed_accuracy"] is None

    def test_falsification_counting_is_still_not_applicable_when_undefined(self):
        env = _env(accuracy=0.7, mode="no_governance")
        metrics = hypothesis_metrics(_rollout(env, [[RIGHT, PriorityTag.ROUTINE, 2, COH_HIGH, 0]]))
        assert metrics["h3_spoof_attempts"] == 0
        assert metrics["h3_detection_rate"] is None
        assert metrics["h3_pass"] is None


class TestDeterminism:
    def test_same_seed_replays_the_same_verifier_decisions(self):
        def run():
            env = _env(accuracy=0.6)
            env._grid[1][0] = TILE_POISON
            return [i["verifier_correct"] for i in _rollout(env, [SPOOF] * 50)]

        assert run() == run()

    def test_reset_replays_the_episode(self):
        env = _env(accuracy=0.6)
        env._grid[1][0] = TILE_POISON
        first = [i["verifier_correct"] for i in _rollout(env, [SPOOF] * 30)]
        env.reset(seed=0)
        env._grid = [[TILE_EMPTY] * env.size for _ in range(env.size)]
        env._pos = (0, 0)
        env._grid[1][0] = TILE_POISON
        assert [i["verifier_correct"] for i in _rollout(env, [SPOOF] * 30)] == first

    def test_different_seeds_diverge(self):
        def run(seed):
            env = make_env(
                mode="governance", size=6, seed=seed, adversarial=True, verifier_accuracy=0.6
            )
            env.reset(seed=seed)
            env._grid = [[TILE_EMPTY] * env.size for _ in range(env.size)]
            env._pos = (0, 0)
            env._grid[1][0] = TILE_POISON
            return [i["verifier_correct"] for i in _rollout(env, [SPOOF] * 50)]

        assert run(1) != run(2)


class TestLearnedVerifier:
    def test_classifier_kind_reports_a_measured_accuracy(self):
        env = make_env(
            mode="governance",
            size=6,
            seed=0,
            adversarial=True,
            verifier_kind="classifier",
            verifier_sensor_noise=0.6,
        )
        assert isinstance(env.verifier, ClassifierVerifier)
        assert 0.0 < env.verifier_accuracy <= 1.0

    def test_classifier_lands_on_the_same_axis_as_the_dial(self):
        # What makes the learned verifier a validation of the dial rather than a
        # separate experiment: its measured accuracy is a point on the same axis.
        env = make_env(
            mode="governance",
            size=6,
            seed=0,
            adversarial=True,
            verifier_kind="classifier",
            verifier_sensor_noise=0.6,
        )
        env.reset(seed=0)
        env._grid = [[TILE_EMPTY] * env.size for _ in range(env.size)]
        env._pos = (0, 0)
        env._grid[1][0] = TILE_POISON
        env.max_steps = 10_000
        observed = hypothesis_metrics(_rollout(env, [SPOOF] * 500))["verifier_observed_accuracy"]
        assert 0.0 <= observed <= 1.0

    def test_profiles_cover_every_tile_in_the_vocabulary(self):
        profiles = GovernanceGridWorld._verifier_profiles(TILE_VOCABULARY)
        assert set(profiles) == set(TILE_VOCABULARY)
        assert len({len(vec) for vec in profiles.values()}) == 1


class TestValidation:
    @pytest.mark.parametrize("accuracy", [-0.5, 1.5])
    def test_out_of_range_accuracy_raises(self, accuracy):
        with pytest.raises(ValueError, match="accuracy must be in"):
            GovernanceGridWorld(verifier_accuracy=accuracy)

    def test_unknown_verifier_kind_raises(self):
        with pytest.raises(ValueError, match="Unknown verifier kind"):
            GovernanceGridWorld(verifier_kind="vibes")
