"""Tests for agent validation metrics and reports (#141)."""

import csv
import json

import pytest

from src.nomos.agents import (
    GovernorComparisonHarness,
    JudgeAssessment,
    StubBackend,
    compute_pair_metrics,
    judge_alignment,
    latency_percentiles,
    oracle_would_violate,
    run_agent_analysis,
    sample_judge_steps,
    summarize_pairs,
)
from src.nomos.agents.harness import ArmResult, PairResult, StepLogEntry
from src.nomos.agents.scenarios import TemptationBankLLM
from src.nomos.committee.members import ExampleRewardMember, ExampleSafetyMember
from src.nomos.experiments.base import ExperimentMetrics
from src.nomos.speaker import SpeakerStateMachine

# ----------------------------------------------------------------------
# Synthetic paired trajectories
# ----------------------------------------------------------------------


def _entry(step: int, *, vetoed: bool = False, violations: int = 0, latency: float = 0.0) -> StepLogEntry:
    return StepLogEntry(
        step=step,
        arm="governed",
        observation="obs",
        agent_action_index=0,
        confidence=0.8,
        rationale="r",
        proposed_action="a",
        decision_action="a",
        vetoed=vetoed,
        is_default=False,
        would_have_been=None,
        reward=0.0,
        violations_delta=violations,
        select_latency=latency,
    )


def _arm(arm: str, entries: list[StepLogEntry], total_reward: float = 0.0) -> ArmResult:
    return ArmResult(
        arm=arm,
        log=entries,
        metrics=ExperimentMetrics(total_reward=total_reward, total_steps=len(entries)),
    )


def _pair(
    seed: int,
    governed: list[StepLogEntry],
    ungoverned: list[StepLogEntry],
    governed_reward: float,
    ungoverned_reward: float,
) -> PairResult:
    return PairResult(
        seed=seed,
        governed=_arm("governed", governed, governed_reward),
        ungoverned=_arm("ungoverned", ungoverned, ungoverned_reward),
    )


def _ground_truth_pairs() -> list[PairResult]:
    pair_1 = _pair(
        seed=0,
        governed=[
            _entry(0),
            _entry(1, vetoed=True),
            _entry(2),
            _entry(3, vetoed=True),
            _entry(4, vetoed=True),
        ],
        ungoverned=[_entry(0), _entry(1, violations=1), _entry(2), _entry(3, violations=1), _entry(4)],
        governed_reward=40.0,
        ungoverned_reward=50.0,
    )
    pair_2 = _pair(
        seed=1,
        governed=[_entry(0, vetoed=True), _entry(1), _entry(2, vetoed=True), _entry(3), _entry(4)],
        ungoverned=[
            _entry(0, violations=1),
            _entry(1),
            _entry(2, violations=1),
            _entry(3),
            _entry(4, violations=1),
        ],
        governed_reward=30.0,
        ungoverned_reward=25.0,
    )
    return [pair_1, pair_2]


# ----------------------------------------------------------------------
# Counterfactual oracle and per-pair metrics
# ----------------------------------------------------------------------


class TestOracle:
    def test_oracle_from_ungoverned_violations(self) -> None:
        pair = _ground_truth_pairs()[0]
        assert oracle_would_violate(pair) == [False, True, False, True, False]

    def test_mismatched_step_counts_rejected(self) -> None:
        pair = _pair(0, [_entry(0), _entry(1)], [_entry(0)], 0.0, 0.0)
        with pytest.raises(ValueError, match="step count"):
            oracle_would_violate(pair)


class TestPairMetrics:
    def test_known_ground_truth(self) -> None:
        metrics = compute_pair_metrics(_ground_truth_pairs()[0])
        assert metrics.num_steps == 5
        assert metrics.ungoverned_violation_rate == pytest.approx(0.4)
        assert metrics.governed_violation_rate == 0.0
        assert metrics.reward_preservation_ratio == pytest.approx(0.8)
        assert metrics.veto_precision == pytest.approx(2 / 3)
        assert metrics.veto_recall == 1.0
        assert metrics.vetoes == 3
        assert metrics.oracle_positives == 2

    def test_missed_violations_penalize_recall(self) -> None:
        metrics = compute_pair_metrics(_ground_truth_pairs()[1])
        assert metrics.ungoverned_violation_rate == pytest.approx(0.6)
        assert metrics.governed_violation_rate == 0.0
        assert metrics.reward_preservation_ratio == pytest.approx(1.2)
        assert metrics.veto_precision == 1.0
        assert metrics.veto_recall == pytest.approx(2 / 3)

    def test_no_vetoes_yield_none_precision(self) -> None:
        pair = _pair(0, [_entry(0), _entry(1)], [_entry(0), _entry(1, violations=1)], 4.0, 2.0)
        metrics = compute_pair_metrics(pair)
        assert metrics.veto_precision is None
        assert metrics.veto_recall == 0.0  # the one violation was missed

    def test_no_oracle_positives_yield_none_recall(self) -> None:
        pair = _pair(0, [_entry(0, vetoed=True), _entry(1)], [_entry(0), _entry(1)], 4.0, 4.0)
        metrics = compute_pair_metrics(pair)
        assert metrics.veto_precision == 0.0  # veto on a clean step
        assert metrics.veto_recall is None

    def test_zero_ungoverned_reward_yields_none_preservation(self) -> None:
        pair = _pair(0, [_entry(0)], [_entry(0)], 1.0, 0.0)
        assert compute_pair_metrics(pair).reward_preservation_ratio is None


# ----------------------------------------------------------------------
# Latency
# ----------------------------------------------------------------------


class TestLatency:
    def test_p50_p95_nearest_rank(self) -> None:
        stats = latency_percentiles([0.01, 0.02, 0.03, 0.04, 0.05])
        assert stats["p50"] == pytest.approx(0.03)
        assert stats["p95"] == pytest.approx(0.05)

    def test_empty_latencies_zero(self) -> None:
        assert latency_percentiles([]) == {"p50": 0.0, "p95": 0.0}

    def test_harness_records_select_latency(self) -> None:
        harness = GovernorComparisonHarness(
            lambda speaker: TemptationBankLLM(speaker),
            StubBackend(script=[1, 1, 1]),
            TemptationBankLLM.action_space(),
            SpeakerStateMachine(
                members={"reward": ExampleRewardMember(), "safety": ExampleSafetyMember()},
                default_action="work",
            ),
            observation_fn=lambda s: s.render_observation(),
        )
        pair = harness.run_pair(seed=0, steps=3)
        for arm in (pair.governed, pair.ungoverned):
            assert len(arm.log) == 3
            for entry in arm.log:
                assert entry.select_latency >= 0.0


# ----------------------------------------------------------------------
# Aggregates across seeds
# ----------------------------------------------------------------------


class TestSummary:
    def test_aggregates_known_two_pairs(self) -> None:
        pairs = _ground_truth_pairs()
        latencies = [0.01, 0.02, 0.03, 0.04, 0.05]
        for pair in pairs:
            for entry, latency in zip(pair.governed.log, latencies):
                entry.select_latency = latency

        summary = summarize_pairs(pairs)
        assert summary.num_pairs == 2
        assert summary.num_steps == 10
        assert summary.ungoverned_violation_rate == pytest.approx(0.5)
        assert summary.governed_violation_rate == 0.0
        assert summary.governed_rate_never_worse == 1.0
        assert summary.reward_preservation_ratio == pytest.approx(1.0)
        assert summary.reward_preservation_ci[0] == pytest.approx(0.8, abs=1e-3)
        assert summary.reward_preservation_ci[1] == pytest.approx(1.2, abs=1e-3)
        assert summary.reward_cohens_d == pytest.approx(-0.1857, abs=1e-3)
        assert summary.veto_precision == pytest.approx(5 / 6)
        assert summary.veto_recall == pytest.approx(5 / 6)
        assert summary.latency_p50["governed"] == pytest.approx(0.03)
        assert summary.latency_p95["governed"] == pytest.approx(0.05)
        assert summary.latency_p50["ungoverned"] == 0.0

    def test_empty_pairs_all_zero(self) -> None:
        summary = summarize_pairs([])
        assert summary.num_pairs == 0
        assert summary.ungoverned_violation_rate == 0.0
        assert summary.veto_precision == 0.0
        assert summary.reward_preservation_ci == (0.0, 0.0)


# ----------------------------------------------------------------------
# LLM-as-judge alignment
# ----------------------------------------------------------------------


class TestJudgeAlignment:
    def test_assessment_validation(self) -> None:
        with pytest.raises(ValueError, match="score"):
            JudgeAssessment("judge:a", 0, 0, 0, True, True)
        with pytest.raises(ValueError, match="score"):
            JudgeAssessment("judge:a", 0, 0, 6, True, True)
        with pytest.raises(ValueError, match="judge_id"):
            JudgeAssessment("", 0, 0, 3, True, True)

    def test_alignment_known_verdicts(self) -> None:
        assessments = [
            JudgeAssessment("judge:a", 0, 1, 4, True, True),
            JudgeAssessment("judge:a", 0, 2, 3, False, True),
            JudgeAssessment("judge:b", 0, 1, 5, True, True),
            JudgeAssessment("judge:b", 0, 2, 2, False, False),
        ]
        metrics = judge_alignment(assessments)
        assert metrics.num_samples == 4
        assert metrics.mean_score == pytest.approx(3.5)
        assert metrics.oracle_agreement == pytest.approx(0.75)
        assert metrics.inter_rater_agreement == pytest.approx(0.5)
        assert metrics.mean_abs_score_diff == pytest.approx(1.0)

    def test_sampler_deterministic_and_bounded(self) -> None:
        pairs = _ground_truth_pairs()
        first = sample_judge_steps(pairs, samples_per_pair=3)
        assert len(first) == 6
        assert first == sample_judge_steps(pairs, samples_per_pair=3)
        for pair, step in first:
            assert 0 <= step < len(pair.ungoverned.log)

    def test_sampler_exhaustive_on_short_pairs(self) -> None:
        pairs = _ground_truth_pairs()
        samples = sample_judge_steps(pairs, samples_per_pair=10)
        assert len(samples) == 10


# ----------------------------------------------------------------------
# Report generation
# ----------------------------------------------------------------------


def _assessments() -> list[JudgeAssessment]:
    return [
        JudgeAssessment("judge:a", 0, 1, 4, True, True),
        JudgeAssessment("judge:b", 0, 1, 5, True, True),
    ]


class TestReport:
    def test_run_agent_analysis_writes_artifacts(self, tmp_path) -> None:
        pairs = _ground_truth_pairs()
        result = run_agent_analysis(pairs, _assessments(), output_dir=str(tmp_path))

        assert result["summary"].num_pairs == 2
        with open(tmp_path / "agent_benchmark_summary.csv", newline="") as f:
            rows = list(csv.reader(f))
        assert rows[0] == [
            "seed",
            "num_steps",
            "ungoverned_violation_rate",
            "governed_violation_rate",
            "reward_preservation_ratio",
            "veto_precision",
            "veto_recall",
        ]
        assert len(rows) == 3
        assert rows[1][0] == "0"
        assert rows[1][4] == "0.8"
        assert rows[2][0] == "1"

        with open(tmp_path / "agent_benchmark_results.json") as f:
            data = json.load(f)
        assert data["num_pairs"] == 2
        assert data["num_steps"] == 10
        assert data["summary"]["ungoverned_violation_rate"] == 0.5
        assert len(data["pairs"]) == 2
        assert data["pairs"][0]["veto_precision"] == pytest.approx(2 / 3)
        assert data["judge"]["mean_score"] == 4.5

        with open(tmp_path / "agent_report.md") as f:
            md = f.read()
        assert "# Agent Validation Report" in md
        assert "## Reward preservation" in md
        assert "## LLM-as-judge alignment" in md

    def test_report_without_judge_assessments(self, tmp_path) -> None:
        result = run_agent_analysis(_ground_truth_pairs(), output_dir=str(tmp_path))
        assert result["judge"] is None
        with open(tmp_path / "agent_benchmark_results.json") as f:
            data = json.load(f)
        assert data["judge"] is None
        with open(tmp_path / "agent_report.md") as f:
            md = f.read()
        assert "## LLM-as-judge alignment" not in md
