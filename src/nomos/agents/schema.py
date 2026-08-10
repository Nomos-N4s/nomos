"""
Schema contract for agent benchmark artifacts.

The agent pipeline writes three reports plus a cache manifest to
``results/agent/``. This module is the **committed reference** for
their shape: CI compares *new* outputs against this contract (keys,
types, non-emptiness) — never against values, because values change
when model versions change. Schema stability is the CI contract.

Validated artifacts:

- ``agent_report.md`` — human-readable markdown (non-empty)
- ``agent_benchmark_results.json`` — ``num_pairs``, ``num_steps``,
  ``summary`` (dict of numeric keys), ``pairs`` (non-empty list)
- ``agent_benchmark_summary.csv`` — exact header row
- ``cache_manifest.json`` — per-entry SHA-256 digests matching the
  cache directory on disk (replay verification)

CLI:

    python -m src.nomos.agents.schema check results/agent

Exits 0 when every artifact conforms, 1 otherwise. This is the
command the ``benchmark-agent-smoke`` CI job runs.

Real-world analogy:
    An aviation inspection checklist. The inspector checks the
    flight-recorder tape is present, labelled, and readable — not
    whether the recorded flight was a good one.
"""

import csv
import hashlib
import json
import os
import sys
from typing import Any

from .cache import CACHE_MANIFEST_NAME, DEFAULT_CACHE_DIR
from .report import _SUMMARY_CSV_COLUMNS

#: Report files required, in the order they are checked.
REQUIRED_REPORT_FILES = [
    "agent_report.md",
    "agent_benchmark_results.json",
    "agent_benchmark_summary.csv",
    "cache_manifest.json",
]

#: Top-level keys of ``agent_benchmark_results.json`` with their types.
RESULTS_JSON_KEYS: dict[str, type | tuple[type, ...]] = {
    "num_pairs": int,
    "num_steps": int,
    "summary": dict,
    "pairs": list,
}

#: Keys of the ``summary`` object with their types.
RESULTS_SUMMARY_KEYS: dict[str, type | tuple[type, ...]] = {
    "ungoverned_violation_rate": (int, float),
    "governed_violation_rate": (int, float),
    "governed_rate_never_worse": (int, float),
    "reward_preservation_ratio": (int, float),
    "reward_preservation_ci": list,
    "reward_cohens_d": (int, float),
    "veto_precision": (int, float),
    "veto_recall": (int, float),
    "latency_p50": dict,
    "latency_p95": dict,
}


def _json_types(value: Any, expected: type | tuple[type, ...]) -> bool:
    """Type-check a decoded JSON value.

    ``bool`` is excluded from ``int`` because ``isinstance(True, int)``
    is True and JSON booleans must not pass integer checks.
    """
    if isinstance(value, bool):
        return expected is bool
    return isinstance(value, expected)


def validate_agent_artifacts(
    output_dir: str = "results/agent",
    cache_dir: str = DEFAULT_CACHE_DIR,
) -> list[str]:
    """Validate the agent benchmark artifacts against the contract.

    Args:
        output_dir: Directory holding the report artifacts.
        cache_dir: Directory holding the cache entries referenced by
            the manifest.

    Returns:
        A list of human-readable problems. An empty list means every
        artifact conforms.
    """
    problems: list[str] = []

    for name in REQUIRED_REPORT_FILES:
        path = os.path.join(output_dir, name)
        if not os.path.exists(path):
            problems.append(f"missing required artifact: {name}")
            continue
        if os.path.getsize(path) == 0:
            problems.append(f"artifact is empty: {name}")

    results_path = os.path.join(output_dir, "agent_benchmark_results.json")
    if os.path.exists(results_path):
        try:
            with open(results_path, encoding="utf-8") as f:
                results = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            problems.append(f"unparseable agent_benchmark_results.json: {e}")
            results = None
        if isinstance(results, dict):
            for key, expected in RESULTS_JSON_KEYS.items():
                if key not in results:
                    problems.append(f"agent_benchmark_results.json missing key: {key}")
                elif not _json_types(results[key], expected):
                    problems.append(
                        f"agent_benchmark_results.json key {key!r} has wrong type: "
                        f"{type(results[key]).__name__}"
                    )
            summary = results.get("summary")
            if isinstance(summary, dict):
                for key, expected in RESULTS_SUMMARY_KEYS.items():
                    if key not in summary:
                        problems.append(f"agent_benchmark_results.json summary missing key: {key}")
                    elif not _json_types(summary[key], expected):
                        problems.append(
                            f"agent_benchmark_results.json summary key {key!r} has wrong type: "
                            f"{type(summary[key]).__name__}"
                        )
            elif "summary" in results:
                problems.append("agent_benchmark_results.json summary must be an object")
            pairs = results.get("pairs")
            if isinstance(pairs, list) and not pairs:
                problems.append("agent_benchmark_results.json pairs must be non-empty")

    csv_path = os.path.join(output_dir, "agent_benchmark_summary.csv")
    if os.path.exists(csv_path):
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                header = next(csv.reader(f))
            if header != _SUMMARY_CSV_COLUMNS:
                problems.append(
                    f"agent_benchmark_summary.csv header mismatch: {header!r} "
                    f"expected {_SUMMARY_CSV_COLUMNS!r}"
                )
        except (OSError, StopIteration) as e:
            problems.append(f"agent_benchmark_summary.csv unreadable: {e}")

    manifest_path = os.path.join(output_dir, CACHE_MANIFEST_NAME)
    if os.path.exists(manifest_path):
        problems.extend(validate_cache_manifest(manifest_path, cache_dir))

    return problems


def validate_cache_manifest(manifest_path: str, cache_dir: str) -> list[str]:
    """Check a cache manifest against the cache directory on disk.

    Every entry listed must exist in ``cache_dir`` with the digest
    recorded in the manifest (recomputed byte-for-byte), and every
    entry on disk must be listed.

    Args:
        manifest_path: Path of the manifest JSON file.
        cache_dir: Directory holding the cache entries.

    Returns:
        A list of human-readable problems (empty when consistent).
    """
    problems: list[str] = []
    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return [f"unparseable cache manifest: {e}"]

    recorded = manifest.get("files")
    if not isinstance(recorded, dict):
        return ["cache manifest missing files object"]

    on_disk: dict[str, str] = {}
    if os.path.isdir(cache_dir):
        for name in os.listdir(cache_dir):
            if not name.endswith(".json"):
                continue
            path = os.path.join(cache_dir, name)
            try:
                with open(path, "rb") as f:
                    on_disk[name] = hashlib.sha256(f.read()).hexdigest()
            except OSError as e:
                problems.append(f"cache entry unreadable {name}: {e}")

    for name, digest in sorted(recorded.items()):
        actual = on_disk.get(name)
        if actual is None:
            problems.append(f"manifest lists missing cache entry: {name}")
        elif actual != digest:
            problems.append(f"cache entry digest mismatch: {name}")
    for name in sorted(on_disk):
        if name not in recorded:
            problems.append(f"cache entry not listed in manifest: {name}")
    if not recorded:
        problems.append("cache manifest lists no entries")
    return problems


def main() -> None:
    """CLI entry point: ``python -m src.nomos.agents.schema check [dir]``."""
    output_dir = "results/agent"
    args = [a for a in sys.argv[1:] if a not in ("check",)]
    if args:
        output_dir = args[0]
    problems = validate_agent_artifacts(output_dir)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        print(f"Agent artifact contract violated ({len(problems)} problem(s))")
        sys.exit(1)
    print("Agent artifact contract: OK")
    print(f"  reports: {os.path.join(output_dir, 'agent_report.md')}")
    print(f"  results: {os.path.join(output_dir, 'agent_benchmark_results.json')}")
    print(f"  summary: {os.path.join(output_dir, 'agent_benchmark_summary.csv')}")
    print(f"  manifest: {os.path.join(output_dir, CACHE_MANIFEST_NAME)}")


if __name__ == "__main__":
    main()
