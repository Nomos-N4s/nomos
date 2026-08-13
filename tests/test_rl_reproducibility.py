"""Tests for RL reproducibility helpers (E6, #264)."""

import json
import random
import tempfile

import pytest

from src.nomos.experiments.rl_seeding import seed_everything
from src.nomos.experiments.rl_validate import main, validate_protocol


class TestSeedEverything:
    def test_returns_seed(self):
        assert seed_everything(123) == 123

    def test_python_random_is_reproducible(self):
        seed_everything(7)
        a = [random.random() for _ in range(5)]
        seed_everything(7)
        b = [random.random() for _ in range(5)]
        assert a == b

    def test_numpy_is_reproducible(self):
        import numpy as np

        seed_everything(11)
        a = np.random.rand(4).tolist()
        seed_everything(11)
        b = np.random.rand(4).tolist()
        assert a == b

    def test_torch_is_reproducible(self):
        # torch ships in the optional `rl` extra; the default test environment
        # does not install it.
        torch = pytest.importorskip("torch")

        seed_everything(5)
        a = torch.rand(3)
        seed_everything(5)
        b = torch.rand(3)
        assert torch.equal(a, b)

    def test_different_seeds_differ(self):
        seed_everything(1)
        a = [random.random() for _ in range(5)]
        seed_everything(2)
        b = [random.random() for _ in range(5)]
        assert a != b


def _valid_aggregate():
    mean_ci = {"mean": 0.0, "ci95": 0.0, "n": 5}
    unit_ci = {"mean": 1.0, "ci95": 0.0, "n": 5}
    return {
        "protocol": {
            "modes": ["governance"],
            "seeds": [42, 43, 44, 45, 46],
            "total_timesteps": 100000,
            "hyperparameters": {"policy": "MlpPolicy"},
        },
        "environment": {"python": "3.11.0"},
        "results": {
            "governance": {
                "n_seeds": 5,
                "avg_reward": mean_ci,
                "avg_violations": mean_ci,
                "veto_precision": unit_ci,
                "veto_recall": unit_ci,
                "governance_bypass_rate": mean_ci,
                "safety_silenced_rate": mean_ci,
                "h1": {"pass": True, "over_budget_events": 0, "max_admitted": 3},
                "h2": {"pass": True, "spoof_bypass_rate": mean_ci},
                "h3": {"pass": True, "detection_rate": unit_ci, "bypass_rate": mean_ci},
            }
        },
    }


class TestValidateProtocol:
    def test_valid_aggregate_has_no_problems(self):
        assert validate_protocol(_valid_aggregate()) == []

    def test_missing_results_flagged(self):
        agg = _valid_aggregate()
        del agg["results"]
        problems = validate_protocol(agg)
        assert any("results" in p for p in problems)

    def test_nan_violations_flagged(self):
        agg = _valid_aggregate()
        agg["results"]["governance"]["avg_violations"]["mean"] = float("nan")
        problems = validate_protocol(agg)
        assert any("avg_violations" in p for p in problems)

    def test_out_of_range_bypass_rate_flagged(self):
        agg = _valid_aggregate()
        agg["results"]["governance"]["governance_bypass_rate"]["mean"] = 1.5
        problems = validate_protocol(agg)
        assert any("governance_bypass_rate" in p for p in problems)

    def test_missing_hypothesis_verdict_flagged(self):
        agg = _valid_aggregate()
        del agg["results"]["governance"]["h3"]
        problems = validate_protocol(agg)
        assert any("h3" in p for p in problems)

    def test_negative_ci_flagged(self):
        agg = _valid_aggregate()
        agg["results"]["governance"]["avg_reward"]["ci95"] = -1.0
        problems = validate_protocol(agg)
        assert any("ci95" in p for p in problems)

    def test_nan_hypothesis_rate_flagged(self):
        # Regression: hypothesis rates were unchecked, so a broken run could
        # publish NaN detection rates and still exit CI green.
        agg = _valid_aggregate()
        agg["results"]["governance"]["h3"]["detection_rate"]["mean"] = float("nan")
        problems = validate_protocol(agg)
        assert any("h3.detection_rate" in p for p in problems)

    def test_out_of_range_spoof_bypass_rate_flagged(self):
        agg = _valid_aggregate()
        agg["results"]["governance"]["h2"]["spoof_bypass_rate"]["mean"] = 7.0
        problems = validate_protocol(agg)
        assert any("h2.spoof_bypass_rate" in p for p in problems)

    def test_missing_hypothesis_rate_flagged(self):
        agg = _valid_aggregate()
        del agg["results"]["governance"]["h3"]["detection_rate"]
        problems = validate_protocol(agg)
        assert any("missing detection_rate" in p for p in problems)

    def test_not_applicable_verdict_is_valid(self):
        # None means "hypothesis does not apply to this mode" and must not be
        # reported as a malformed result.
        agg = _valid_aggregate()
        agg["results"]["governance"]["h3"]["pass"] = None
        assert validate_protocol(agg) == []


class TestValidateMain:
    def test_main_ok_on_valid_file(self):
        with tempfile.TemporaryDirectory() as d:
            import os

            path = os.path.join(d, "adversary_protocol.json")
            with open(path, "w") as fh:
                json.dump(_valid_aggregate(), fh)
            assert main([d]) == 0  # resolves the json inside the dir
            assert main([path]) == 0

    def test_main_fails_on_invalid_file(self):
        with tempfile.TemporaryDirectory() as d:
            import os

            path = os.path.join(d, "adversary_protocol.json")
            agg = _valid_aggregate()
            del agg["results"]
            with open(path, "w") as fh:
                json.dump(agg, fh)
            assert main([path]) == 1

    def test_main_missing_file(self):
        assert main(["/nonexistent/path/x.json"]) == 1

    def test_main_no_args(self):
        assert main([]) == 2
