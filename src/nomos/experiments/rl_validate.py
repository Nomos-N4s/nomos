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
            elif not isinstance(block["pass"], bool):
                problems.append(f"{mode}.{hyp}.pass is not a bool")

    return problems


def _resolve_path(path: str) -> str:
    if os.path.isdir(path):
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
        aggregate = json.load(fh)

    problems = validate_protocol(aggregate)
    if problems:
        print(f"INVALID: {len(problems)} problem(s) in {path}")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"OK: {path} is well-formed and sane ({len(aggregate['results'])} modes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
