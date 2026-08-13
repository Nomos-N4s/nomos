"""Tests for the tunable-accuracy Integrity verifiers (V1, #272).

The published result rests on an oracle verifier, which makes "the grounded
verifier catches lies" nearly true by construction. These tests pin down the
replacement: an accuracy dial that is honest about being a dial (its observed
accuracy converges to the ε it was given), a learned verifier whose *measured*
accuracy lands on the same axis, and — the regression that protects Appendix E —
an oracle path that draws no randomness at all.
"""

import pytest

from src.nomos.experiments.rl_seeding import derive_rng
from src.nomos.experiments.rl_verifier import (
    VERIFIER_KINDS,
    ClassifierVerifier,
    NoisyVerifier,
    OracleVerifier,
    make_verifier,
)

VOCABULARY = (0, 1, 2, 3)

# Mirrors the GovernanceGridWorld truth profiles: empty, apple, poison, wall.
PROFILES = {
    0: (0.0, 0.1, 0.9, 0.5, 0.2, 0.7, 0.8),
    1: (1.0, 0.0, 1.0, 1.0, 0.3, 0.8, 1.0),
    2: (5.0, 0.9, 0.1, -0.5, 0.8, 0.2, 0.1),
    3: (0.0, 0.5, 0.5, 0.0, 0.1, 0.5, 0.5),
}


class TestDeriveRng:
    def test_same_seed_and_stream_repeat(self):
        a = [derive_rng(7, "verifier").random() for _ in range(5)]
        b = [derive_rng(7, "verifier").random() for _ in range(5)]
        assert a == b

    def test_streams_are_independent(self):
        # The whole point: turning on one noise source must not shift another.
        a = [derive_rng(7, "verifier").random() for _ in range(5)]
        b = [derive_rng(7, "layout").random() for _ in range(5)]
        assert a != b

    def test_different_seeds_differ(self):
        assert derive_rng(1, "verifier").random() != derive_rng(2, "verifier").random()


class TestOracleVerifier:
    def test_always_returns_the_true_tile(self):
        verifier = OracleVerifier()
        for tile in VOCABULARY:
            assert verifier.observe(tile) == tile

    def test_accuracy_is_one(self):
        assert OracleVerifier().accuracy == 1.0

    def test_draws_no_randomness(self):
        # The Appendix E regression guard: if the oracle consumed the shared
        # stream, enabling the dial would shift grid layouts and epsilon = 1.0
        # would stop reproducing the published run.
        verifier = OracleVerifier()
        before = derive_rng(3, "verifier").random()
        for _ in range(100):
            verifier.observe(2)
        assert derive_rng(3, "verifier").random() == before


class TestNoisyVerifierValidation:
    @pytest.mark.parametrize("accuracy", [-0.1, 1.1])
    def test_out_of_range_accuracy_raises(self, accuracy):
        with pytest.raises(ValueError, match="accuracy must be in"):
            NoisyVerifier(accuracy, VOCABULARY)

    def test_single_tile_vocabulary_raises(self):
        with pytest.raises(ValueError, match="at least two tiles"):
            NoisyVerifier(0.5, (2,))

    def test_boundaries_are_allowed(self):
        assert NoisyVerifier(0.0, VOCABULARY).accuracy == 0.0
        assert NoisyVerifier(1.0, VOCABULARY).accuracy == 1.0


class TestNoisyVerifierAccuracy:
    @pytest.mark.parametrize("epsilon", [0.5, 0.7, 0.9, 0.99])
    def test_observed_accuracy_converges_to_epsilon(self, epsilon):
        # The V1 definition of done: the dial must mean what it says.
        verifier = NoisyVerifier(epsilon, VOCABULARY, seed=11)
        trials = 20_000
        correct = sum(verifier.observe(2) == 2 for _ in range(trials))
        assert abs(correct / trials - epsilon) < 0.02

    def test_zero_accuracy_is_never_right(self):
        verifier = NoisyVerifier(0.0, VOCABULARY, seed=3)
        assert all(verifier.observe(2) != 2 for _ in range(500))

    def test_errors_stay_inside_the_vocabulary(self):
        verifier = NoisyVerifier(0.0, VOCABULARY, seed=4)
        assert {verifier.observe(2) for _ in range(500)} <= set(VOCABULARY) - {2}

    def test_errors_are_spread_over_the_other_tiles(self):
        # A verifier that always errs the same way would be a relabelling, not
        # noise — and would make the sweep measure one confusion instead of an
        # error rate.
        verifier = NoisyVerifier(0.0, VOCABULARY, seed=5)
        assert len({verifier.observe(2) for _ in range(500)}) == len(VOCABULARY) - 1


class TestNoisyVerifierDeterminism:
    def test_same_seed_gives_the_same_sequence(self):
        a = NoisyVerifier(0.6, VOCABULARY, seed=42)
        b = NoisyVerifier(0.6, VOCABULARY, seed=42)
        assert [a.observe(2) for _ in range(50)] == [b.observe(2) for _ in range(50)]

    def test_different_seeds_diverge(self):
        a = NoisyVerifier(0.6, VOCABULARY, seed=1)
        b = NoisyVerifier(0.6, VOCABULARY, seed=2)
        assert [a.observe(2) for _ in range(50)] != [b.observe(2) for _ in range(50)]

    def test_reseed_replays_the_stream(self):
        verifier = NoisyVerifier(0.6, VOCABULARY, seed=9)
        first = [verifier.observe(2) for _ in range(50)]
        verifier.reseed(9)
        assert [verifier.observe(2) for _ in range(50)] == first


class TestClassifierVerifier:
    def test_measured_accuracy_is_a_probability(self):
        verifier = ClassifierVerifier(PROFILES, sensor_noise=0.35, seed=0)
        assert 0.0 <= verifier.accuracy <= 1.0

    def test_a_clean_sensor_is_nearly_an_oracle(self):
        verifier = ClassifierVerifier(PROFILES, sensor_noise=0.01, seed=0)
        assert verifier.accuracy > 0.99

    def test_accuracy_degrades_as_the_sensor_degrades(self):
        # This is what puts the learned verifier *on* the epsilon axis: sweeping
        # sensor noise moves it along the same axis the parametric dial spans.
        accuracies = [
            ClassifierVerifier(PROFILES, sensor_noise=noise, seed=0).accuracy
            for noise in (0.05, 0.5, 1.5)
        ]
        assert accuracies == sorted(accuracies, reverse=True)
        assert accuracies[0] > accuracies[-1] + 0.1

    def test_predictions_are_deterministic_for_a_seed(self):
        a = ClassifierVerifier(PROFILES, sensor_noise=0.5, seed=7)
        b = ClassifierVerifier(PROFILES, sensor_noise=0.5, seed=7)
        assert a.accuracy == b.accuracy
        assert [a.observe(2) for _ in range(50)] == [b.observe(2) for _ in range(50)]

    def test_reseed_replays_the_sensor_stream(self):
        verifier = ClassifierVerifier(PROFILES, sensor_noise=0.5, seed=7)
        first = [verifier.observe(2) for _ in range(50)]
        verifier.reseed(7)
        assert [verifier.observe(2) for _ in range(50)] == first

    def test_observations_stay_inside_the_vocabulary(self):
        verifier = ClassifierVerifier(PROFILES, sensor_noise=0.8, seed=1)
        assert {verifier.observe(2) for _ in range(300)} <= set(PROFILES)

    def test_an_untrained_tile_is_not_granted_oracle_access(self):
        # Returning an unknown tile unchanged would hand back ground truth for
        # exactly the tiles the verifier has no competence over.
        verifier = ClassifierVerifier(PROFILES, sensor_noise=0.3, seed=1)
        assert verifier.observe(99) != 99

    def test_too_few_tiles_raises(self):
        with pytest.raises(ValueError, match="at least two tiles"):
            ClassifierVerifier({0: (0.0, 1.0)})

    def test_ragged_profiles_raise(self):
        with pytest.raises(ValueError, match="same length"):
            ClassifierVerifier({0: (0.0, 1.0), 1: (1.0,)})


class TestMakeVerifier:
    def test_full_accuracy_is_the_oracle(self):
        verifier = make_verifier("parametric", 1.0, VOCABULARY, PROFILES)
        assert isinstance(verifier, OracleVerifier)

    def test_below_full_accuracy_is_noisy(self):
        verifier = make_verifier("parametric", 0.9, VOCABULARY, PROFILES, seed=2)
        assert isinstance(verifier, NoisyVerifier)
        assert verifier.accuracy == 0.9

    def test_classifier_kind(self):
        verifier = make_verifier("classifier", 1.0, VOCABULARY, PROFILES, sensor_noise=0.4)
        assert isinstance(verifier, ClassifierVerifier)
        # Accuracy is measured, not taken from the ignored dial argument.
        assert verifier.accuracy < 1.0

    def test_unknown_kind_raises(self):
        with pytest.raises(ValueError, match="Unknown verifier kind"):
            make_verifier("psychic", 0.9, VOCABULARY, PROFILES)

    def test_kinds_constant_is_exhaustive(self):
        for kind in VERIFIER_KINDS:
            assert make_verifier(kind, 0.9, VOCABULARY, PROFILES) is not None
