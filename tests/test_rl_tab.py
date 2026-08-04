import pandas as pd
import pytest

from src.nomos.dashboard.rl_tab import (
    _format_last_updated,
    _generate_rl_summary,
    _has_new_data,
    _latest_data_mtime,
)


def _row(label, mean_reward, std_reward=1.0):
    return {"label": label, "mean_reward": mean_reward, "std_reward": std_reward}


class TestGenerateRlSummaryEdgeCases:
    def test_none_summary(self):
        assert _generate_rl_summary(None) == "No RL training results available."

    def test_empty_dataframe(self):
        assert _generate_rl_summary(pd.DataFrame()) == "No RL training results available."

    def test_missing_required_columns(self):
        df = pd.DataFrame([{"label": "governed"}])
        assert _generate_rl_summary(df) == "Incomplete RL training results."

    def test_no_governed_rows(self):
        df = pd.DataFrame([_row("ungoverned", 10.0)])
        result = _generate_rl_summary(df)
        assert result == "Insufficient data to compare governed and ungoverned agents."

    def test_no_ungoverned_rows(self):
        df = pd.DataFrame([_row("governed", 10.0)])
        result = _generate_rl_summary(df)
        assert result == "Insufficient data to compare governed and ungoverned agents."

    def test_empty_after_filtering(self):
        df = pd.DataFrame([_row("random", 10.0), _row("baseline", 5.0)])
        result = _generate_rl_summary(df)
        assert result == "Insufficient data to compare governed and ungoverned agents."


class TestGenerateRlSummaryContent:
    def test_basic_summary_content(self):
        df = pd.DataFrame(
            [
                _row("governed", 50.0, 5.0),
                _row("ungoverned", 30.0, 8.0),
            ]
        )
        result = _generate_rl_summary(df)
        assert "50.00" in result
        assert "5.00" in result
        assert "30.00" in result
        assert "8.00" in result
        assert "Governed agents achieved" in result

    def test_case_insensitive_labels(self):
        df = pd.DataFrame(
            [
                _row("Governed", 50.0, 5.0),
                _row("Ungoverned", 30.0, 8.0),
            ]
        )
        result = _generate_rl_summary(df)
        assert "Governed agents achieved" in result
        assert "50.00" in result

    def test_averages_multiple_seeds(self):
        df = pd.DataFrame(
            [
                _row("governed", 40.0, 4.0),
                _row("governed", 60.0, 6.0),
                _row("ungoverned", 20.0, 2.0),
                _row("ungoverned", 40.0, 4.0),
            ]
        )
        result = _generate_rl_summary(df)
        # means: governed reward=50.00 std=5.00, ungoverned reward=30.00 std=3.00
        assert "50.00" in result
        assert "5.00" in result
        assert "30.00" in result
        assert "3.00" in result

    def test_extra_labels_ignored(self):
        df = pd.DataFrame(
            [
                _row("governed", 50.0, 5.0),
                _row("ungoverned", 30.0, 8.0),
                _row("random", 10.0, 2.0),
            ]
        )
        result = _generate_rl_summary(df)
        assert "50.00" in result
        assert "30.00" in result


class TestGenerateRlSummaryErrorHandling:
    def test_malformed_data_does_not_raise(self):
        df = pd.DataFrame(
            [
                {"label": "governed", "mean_reward": "not-a-number", "std_reward": 1.0},
                {"label": "ungoverned", "mean_reward": 10.0, "std_reward": 1.0},
            ]
        )
        result = _generate_rl_summary(df)
        assert result == "Unable to generate RL training summary."


class TestLatestDataMtime:
    def test_missing_directory_returns_none(self, tmp_path):
        missing = tmp_path / "does_not_exist"
        assert _latest_data_mtime(str(missing)) is None

    def test_empty_directory_returns_none(self, tmp_path):
        assert _latest_data_mtime(str(tmp_path)) is None

    def test_ignores_non_csv_files(self, tmp_path):
        (tmp_path / "notes.txt").write_text("hello")
        assert _latest_data_mtime(str(tmp_path)) is None

    def test_finds_csv_in_nested_subdirectory(self, tmp_path):
        nested = tmp_path / "minigrid"
        nested.mkdir()
        (nested / "comparison_summary.csv").write_text("a,b\n1,2\n")
        assert _latest_data_mtime(str(tmp_path)) is not None

    def test_returns_newest_mtime_across_multiple_files(self, tmp_path):
        import os
        import time

        old_file = tmp_path / "old.csv"
        old_file.write_text("a\n1\n")
        old_mtime = time.time() - 1000
        os.utime(old_file, (old_mtime, old_mtime))

        new_file = tmp_path / "new.csv"
        new_file.write_text("a\n2\n")

        latest = _latest_data_mtime(str(tmp_path))
        assert latest == pytest.approx(os.path.getmtime(new_file), abs=0.01)


class TestHasNewData:
    def test_first_check_is_never_new(self):
        # previous_mtime is None on the very first render - shouldn't flag "new".
        assert _has_new_data(current_mtime=123.0, previous_mtime=None) is False

    def test_no_data_at_all_is_not_new(self):
        assert _has_new_data(current_mtime=None, previous_mtime=None) is False

    def test_unchanged_mtime_is_not_new(self):
        assert _has_new_data(current_mtime=100.0, previous_mtime=100.0) is False

    def test_newer_mtime_is_new(self):
        assert _has_new_data(current_mtime=200.0, previous_mtime=100.0) is True

    def test_data_disappearing_is_not_new(self):
        assert _has_new_data(current_mtime=None, previous_mtime=100.0) is False


class TestFormatLastUpdated:
    def test_none_mtime(self):
        assert _format_last_updated(None) == "No RL results found yet."

    def test_known_mtime_is_formatted(self):
        result = _format_last_updated(0.0)
        assert result.startswith("Last updated: ")
        assert len(result) > len("Last updated: ")
