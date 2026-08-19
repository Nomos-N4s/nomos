import io
import json
import os
import sys
import tempfile

from src.nomos.prove.predictions import LEAN_COVERAGE, LeanStatus, PredictionResult
from src.nomos.prove.runner import (
    export_json,
    filter_by_chapter,
    lean_coverage_tally,
    main,
    print_summary,
    run_all,
)


class TestRunAll:
    def test_returns_list_of_prediction_results(self):
        results = run_all()
        assert len(results) == 12
        assert all(isinstance(r, PredictionResult) for r in results)

    def test_all_pass(self):
        results = run_all()
        failed = [r for r in results if not r.passed]
        assert len(failed) == 0, f"Failed: {[(r.id, r.evidence) for r in failed]}"


class TestFilterByChapter:
    def test_ch2_returns_only_ch2(self):
        results = run_all()
        ch2 = filter_by_chapter(results, "Ch2")
        assert all(r.chapter == "Ch2" for r in ch2)

    def test_invalid_chapter_returns_empty(self):
        results = run_all()
        empty = filter_by_chapter(results, "Ch99")
        assert empty == []

    def test_all_chapters_covered(self):
        results = run_all()
        for chapter in ["Ch2", "Ch3", "Ch4"]:
            filtered = filter_by_chapter(results, chapter)
            assert len(filtered) > 0, f"No predictions for {chapter}"


class TestPrintSummary:
    def test_output_contains_pass_summary(self):
        results = run_all()
        captured = io.StringIO()
        sys.stdout = captured
        try:
            print_summary(results)
        finally:
            sys.stdout = sys.__stdout__
        output = captured.getvalue()
        assert "12/12" in output
        assert "Summary:" in output

    def test_output_contains_all_predictions(self):
        results = run_all()
        captured = io.StringIO()
        sys.stdout = captured
        try:
            print_summary(results)
        finally:
            sys.stdout = sys.__stdout__
        output = captured.getvalue()
        for i in range(1, 13):
            assert f"P{i:02d}" in output, f"Prediction {i} not found in output"


class TestExportJson:
    def test_creates_json_file_with_all_fields(self):
        results = run_all()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "results.json")
            export_json(results, path)
            assert os.path.exists(path)
            with open(path) as f:
                data = json.load(f)
            assert "predictions" in data
            assert "passed" in data
            assert "total" in data
            assert data["total"] == 12
            assert len(data["predictions"]) == 12
            assert all("id" in p for p in data["predictions"])
            assert all("passed" in p for p in data["predictions"])

    def test_empty_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "empty.json")
            export_json([], path)
            with open(path) as f:
                data = json.load(f)
            assert data["passed"] == 0
            assert data["total"] == 0


class TestMain:
    def test_main_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = os.path.join(tmp, "out.json")
            old_argv = sys.argv
            try:
                sys.argv = ["runner", "--all", "--json", json_path]
                main()
            except SystemExit:
                pass
            finally:
                sys.argv = old_argv
            if os.path.exists(json_path):
                with open(json_path) as f:
                    data = json.load(f)
                assert data["total"] == 12

    def test_main_ch2_only(self):
        captured = io.StringIO()
        sys.stdout = captured
        old_argv = sys.argv
        try:
            sys.argv = ["runner", "--ch2"]
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv
            sys.stdout = sys.__stdout__

    def test_main_single_prediction(self):
        captured = io.StringIO()
        sys.stdout = captured
        old_argv = sys.argv
        try:
            sys.argv = ["runner", "--single", "5"]
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv
            sys.stdout = sys.__stdout__
        output = captured.getvalue()
        assert "1/1" in output or "P05" in output


class TestLeanCoverageReporting:
    """The runner must not let a reader take a passing assert for a proof."""

    def _summary(self):
        results = run_all()
        captured = io.StringIO()
        sys.stdout = captured
        try:
            print_summary(results)
        finally:
            sys.stdout = sys.__stdout__
        return captured.getvalue()

    def test_every_prediction_line_carries_its_lean_status(self):
        output = self._summary()
        for pid, coverage in LEAN_COVERAGE.items():
            assert f"Lean: {coverage.status.value}" in output, (
                f"P{pid:02d}'s status is missing from the summary"
            )

    def test_named_theorems_reach_the_summary(self):
        output = self._summary()
        for coverage in LEAN_COVERAGE.values():
            for name in coverage.declarations:
                assert name in output

    def test_summary_says_the_asserts_are_python(self):
        output = self._summary()
        assert "verified by Python asserts" in output
        assert "No Lean proof is checked by this run" in output

    def test_tally_counts_the_map(self):
        results = run_all()
        tally = lean_coverage_tally(results)
        for status in LeanStatus:
            expected = sum(1 for c in LEAN_COVERAGE.values() if c.status is status)
            assert f"{expected} {status.value}" in tally
        assert tally in self._summary()

    def test_tally_of_nothing_is_empty(self):
        assert lean_coverage_tally([]) == ""

    def test_export_carries_the_coverage(self):
        results = run_all()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "results.json")
            export_json(results, path)
            with open(path) as f:
                data = json.load(f)
        for entry in data["predictions"]:
            coverage = LEAN_COVERAGE[entry["id"]]
            assert entry["lean_status"] == coverage.status.value
            assert entry["lean_declarations"] == list(coverage.declarations)
