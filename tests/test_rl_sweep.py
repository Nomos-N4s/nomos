"""Tests for the ε-sweep, its scoring, and its figures (V4, #275).

The sweep's job is to report a curve shape honestly, so the scoring is tested
against curves of every shape it might have to describe — a plateau, a cliff, a
flat-zero line the adversary never troubled — including the case that matters
most: a curve where H4 and H5 pass but H6 fails, meaning the layer "held"
against an adversary that could not play, and the passes carry no information.
"""

import json
import os
import tempfile

import pytest

from src.nomos.experiments.rl_sweep import (
    ANCHOR_EPSILON,
    ARMS,
    EPSILON_GRID,
    H4_MAX_BYPASS,
    H5_MAX_STEP,
    H6_MIN_BYPASS,
    preregistration_provenance,
    score_curve,
)
from src.nomos.experiments.rl_validate import main, validate_sweep


def _ci(mean, ci95=0.0, n=5):
    return {"mean": mean, "ci95": ci95, "n": n}


def _point(epsilon, arm, bypass, *, integrity=0.2, detection=1.0, region=0.0):
    return {
        "epsilon": epsilon,
        "arm": arm,
        "n_seeds": 5,
        "effective_accuracy": epsilon,
        "observed_accuracy": _ci(epsilon),
        "bypass_rate": _ci(bypass),
        "safety_silenced_rate": _ci(1.0),
        "detection_rate": _ci(detection),
        "veto_precision": _ci(1.0),
        "veto_recall": _ci(1.0 - bypass),
        "avg_violations": _ci(bypass * 10),
        "spoof_region_rate": _ci(region),
        "falsified_integrity_mean": _ci(integrity),
        "falsified_integrity_max": _ci(integrity + 0.1),
        "ambiguous_bypass_rate": _ci(bypass * 2),
        "h1_pass": True,
        "h2_pass": True,
        "h3_pass": True,
    }


def _curve(rates, arm="unshaped", **kwargs):
    """Build one arm's points from an ε -> bypass-rate mapping."""
    return [_point(eps, arm, rate, **kwargs) for eps, rate in rates.items()]


GRACEFUL = {1.0: 0.0, 0.99: 0.01, 0.95: 0.04, 0.9: 0.08, 0.8: 0.15, 0.7: 0.22, 0.6: 0.3, 0.5: 0.38}
CLIFF = {1.0: 0.0, 0.99: 0.0, 0.95: 0.4, 0.9: 0.6, 0.8: 0.7, 0.7: 0.75, 0.6: 0.8, 0.5: 0.85}
FLAT = dict.fromkeys(EPSILON_GRID, 0.0)


class TestConstants:
    def test_grid_is_dense_near_one(self):
        # A cliff between "right 99% of the time" and "right 95% of the time"
        # would be invisible on a uniformly spaced grid.
        assert EPSILON_GRID[0] == 1.0
        assert list(EPSILON_GRID) == sorted(EPSILON_GRID, reverse=True)
        assert 0.99 in EPSILON_GRID and 0.95 in EPSILON_GRID

    def test_both_arms_are_swept(self):
        assert set(ARMS) == {"unshaped", "shaped"}

    def test_anchor_is_the_oracle(self):
        assert ANCHOR_EPSILON == 1.0


class TestPreregistrationProvenance:
    def test_hashes_the_real_preregistration(self):
        provenance = preregistration_provenance()
        assert provenance["sha256"] is not None
        assert len(provenance["sha256"]) == 64

    def test_records_the_commit_that_last_touched_it(self):
        # The claim "pre-registered" is a claim about time. A hash proves the
        # text has not moved; the commit proves it predates the run.
        provenance = preregistration_provenance()
        assert provenance["commit"] is not None
        assert provenance["committed_at"] is not None

    def test_missing_file_degrades_rather_than_raises(self):
        provenance = preregistration_provenance("book/does-not-exist.md")
        assert provenance["sha256"] is None
        assert provenance["path"] == "book/does-not-exist.md"

    def test_hash_changes_with_the_content(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.md"), os.path.join(d, "b.md")
            with open(a, "w") as fh:
                fh.write("H4: bypass <= 0.05")
            with open(b, "w") as fh:
                fh.write("H4: bypass <= 0.50")
            assert preregistration_provenance(a)["sha256"] != preregistration_provenance(b)["sha256"]


class TestScoreGracefulCurve:
    def setup_method(self):
        self.verdicts = score_curve(_curve(GRACEFUL) + _curve(GRACEFUL, arm="shaped", integrity=0.3))

    def test_h4_passes_on_the_plateau(self):
        assert self.verdicts["h4"]["pass"] is True
        assert self.verdicts["h4"]["worst"] <= H4_MAX_BYPASS

    def test_h5_finds_no_cliff(self):
        assert self.verdicts["h5"]["pass"] is True
        assert self.verdicts["h5"]["worst_step"] <= H5_MAX_STEP

    def test_h6_confirms_the_game_was_winnable(self):
        assert self.verdicts["h6"]["pass"] is True
        assert self.verdicts["h6"]["best_arm_bypass"] >= H6_MIN_BYPASS

    def test_shape_is_reported_as_graceful(self):
        shape = self.verdicts["curve_shape"]
        assert shape["cliff"] is False
        assert shape["critical_epsilon_region"] is None
        assert shape["monotone"] is True


class TestScoreCliffCurve:
    def setup_method(self):
        self.verdicts = score_curve(_curve(CLIFF))

    def test_h4_fails_because_the_plateau_broke(self):
        assert self.verdicts["h4"]["pass"] is False

    def test_h5_detects_the_cliff(self):
        assert self.verdicts["h5"]["pass"] is False
        assert self.verdicts["h5"]["worst_step"] > H5_MAX_STEP

    def test_the_critical_region_is_located(self):
        shape = self.verdicts["curve_shape"]
        assert shape["cliff"] is True
        # The 0.99 -> 0.95 step is the drop; the region brackets it.
        assert shape["critical_epsilon_region"] == [0.95, 0.99]
        assert shape["largest_step"]["from_epsilon"] == 0.99


class TestUninformativePasses:
    """The case the epic is really guarding against.

    A flat-zero curve passes H4 and H5 effortlessly — and means nothing, because
    the adversary never got into the game. H6 is what turns that from a
    reassuring result into a flagged one.
    """

    def setup_method(self):
        self.verdicts = score_curve(_curve(FLAT))

    def test_h4_and_h5_pass_on_a_meaningless_curve(self):
        assert self.verdicts["h4"]["pass"] is True
        assert self.verdicts["h5"]["pass"] is True

    def test_but_h6_fails_and_says_so(self):
        assert self.verdicts["h6"]["pass"] is False
        assert self.verdicts["h6"]["best_arm_bypass"] < H6_MIN_BYPASS


class TestH7ShapingVerdict:
    def test_passes_when_the_gradient_moved_and_the_anchor_held(self):
        points = _curve(GRACEFUL, integrity=0.15) + _curve(GRACEFUL, arm="shaped", integrity=0.35)
        h7 = score_curve(points)["h7"]
        assert h7["gradient_alive"] is True
        assert h7["scoreboard_unchanged"] is True
        assert h7["pass"] is True

    def test_fails_when_shaping_did_not_move_the_search(self):
        points = _curve(GRACEFUL, integrity=0.2) + _curve(GRACEFUL, arm="shaped", integrity=0.2)
        h7 = score_curve(points)["h7"]
        assert h7["gradient_alive"] is False
        assert h7["pass"] is False

    def test_fails_when_the_anchor_moved(self):
        # If epsilon = 1.0 no longer reproduces "governance held", shaping has
        # changed the scoreboard and not just the search.
        broken = dict(GRACEFUL)
        broken[1.0] = 0.4
        points = _curve(broken, integrity=0.15) + _curve(broken, arm="shaped", integrity=0.35)
        h7 = score_curve(points)["h7"]
        assert h7["scoreboard_unchanged"] is False
        assert h7["pass"] is False


class TestUndefinedIsNeverFailure:
    def test_missing_plateau_points_give_no_verdict(self):
        partial = score_curve(_curve({0.8: 0.1, 0.7: 0.2}))
        assert partial["h4"]["pass"] is None  # not False
        assert partial["h6"]["pass"] is None

    def test_single_arm_gives_no_h7_verdict(self):
        assert score_curve(_curve(GRACEFUL))["h7"]["pass"] is None

    def test_a_point_with_no_data_is_skipped_rather_than_zeroed(self):
        points = _curve(GRACEFUL)
        points[0]["bypass_rate"] = {"mean": 0.0, "ci95": 0.0, "n": 0}
        verdicts = score_curve(points)
        assert all(s["from_epsilon"] != 1.0 for s in verdicts["curve_shape"]["steps"])

    def test_empty_points_do_not_crash(self):
        verdicts = score_curve([])
        assert verdicts["h4"]["pass"] is None
        assert verdicts["curve_shape"]["largest_step"] is None


def _frontier(points=None):
    return {
        "preregistration": preregistration_provenance(),
        "sweep": {
            "epsilons": list(EPSILON_GRID),
            "arms": list(ARMS),
            "seeds": [42, 43, 44, 45, 46],
            "total_timesteps": 100_000,
            "size": 10,
            "eval_episodes": 10,
            "mode": "governance",
            "anchor_epsilon": ANCHOR_EPSILON,
            "environment_config": {
                "ambiguity_ratio": 0.5,
                "spoof_region": True,
                "claim_resolution": 17,
            },
        },
        "points": points if points is not None else _curve(GRACEFUL),
        "controls": {
            "no_governance": _point(1.0, "control", 1.0),
            "static_mask": _point(1.0, "control", 0.0),
        },
        "verdicts": score_curve(points if points is not None else _curve(GRACEFUL)),
    }


class TestValidateSweep:
    def test_a_well_formed_frontier_has_no_problems(self):
        assert validate_sweep(_frontier()) == []

    def test_a_cliff_is_valid_too(self):
        # Both shapes are legitimate outcomes; a validator that rejected one
        # would be enforcing a conclusion rather than checking a schema.
        assert validate_sweep(_frontier(_curve(CLIFF))) == []

    def test_missing_preregistration_hash_is_an_error(self):
        frontier = _frontier()
        frontier["preregistration"]["sha256"] = None
        assert any("unverifiable" in p for p in validate_sweep(frontier))

    def test_missing_preregistration_block_is_an_error(self):
        frontier = _frontier()
        del frontier["preregistration"]
        assert any("preregistration" in p for p in validate_sweep(frontier))

    def test_out_of_range_epsilon_flagged(self):
        frontier = _frontier()
        frontier["points"][0]["epsilon"] = 1.5
        assert any("epsilon outside" in p for p in validate_sweep(frontier))

    def test_nan_bypass_rate_flagged(self):
        frontier = _frontier()
        frontier["points"][0]["bypass_rate"]["mean"] = float("nan")
        assert any("bypass_rate" in p for p in validate_sweep(frontier))

    def test_out_of_range_bypass_rate_flagged(self):
        frontier = _frontier()
        frontier["points"][0]["bypass_rate"]["mean"] = 3.0
        assert any("bypass_rate" in p for p in validate_sweep(frontier))

    def test_missing_verdict_flagged(self):
        frontier = _frontier()
        del frontier["verdicts"]["h6"]
        assert any("h6" in p for p in validate_sweep(frontier))

    def test_not_applicable_verdicts_are_valid(self):
        frontier = _frontier()
        frontier["verdicts"]["h6"]["pass"] = None
        assert validate_sweep(frontier) == []

    def test_empty_points_flagged(self):
        frontier = _frontier()
        frontier["points"] = []
        assert any("points" in p for p in validate_sweep(frontier))


class TestValidatorDispatch:
    def test_main_validates_a_frontier_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "verifier_frontier.json")
            with open(path, "w") as fh:
                json.dump(_frontier(), fh)
            assert main([d]) == 0  # resolved from the directory
            assert main([path]) == 0

    def test_main_rejects_a_broken_frontier(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "verifier_frontier.json")
            frontier = _frontier()
            frontier["points"] = []
            with open(path, "w") as fh:
                json.dump(frontier, fh)
            assert main([path]) == 1


class TestFigures:
    def test_both_figures_render(self):
        from src.nomos.experiments.rl_figures import generate_frontier_figures

        with tempfile.TemporaryDirectory() as d:
            figures = generate_frontier_figures(_frontier(), output_dir=d)
            assert set(figures) == {"verifier_frontier", "verifier_frontier_panels"}
            for name in figures:
                assert os.path.exists(os.path.join(d, f"{name}.png"))
                assert os.path.exists(os.path.join(d, f"{name}.svg"))

    def test_a_cliff_renders_with_its_region_shaded(self):
        from src.nomos.experiments.rl_figures import plot_verifier_frontier

        with tempfile.TemporaryDirectory() as d:
            frontier = _frontier(_curve(CLIFF))
            assert frontier["verdicts"]["curve_shape"]["critical_epsilon_region"]
            plot_verifier_frontier(frontier, output_dir=d)
            assert os.path.exists(os.path.join(d, "verifier_frontier.png"))

    def test_points_with_no_data_are_dropped_not_zeroed(self):
        from src.nomos.experiments.rl_figures import _series

        frontier = _frontier()
        frontier["points"][0]["bypass_rate"] = {"mean": 0.0, "ci95": 0.0, "n": 0}
        dropped = frontier["points"][0]["epsilon"]
        xs, _, _, _ = _series(frontier, "unshaped", "bypass_rate")
        assert dropped not in xs

    def test_intervals_are_clamped_to_the_feasible_range(self):
        from src.nomos.experiments.rl_figures import _series

        frontier = _frontier([_point(0.5, "unshaped", 0.05)])
        frontier["points"][0]["bypass_rate"] = _ci(0.05, ci95=0.4)
        _, _, lows, highs = _series(frontier, "unshaped", "bypass_rate")
        assert lows[0] == 0.0  # a rate cannot be negative
        assert highs[0] <= 1.0


@pytest.mark.slow
class TestSweepSmoke:
    def test_a_tiny_sweep_runs_end_to_end(self):
        pytest.importorskip("stable_baselines3")
        from src.nomos.experiments.rl_sweep import run_sweep

        with tempfile.TemporaryDirectory() as d:
            frontier = run_sweep(
                epsilons=[1.0, 0.5],
                arms=["unshaped"],
                seeds=[1],
                total_timesteps=200,
                size=6,
                eval_episodes=1,
                controls=False,
                log_dir=d,
            )
            assert os.path.exists(os.path.join(d, "verifier_frontier.json"))
        assert len(frontier["points"]) == 2
        assert {p["epsilon"] for p in frontier["points"]} == {1.0, 0.5}
        assert frontier["preregistration"]["sha256"] is not None
        assert validate_sweep(frontier) == []
