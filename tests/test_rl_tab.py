import pandas as pd

from src.governance.dashboard.rl_tab import _generate_rl_summary


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
