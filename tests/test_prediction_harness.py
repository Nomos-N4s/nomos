"""Tests for the formal prediction cross-validation harness (#144)."""

import json
import os

import pytest

from src.nomos.agents import (
    CrossValidationResult,
    CrossValidationRow,
    PredictionConfig,
    get_prediction_registry,
    run_cross_validation,
)
from src.nomos.agents.harness import ArmResult, PairResult, StepLogEntry
from src.nomos.agents.pipeline import ALL_AGENT_SCENARIOS
from src.nomos.agents.prediction_harness import (
    _PREDICTION_REGISTRY,
    _classify_adversarial_outcome,
    _compute_sensitivity,
    _evaluate_behavioral,
    _evaluate_structural,
    _prediction_description,
    _register_all_predictions,
    _run_adversarial_episode,
    _run_prediction_pair,
)
from src.nomos.agents.scenarios import DeadlockMazeLLM, DriftLabLLM, GridWorldLLM, TemptationBankLLM
from src.nomos.experiments.base import ExperimentMetrics
from src.nomos.speaker import SpeakerStateMachine


# ----------------------------------------------------------------------
# Registry integrity
# ----------------------------------------------------------------------


class TestPredictionRegistry:
    def test_all_12_predictions_present(self) -> None:
        _register_all_predictions()
        assert len(_PREDICTION_REGISTRY) == 12

    def test_every_prediction_mapped_to_scenario(self) -> None:
        _register_all_predictions()
        for pred_id, config in _PREDICTION_REGISTRY.items():
            assert config.scenarios, f"Prediction {pred_id} has no scenarios"

    def test_every_prediction_has_adversarial_prompts(self) -> None:
        _register_all_predictions()
        for pred_id, config in _PREDICTION_REGISTRY.items():
            assert config.adversarial_prompts, f"Prediction {pred_id} has no adversarial prompts"

    def test_every_prediction_has_non_empty_hypothesis(self) -> None:
        _register_all_predictions()
        for pred_id, config in _PREDICTION_REGISTRY.items():
            assert config.hypothesis.strip(), f"Prediction {pred_id} has empty hypothesis"

    def test_scenario_classes_are_known(self) -> None:
        _register_all_predictions()
        known = {cls.__name__ for cls in ALL_AGENT_SCENARIOS}
        for pred_id, config in _PREDICTION_REGISTRY.items():
            for scenario_cls in config.scenarios:
                assert scenario_cls.__name__ in known, (
                    f"Prediction {pred_id} references unknown scenario {scenario_cls.__name__}"
                )

    def test_prediction_ids_are_sequential(self) -> None:
        _register_all_predictions()
        assert sorted(_PREDICTION_REGISTRY.keys()) == list(range(1, 13))

    def test_public_registry_matches_internal(self) -> None:
        _register_all_predictions()
        public = get_prediction_registry()
        assert len(public) == len(_PREDICTION_REGISTRY)
        assert set(public.keys()) == set(_PREDICTION_REGISTRY.keys())


# ----------------------------------------------------------------------
# Evaluators
# ----------------------------------------------------------------------


def _step_entry(vetoed: bool = False, violations: int = 0, proposed_action: str = "a", decision_action: str = "a") -> StepLogEntry:
    return StepLogEntry(
        step=0,
        arm="governed",
        observation="obs",
        agent_action_index=0,
        confidence=0.8,
        rationale="r",
        proposed_action=proposed_action,
        decision_action=decision_action,
        vetoed=vetoed,
        is_default=False,
        would_have_been=None,
        reward=0.0,
        violations_delta=violations,
        select_latency=0.0,
    )


def _arm(entries: list[StepLogEntry], total_reward: float = 0.0) -> ArmResult:
    return ArmResult(
        arm="governed",
        log=entries,
        metrics=ExperimentMetrics(total_reward=total_reward, total_steps=len(entries)),
    )


def _pair(governed_entries: list[StepLogEntry], ungoverned_entries: list[StepLogEntry]) -> PairResult:
    return PairResult(
        seed=0,
        governed=_arm(governed_entries),
        ungoverned=_arm(ungoverned_entries),
    )


class TestEvaluators:
    def test_behavioral_passes_when_governed_rate_lte_ungoverned(self) -> None:
        pair = _pair(
            [_step_entry(violations=0), _step_entry(violations=0)],
            [_step_entry(violations=1), _step_entry(violations=1)],
        )
        passed, evidence = _evaluate_behavioral(pair)
        assert passed is True
        assert "governed_rate=0.000" in evidence
        assert "ungoverned_rate=1.000" in evidence

    def test_behavioral_fails_when_governed_rate_exceeds_ungoverned(self) -> None:
        pair = _pair(
            [_step_entry(violations=1), _step_entry(violations=1)],
            [_step_entry(violations=0), _step_entry(violations=0)],
        )
        passed, evidence = _evaluate_behavioral(pair)
        assert passed is False

    def test_structural_passes_when_steps_completed(self) -> None:
        pair = _pair([_step_entry()], [_step_entry()])
        passed, evidence = _evaluate_structural(pair)
        assert passed is True
        assert "1 steps" in evidence

    def test_structural_fails_on_empty_run(self) -> None:
        pair = _pair([], [])
        passed, evidence = _evaluate_structural(pair)
        assert passed is False


# ----------------------------------------------------------------------
# Adversarial classification
# ----------------------------------------------------------------------


class TestAdversarialClassification:
    def test_vetoed_action_is_blocked(self) -> None:
        entry = _step_entry(vetoed=True, decision_action="stand_still")
        assert _classify_adversarial_outcome(entry, "ignore rules") == "blocked"

    def test_default_action_is_blocked(self) -> None:
        entry = _step_entry(vetoed=False, decision_action="stand_still")
        entry.is_default = True
        assert _classify_adversarial_outcome(entry, "ignore rules") == "blocked"

    def test_non_vetoed_non_default_is_succeeded(self) -> None:
        entry = _step_entry(vetoed=False, decision_action="take_loan")
        entry.is_default = False
        assert _classify_adversarial_outcome(entry, "take a loan") == "succeeded"


# ----------------------------------------------------------------------
# Cross-validation runner (StubBackend, single config)
# ----------------------------------------------------------------------


class TestCrossValidationRunner:
    def test_stub_backend_produces_rows_for_all_predictions(self) -> None:
        result = run_cross_validation(
            seeds=1,
            steps=10,
            use_cache=False,
            adversarial=False,
        )
        assert len(result.rows) == 12
        assert all(isinstance(r, CrossValidationRow) for r in result.rows)
        for pred_id in range(1, 13):
            assert any(r.prediction_id == pred_id for r in result.rows), (
                f"Missing rows for prediction {pred_id}"
            )

    def test_single_prediction_subset(self) -> None:
        result = run_cross_validation(
            seeds=1,
            steps=10,
            prediction_ids=[1, 5, 9],
            use_cache=False,
            adversarial=False,
        )
        ids = {r.prediction_id for r in result.rows}
        assert ids == {1, 5, 9}

    def test_multiple_seeds_multiply_rows(self) -> None:
        result = run_cross_validation(
            seeds=2,
            steps=10,
            use_cache=False,
            adversarial=False,
        )
        assert len(result.rows) == 24

    def test_adversarial_catalog_records_outcomes(self) -> None:
        result = run_cross_validation(
            seeds=1,
            steps=10,
            use_cache=False,
            adversarial=True,
        )
        assert len(result.catalog) > 0
        for entry in result.catalog:
            assert entry.outcome in ("blocked", "partial", "succeeded")

    def test_adversarial_disabled_produces_empty_catalog(self) -> None:
        result = run_cross_validation(
            seeds=1,
            steps=10,
            use_cache=False,
            adversarial=False,
        )
        assert result.catalog == []

    def test_rows_include_adversarial_outcome_when_enabled(self) -> None:
        result = run_cross_validation(
            seeds=1,
            steps=10,
            use_cache=False,
            adversarial=True,
        )
        rows_with_outcome = [r for r in result.rows if r.adversarial_outcome is not None]
        assert len(rows_with_outcome) > 0

    def test_sensitivity_report_present(self) -> None:
        result = run_cross_validation(
            seeds=1,
            steps=10,
            use_cache=False,
            adversarial=False,
        )
        assert isinstance(result.sensitivity, dict)
        assert len(result.sensitivity) == 12


# ----------------------------------------------------------------------
# Sensitivity analysis
# ----------------------------------------------------------------------


class TestSensitivityAnalysis:
    def test_model_robust_when_all_pass(self) -> None:
        rows = [
            CrossValidationRow(1, "P1", "GridWorld", "hyp", "m1", 0.0, 0, True, "ok"),
            CrossValidationRow(1, "P1", "GridWorld", "hyp", "m1", 0.7, 0, True, "ok"),
            CrossValidationRow(1, "P1", "GridWorld", "hyp", "m2", 0.0, 0, True, "ok"),
        ]
        report = _compute_sensitivity(rows)
        assert report["1"]["model_robust"] is True
        assert report["1"]["model_fragile"] is False

    def test_model_fragile_when_any_fails(self) -> None:
        rows = [
            CrossValidationRow(1, "P1", "GridWorld", "hyp", "m1", 0.0, 0, True, "ok"),
            CrossValidationRow(1, "P1", "GridWorld", "hyp", "m1", 0.7, 0, False, "fail"),
        ]
        report = _compute_sensitivity(rows)
        assert report["1"]["model_robust"] is False
        assert report["1"]["model_fragile"] is True

    def test_empty_rows_returns_empty_report(self) -> None:
        report = _compute_sensitivity([])
        assert report == {}

    def test_notes_include_model_and_temperature(self) -> None:
        rows = [
            CrossValidationRow(1, "P1", "GridWorld", "hyp", "m1", 0.0, 0, True, "ok"),
            CrossValidationRow(1, "P1", "GridWorld", "hyp", "m1", 0.0, 1, False, "fail"),
        ]
        report = _compute_sensitivity(rows)
        assert "m1@0.0: 50%" in report["1"]["notes"]


# ----------------------------------------------------------------------
# Serialisation
# ----------------------------------------------------------------------


class TestSerialisation:
    def test_to_markdown_contains_confirmation_table(self) -> None:
        result = CrossValidationResult(
            rows=[
                CrossValidationRow(
                    prediction_id=1,
                    prediction_description="Budget cap",
                    scenario="GridWorldLLM",
                    hypothesis="hyp",
                    model="m1",
                    temperature=0.0,
                    seed=0,
                    passed=True,
                    evidence="ok",
                )
            ],
            catalog=[],
            sensitivity={},
        )
        md = result.to_markdown()
        assert "# Formal Prediction Cross-Validation Report" in md
        assert "## Empirical confirmation table" in md
        assert "Budget cap" in md

    def test_to_markdown_contains_catalog_when_present(self) -> None:
        from src.nomos.agents.prediction_harness import AdversarialOutcome

        result = CrossValidationResult(
            rows=[],
            catalog=[
                AdversarialOutcome(
                    prediction_id=1,
                    scenario="GridWorldLLM",
                    prompt="injection",
                    model="m1",
                    temperature=0.0,
                    seed=0,
                    outcome="blocked",
                    agent_action="move_up",
                    decision_action="stand_still",
                    vetoed=True,
                )
            ],
            sensitivity={},
        )
        md = result.to_markdown()
        assert "## Adversarial edge-case catalog" in md
        assert "blocked" in md

    def test_to_json_round_trip(self) -> None:
        result = CrossValidationResult(
            rows=[
                CrossValidationRow(
                    prediction_id=1,
                    prediction_description="P1",
                    scenario="GridWorldLLM",
                    hypothesis="h",
                    model="m1",
                    temperature=0.0,
                    seed=0,
                    passed=True,
                    evidence="e",
                )
            ],
            catalog=[],
            sensitivity={"1": {"model_robust": True, "model_fragile": False, "notes": "x"}},
        )
        data = result.to_json()
        assert data["confirmation_rate"] == 1.0
        assert len(data["rows"]) == 1
        assert data["rows"][0]["prediction_id"] == 1
        assert data["sensitivity"]["1"]["model_robust"] is True
        dumped = json.dumps(data)
        reloaded = json.loads(dumped)
        assert reloaded["rows"][0]["evidence"] == "e"

    def test_confirmation_rate_empty(self) -> None:
        result = CrossValidationResult()
        assert result.confirmation_rate() == 0.0

    def test_confirmation_rate_partial(self) -> None:
        result = CrossValidationResult(
            rows=[
                CrossValidationRow(1, "P1", "S", "h", "m", 0.0, 0, True, "ok"),
                CrossValidationRow(1, "P1", "S", "h", "m", 0.0, 1, False, "fail"),
            ],
            catalog=[],
            sensitivity={},
        )
        assert result.confirmation_rate() == 0.5


# ----------------------------------------------------------------------
# Prediction description helper
# ----------------------------------------------------------------------


class TestPredictionDescription:
    def test_known_descriptions(self) -> None:
        assert _prediction_description(1) == "Budget enforces proposal cap"
        assert _prediction_description(12) == "Deadlock breaker fires after N defaults"

    def test_unknown_prediction_returns_fallback(self) -> None:
        assert "Prediction 99" in _prediction_description(99)
