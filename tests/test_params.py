from src.nomos.identity.params import (
    DEFAULT_PARAMETER_ENVELOPE,
    BoundedParameter,
    ParameterEnvelope,
)


class TestBoundedParameter:
    def test_default_initializes_current(self):
        p = BoundedParameter(name="test", default=5, bounds=(0, 10))
        assert p.current == 5

    def test_set_within_bounds_succeeds(self):
        p = BoundedParameter(name="x", default=5, bounds=(0, 10))
        assert p.set(7)
        assert p.current == 7

    def test_set_below_low_fails(self):
        p = BoundedParameter(name="x", default=5, bounds=(3, 10))
        assert not p.set(1)
        assert p.current == 5

    def test_set_above_high_fails(self):
        p = BoundedParameter(name="x", default=5, bounds=(0, 10))
        assert not p.set(15)
        assert p.current == 5

    def test_set_at_low_succeeds(self):
        p = BoundedParameter(name="x", default=5, bounds=(3, 10))
        assert p.set(3)
        assert p.current == 3

    def test_set_at_high_succeeds(self):
        p = BoundedParameter(name="x", default=5, bounds=(3, 10))
        assert p.set(10)
        assert p.current == 10

    def test_explicit_current_overrides_default(self):
        p = BoundedParameter(name="x", default=5, bounds=(0, 10), current=8)
        assert p.current == 8

    def test_unbounded_low(self):
        p = BoundedParameter(name="x", default=5, bounds=(None, 10))
        assert p.set(-100)
        assert p.current == -100

    def test_unbounded_high(self):
        p = BoundedParameter(name="x", default=5, bounds=(0, None))
        assert p.set(1000)
        assert p.current == 1000


class TestParameterEnvelope:
    def test_register_and_get(self):
        env = ParameterEnvelope()
        env.register("quorum", 0.5, (0.3, 0.7))
        assert env.get("quorum") == 0.5

    def test_set_unknown_returns_false(self):
        env = ParameterEnvelope()
        assert not env.set("nonexistent", 10)

    def test_get_unknown_returns_none(self):
        env = ParameterEnvelope()
        assert env.get("ghost") is None

    def test_set_respects_bounds(self):
        env = ParameterEnvelope()
        env.register("rate", 0.5, (0.0, 1.0))
        assert env.set("rate", 2.0) is False
        assert env.get("rate") == 0.5
        assert env.set("rate", 0.8)
        assert env.get("rate") == 0.8

    def test_reset_to_defaults(self):
        env = ParameterEnvelope()
        env.register("a", 1, (0, 10))
        env.register("b", 2, (0, 10))
        env.set("a", 9)
        env.set("b", 1)
        env.reset_to_defaults()
        assert env.get("a") == 1
        assert env.get("b") == 2

    def test_snapshot(self):
        env = ParameterEnvelope()
        env.register("x", 10, (0, 100))
        env.register("y", 20, (0, 100))
        env.set("x", 50)
        s = env.snapshot()
        assert s == {"x": 50, "y": 20}

    def test_snapshot_is_copy(self):
        env = ParameterEnvelope()
        env.register("x", 10, (0, 100))
        s = env.snapshot()
        s["x"] = 999
        assert env.get("x") == 10


class TestDefaultParameterEnvelope:
    def test_has_expected_params(self):
        expected = {"quorum_threshold", "max_deliberation_rounds", "member_min_budget", "deadlock_threshold_cycles"}
        actual = set(DEFAULT_PARAMETER_ENVELOPE.snapshot().keys())
        assert actual == expected

    def test_quorum_threshold_bounds(self):
        assert DEFAULT_PARAMETER_ENVELOPE.set("quorum_threshold", 0.3)
        assert DEFAULT_PARAMETER_ENVELOPE.set("quorum_threshold", 0.7)
        assert not DEFAULT_PARAMETER_ENVELOPE.set("quorum_threshold", 0.2)
        assert not DEFAULT_PARAMETER_ENVELOPE.set("quorum_threshold", 0.8)

    def test_can_reset_to_defaults(self):
        DEFAULT_PARAMETER_ENVELOPE.set("quorum_threshold", 0.6)
        DEFAULT_PARAMETER_ENVELOPE.reset_to_defaults()
        assert DEFAULT_PARAMETER_ENVELOPE.get("quorum_threshold") == 0.5
