"""
CLI entry point for formal prediction verification.

Runs the 12 executable predictions from :mod:`predictions` and prints
a formatted summary. Supports chapter-level filtering and JSON export.

The predictions are Python asserts. This command runs no Lean, so its
summary counts passing tests and not proofs; each line carries the
prediction's row from :data:`predictions.LEAN_COVERAGE` to say which
theorem, if any, states the same property of the Lean model.

Usage:

.. code-block:: bash

    # Run all 12 predictions
    python -m src.nomos.prove.runner --all

    # Chapter 2 only
    python -m src.nomos.prove.runner --ch2

    # Single prediction
    python -m src.nomos.prove.runner --single 5

    # Export to JSON
    python -m src.nomos.prove.runner --all --json results/prove_results.json
"""

import argparse
import json
import sys
from collections import Counter

from .predictions import ALL_PREDICTIONS, LeanStatus, PredictionResult


def run_all() -> list[PredictionResult]:
    """Execute every prediction function in :data:`ALL_PREDICTIONS`.

    Catches exceptions and wraps them as failed predictions so one
    flaky test doesn't crash the entire suite.

    Returns:
        List of :class:`PredictionResult`, one per prediction.
    """
    results = []
    for pred_fn in ALL_PREDICTIONS:
        try:
            result = pred_fn()
        except Exception as e:
            result = PredictionResult(
                id=ALL_PREDICTIONS.index(pred_fn) + 1,
                chapter="ERR",
                section="0",
                description=pred_fn.__name__,
                passed=False,
                evidence=f"Exception: {e}",
            )
        results.append(result)
    return results


def filter_by_chapter(results: list[PredictionResult], chapter: str) -> list[PredictionResult]:
    """Filter results to a single chapter.

    Args:
        results: Full list of prediction results.
        chapter: Chapter identifier (e.g. ``"Ch2"``, ``"Ch3"``).

    Returns:
        Filtered list.
    """
    return [r for r in results if r.chapter == chapter]


def lean_coverage_tally(results: list[PredictionResult]) -> str:
    """Summarise how the given results relate to the Lean corpus.

    Counted from :data:`predictions.LEAN_COVERAGE` at call time rather than
    written down, so the line cannot drift from the map it reports on.

    Args:
        results: The prediction results to tally.

    Returns:
        One line, e.g. ``"3 proved of the Lean model | 6 no counterpart"``,
        or the empty string when no result carries a coverage row.
    """
    counted = Counter(r.lean.status for r in results if r.lean is not None)
    return " | ".join(
        f"{counted[status]} {status.value}" for status in LeanStatus if counted[status]
    )


def print_summary(results: list[PredictionResult]):
    """Print a formatted test-runner-style summary to stdout.

    Real-world analogy:
        Like ``pytest -v`` output — each test gets a PASS/FAIL line
        with its evidence string, followed by a summary count.

    Each prediction also gets its Lean line, so a reader of this output is
    never left to assume that a passing Python assert was checked by a proof.
    The banner is labelled for the same reason: it is the line a reader is
    most likely to quote, and on its own ``12/12 PASS`` says nothing about
    what did the passing.

    Args:
        results: The prediction results to display.
    """
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"\n{'=' * 60}")
    print("  Formal Prediction Tests (Python)")
    print(f"  {passed}/{total} PASS")
    print(f"{'=' * 60}\n")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] P{r.id:02d} ({r.chapter} \u00a7{r.section}) {r.description}")
        print(f"         {r.evidence}")
        if r.lean is not None:
            named = ": " + ", ".join(r.lean.declarations) if r.lean.declarations else ""
            print(f"         Lean: {r.lean.status.value}{named}")
        print()
    print(f"{'=' * 60}")
    print(f"  Summary: {passed}/{total} predictions verified by Python asserts")
    tally = lean_coverage_tally(results)
    if tally:
        print(f"  Lean:    {tally}")
    print("  No Lean proof is checked by this run; see")
    print("  book/formal-verification-lean.md#prediction-coverage")
    print(f"{'=' * 60}")


def export_json(results: list[PredictionResult], path: str):
    """Export prediction results to a JSON file.

    The JSON structure matches the format used by the Streamlit
    dashboard for displaying verification status.

    Args:
        results: The prediction results to export.
        path: Output file path.
    """
    data = [
        {
            "id": r.id,
            "chapter": r.chapter,
            "section": r.section,
            "description": r.description,
            "passed": r.passed,
            "evidence": r.evidence,
            "lean_status": r.lean.status.value if r.lean else None,
            "lean_declarations": list(r.lean.declarations) if r.lean else [],
        }
        for r in results
    ]
    with open(path, "w") as f:
        json.dump(
            {
                "predictions": data,
                "passed": sum(1 for r in results if r.passed),
                "total": len(results),
            },
            f,
            indent=2,
        )


def main():
    """Parse CLI arguments and run the verification."""
    parser = argparse.ArgumentParser(
        description="Verify formal predictions from the Nomos book chapters"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Run all predictions")
    group.add_argument("--ch2", action="store_true", help="Run Chapter 2 predictions")
    group.add_argument("--ch3", action="store_true", help="Run Chapter 3 predictions")
    group.add_argument("--ch4", action="store_true", help="Run Chapter 4 predictions")
    group.add_argument("--single", type=int, metavar="N", help="Run single prediction N (1-12)")
    parser.add_argument("--json", type=str, help="Export results to JSON file")
    args = parser.parse_args()

    if not any([args.all, args.ch2, args.ch3, args.ch4, args.single]):
        args.all = True

    results = run_all()

    if args.ch2:
        results = filter_by_chapter(results, "Ch2")
    elif args.ch3:
        results = filter_by_chapter(results, "Ch3")
    elif args.ch4:
        results = filter_by_chapter(results, "Ch4")
    elif args.single:
        results = [r for r in results if r.id == args.single]
        if not results:
            print(f"No prediction found with id={args.single}")
            sys.exit(1)

    print_summary(results)

    if args.json:
        export_json(results, args.json)
        print(f"Exported to {args.json}")


if __name__ == "__main__":
    main()
