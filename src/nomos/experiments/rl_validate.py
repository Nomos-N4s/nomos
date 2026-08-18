"""Validate an RL adversary protocol result (E6, #264).

Used by the CI smoke run to assert the harness produced a *sane* result — finite
numbers in plausible ranges — without asserting specific values (which depend on
seed and timesteps). Guards against silent breakage of the pipeline.

Usage::

    python -m nomos.experiments.rl_validate results/rl_adversary/adversary_protocol.json
    python -m nomos.experiments.rl_validate results/rl_adversary   # finds the json

Exits 0 if the result is well-formed and sane, 1 otherwise (printing problems).
"""

from __future__ import annotations

import json
import math
import os
import sys
from collections.abc import Mapping
from typing import Any

from .provenance import verify_preregistration


def _finite(value: Any) -> bool:
    return isinstance(value, int | float) and math.isfinite(value)


def _check_mean_ci(name: str, block: Any, problems: list[str], lo: float, hi: float) -> None:
    if not isinstance(block, Mapping) or "mean" not in block:
        problems.append(f"{name}: missing mean/ci block")
        return
    mean = block.get("mean")
    ci = block.get("ci95")
    if not _finite(mean):
        problems.append(f"{name}.mean is not finite: {mean!r}")
    elif not (lo <= mean <= hi):
        problems.append(f"{name}.mean {mean} outside [{lo}, {hi}]")
    if not _finite(ci) or ci < 0:
        problems.append(f"{name}.ci95 is not a non-negative finite number: {ci!r}")


def validate_protocol(aggregate: Mapping[str, Any]) -> list[str]:
    """Return a list of problems with an aggregate result (empty = valid)."""
    problems: list[str] = []

    protocol = aggregate.get("protocol")
    if not isinstance(protocol, Mapping):
        problems.append("missing 'protocol' block")
    else:
        for key in ("modes", "seeds", "total_timesteps", "hyperparameters"):
            if key not in protocol:
                problems.append(f"protocol missing '{key}'")

    results = aggregate.get("results")
    if not isinstance(results, Mapping) or not results:
        problems.append("missing or empty 'results'")
        return problems

    for mode, data in results.items():
        if not isinstance(data, Mapping):
            problems.append(f"{mode}: result is not an object")
            continue
        if data.get("n_seeds", 0) < 1:
            problems.append(f"{mode}: n_seeds < 1")
        _check_mean_ci(f"{mode}.avg_reward", data.get("avg_reward"), problems, -1e6, 1e6)
        _check_mean_ci(f"{mode}.avg_violations", data.get("avg_violations"), problems, 0.0, 1e6)
        _check_mean_ci(f"{mode}.veto_precision", data.get("veto_precision"), problems, 0.0, 1.0)
        _check_mean_ci(f"{mode}.veto_recall", data.get("veto_recall"), problems, 0.0, 1.0)
        _check_mean_ci(
            f"{mode}.governance_bypass_rate", data.get("governance_bypass_rate"), problems, 0.0, 1.0
        )
        for hyp in ("h1", "h2", "h3"):
            block = data.get(hyp)
            if not isinstance(block, Mapping) or "pass" not in block:
                problems.append(f"{mode}.{hyp}: missing pass verdict")
                continue
            # None is a legitimate verdict: the hypothesis does not apply to
            # this mode. Anything other than a bool or None is malformed.
            if not isinstance(block["pass"], bool) and block["pass"] is not None:
                problems.append(f"{mode}.{hyp}.pass is not a bool or None")

        # The hypothesis rates are the published result, so require them and
        # range-check them: a NaN or out-of-range rate must fail CI rather than
        # sail through because only the top-level metrics were inspected.
        h2 = data.get("h2")
        if isinstance(h2, Mapping):
            if "spoof_bypass_rate" not in h2:
                problems.append(f"{mode}.h2: missing spoof_bypass_rate")
            else:
                _check_mean_ci(
                    f"{mode}.h2.spoof_bypass_rate", h2["spoof_bypass_rate"], problems, 0.0, 1.0
                )
        h3 = data.get("h3")
        if isinstance(h3, Mapping):
            for key in ("detection_rate", "bypass_rate"):
                if key not in h3:
                    problems.append(f"{mode}.h3: missing {key}")
                else:
                    _check_mean_ci(f"{mode}.h3.{key}", h3[key], problems, 0.0, 1.0)

    return problems


def validate_sweep(frontier: Mapping[str, Any]) -> list[str]:
    """Return a list of problems with an ε-sweep frontier (empty = valid).

    Checks the shape of the result and the sanity of its numbers, never their
    values: a cliff and a plateau are both legitimate outcomes, and a validator
    that rejected one of them would be enforcing a conclusion.

    What it does insist on is that the claim to being pre-registered is backed
    by something. A frontier with no pre-registration hash is not a weaker
    result, it is an unfalsifiable one, so its absence is an error rather than
    a warning.
    """
    problems: list[str] = []

    problems.extend(verify_preregistration(frontier.get("preregistration")))

    sweep = frontier.get("sweep")
    if not isinstance(sweep, Mapping):
        problems.append("missing 'sweep' block")
    else:
        for key in ("epsilons", "arms", "seeds", "total_timesteps", "environment_config"):
            if key not in sweep:
                problems.append(f"sweep missing '{key}'")

    points = frontier.get("points")
    if not isinstance(points, list) or not points:
        problems.append("missing or empty 'points'")
        return problems

    for point in points:
        if not isinstance(point, Mapping):
            problems.append("point is not an object")
            continue
        label = f"point(arm={point.get('arm')}, eps={point.get('epsilon')})"
        epsilon = point.get("epsilon")
        if not _finite(epsilon) or not 0.0 <= float(epsilon) <= 1.0:
            problems.append(f"{label}: epsilon outside [0, 1]")
        if point.get("n_seeds", 0) < 1:
            problems.append(f"{label}: n_seeds < 1")
        for key in ("bypass_rate", "veto_precision", "veto_recall"):
            if key not in point:
                problems.append(f"{label}: missing {key}")
            else:
                _check_mean_ci(f"{label}.{key}", point[key], problems, 0.0, 1.0)

    verdicts = frontier.get("verdicts")
    if not isinstance(verdicts, Mapping):
        problems.append("missing 'verdicts' block")
        return problems
    for hypothesis in ("h4", "h5", "h6", "h7"):
        block = verdicts.get(hypothesis)
        if not isinstance(block, Mapping) or "pass" not in block:
            problems.append(f"verdicts.{hypothesis}: missing pass verdict")
        elif not isinstance(block["pass"], bool) and block["pass"] is not None:
            problems.append(f"verdicts.{hypothesis}.pass is not a bool or None")
    if "curve_shape" not in verdicts:
        problems.append("verdicts: missing curve_shape")

    # A partial sweep is not a curve. Scoring silently over whichever points
    # happen to be on disk would make "every point passed" and "the point that
    # would have failed never ran" indistinguishable — the 0/0-as-0.0 defect one
    # level up. The verdicts already degrade to None when coverage is short;
    # this makes the incompleteness itself an error rather than a footnote.
    coverage = verdicts.get("coverage")
    if not isinstance(coverage, Mapping):
        problems.append("verdicts: missing coverage block")
    elif not coverage.get("complete", False):
        missing = coverage.get("missing") or []
        problems.append(
            f"verdicts.coverage: sweep is incomplete — "
            f"{len(missing)} expected (arm, epsilon) point(s) absent: {missing[:8]}"
        )
    return problems


def _resolve_path(path: str) -> str:
    if os.path.isdir(path):
        frontier = os.path.join(path, "verifier_frontier.json")
        if os.path.isfile(frontier):
            return frontier
        return os.path.join(path, "adversary_protocol.json")
    return path


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python -m nomos.experiments.rl_validate <results_dir_or_json>")
        return 2
    path = _resolve_path(args[0])
    if not os.path.isfile(path):
        print(f"ERROR: result file not found: {path}")
        return 1
    with open(path) as fh:
        document = json.load(fh)

    # Dispatch on the document's own shape rather than on the filename, so a
    # renamed or copied artifact is still validated as what it actually is.
    is_frontier = "points" in document and "sweep" in document
    problems = validate_sweep(document) if is_frontier else validate_protocol(document)
    if problems:
        print(f"INVALID: {len(problems)} problem(s) in {path}")
        for p in problems:
            print(f"  - {p}")
        return 1
    if is_frontier:
        print(f"OK: {path} is well-formed and sane ({len(document['points'])} sweep points)")
    else:
        print(f"OK: {path} is well-formed and sane ({len(document['results'])} modes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
