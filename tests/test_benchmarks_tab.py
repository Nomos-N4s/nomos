from src.governance.dashboard.benchmarks_tab import _generate_benchmark_summary


def _agg(strategy, scenario, mean_reward, mean_violations=0.0):
    return {
        "strategy": strategy,
        "scenario": scenario,
        "mean_reward": mean_reward,
        "mean_violations": mean_violations,
    }


class TestGenerateBenchmarkSummaryEdgeCases:
    def test_none_benchmarks(self):
        assert _generate_benchmark_summary(None) == "No benchmark results available."

    def test_empty_aggregates(self):
        assert _generate_benchmark_summary({"aggregates": []}) == "No benchmark aggregates available."

    def test_missing_aggregates_key(self):
        assert _generate_benchmark_summary({}) == "No benchmark aggregates available."

    def test_missing_required_columns(self):
        benchmarks = {"aggregates": [{"strategy": "governance"}]}
        assert _generate_benchmark_summary(benchmarks) == "Incomplete benchmark results."

    def test_no_governance_rows(self):
        benchmarks = {
            "aggregates": [
                _agg("random", "GridWorld", 10.0),
                _agg("veto_only", "GridWorld", 5.0),
            ]
        }
        result = _generate_benchmark_summary(benchmarks)
        assert result == "Insufficient data to compare governance and baseline strategies."

    def test_no_baseline_rows(self):
        benchmarks = {"aggregates": [_agg("governance", "GridWorld", 10.0)]}
        result = _generate_benchmark_summary(benchmarks)
        assert result == "Insufficient data to compare governance and baseline strategies."

    def test_no_overlapping_scenarios(self):
        benchmarks = {
            "aggregates": [
                _agg("governance", "GridWorld", 10.0),
                _agg("random", "DriftLab", 5.0),
            ]
        }
        result = _generate_benchmark_summary(benchmarks)
        assert result == "Insufficient data to compare governance and baseline strategies."


class TestGenerateBenchmarkSummaryContent:
    def test_single_scenario_summary_content(self):
        benchmarks = {
            "aggregates": [
                _agg("governance", "GridWorld", 3.0, 0.0),
                _agg("random", "GridWorld", -48.0, 11.0),
                _agg("static_masking", "GridWorld", -13.0, 3.0),
            ]
        }
        result = _generate_benchmark_summary(benchmarks)
        assert "GridWorld" in result
        assert "3.00" in result
        # best baseline should be static_masking (-13.0), not random (-48.0)
        assert "static_masking" in result
        assert "random" not in result

    def test_exact_match_strategy_filtering(self):
        # "governance" must match exactly (case-insensitive), not substring-match
        # e.g. a strategy like "veto_only_governance_variant" should NOT be
        # treated as a governance row.
        benchmarks = {
            "aggregates": [
                _agg("governance", "GridWorld", 3.0, 0.0),
                _agg("veto_only_governance_variant", "GridWorld", -5.0, 2.0),
            ]
        }
        result = _generate_benchmark_summary(benchmarks)
        # the odd variant strategy should be treated as a baseline, not filtered out
        assert "veto_only_governance_variant" in result

    def test_case_insensitive_governance_match(self):
        benchmarks = {
            "aggregates": [
                _agg("Governance", "GridWorld", 3.0, 0.0),
                _agg("random", "GridWorld", -48.0, 11.0),
            ]
        }
        result = _generate_benchmark_summary(benchmarks)
        assert "GridWorld" in result

    def test_multiple_scenarios_sorted_order(self):
        benchmarks = {
            "aggregates": [
                _agg("governance", "GridWorld", 3.0),
                _agg("random", "GridWorld", -48.0),
                _agg("governance", "DriftLab", 0.0),
                _agg("random", "DriftLab", -1.0),
            ]
        }
        result = _generate_benchmark_summary(benchmarks)
        # scenarios should appear in sorted order: DriftLab before GridWorld
        assert result.index("DriftLab") < result.index("GridWorld")

    def test_delta_sign_positive(self):
        benchmarks = {
            "aggregates": [
                _agg("governance", "TemptationBank", 1998.0),
                _agg("random", "TemptationBank", 1977.0),
            ]
        }
        result = _generate_benchmark_summary(benchmarks)
        assert "+21.00" in result

    def test_delta_sign_negative(self):
        benchmarks = {
            "aggregates": [
                _agg("governance", "DriftLab", 0.0),
                _agg("monolithic_rl", "DriftLab", 5.0),
            ]
        }
        result = _generate_benchmark_summary(benchmarks)
        assert "-5.00" in result

    def test_partial_scenario_overlap_only_common_included(self):
        benchmarks = {
            "aggregates": [
                _agg("governance", "GridWorld", 3.0),
                _agg("random", "GridWorld", -48.0),
                _agg("governance", "OnlyGovScenario", 1.0),
                _agg("random", "OnlyBaselineScenario", 1.0),
            ]
        }
        result = _generate_benchmark_summary(benchmarks)
        assert "GridWorld" in result
        assert "OnlyGovScenario" not in result
        assert "OnlyBaselineScenario" not in result


class TestGenerateBenchmarkSummaryErrorHandling:
    def test_malformed_aggregates_does_not_raise(self):
        benchmarks = {"aggregates": "not-a-list-of-dicts"}
        result = _generate_benchmark_summary(benchmarks)
        assert result == "Unable to generate benchmark summary."