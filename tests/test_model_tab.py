from types import SimpleNamespace

import pytest

from src.governance.dashboard import model_tab
from src.governance.dashboard.model_tab import _generate_model_summary
from src.governance.identity.params import DEFAULT_PARAMETER_ENVELOPE


class _StubBackend:
    """Minimal backend stub exposing only what _generate_model_summary needs."""

    def __init__(self, entities=None, raise_error=False):
        self._entities = entities if entities is not None else []
        self._raise_error = raise_error

    def get_entities_by_type(self, entity_type):
        if self._raise_error:
            raise RuntimeError("backend unavailable")
        return self._entities


def _fake_result(passed):
    return SimpleNamespace(passed=passed, id=1, chapter="Ch1", section="1.0", description="stub")


@pytest.fixture
def patch_run_all_safe(monkeypatch):
    def _patch(results):
        monkeypatch.setattr(model_tab, "run_all_safe", lambda: results)

    return _patch


class TestGenerateModelSummaryContent:
    def test_basic_summary_content(self, patch_run_all_safe):
        patch_run_all_safe([_fake_result(True) for _ in range(12)])
        backend = _StubBackend(entities=[{"type": "action", "name": "a"}] * 5)

        result = _generate_model_summary(backend, identity_vec=[0.1, 0.2, 0.3])

        expected_param_count = len(DEFAULT_PARAMETER_ENVELOPE.snapshot())
        assert "5 ontology entities" in result
        assert "1 core commitments" in result
        assert f"{expected_param_count} parameters" in result
        assert "identity vector is available" in result
        assert "12/12 predictions" in result

    def test_identity_vector_not_available_when_none(self, patch_run_all_safe):
        patch_run_all_safe([_fake_result(True) for _ in range(12)])
        backend = _StubBackend(entities=[])

        result = _generate_model_summary(backend, identity_vec=None)

        assert "identity vector is not available" in result

    def test_identity_vector_not_available_when_empty_list(self, patch_run_all_safe):
        patch_run_all_safe([_fake_result(True) for _ in range(12)])
        backend = _StubBackend(entities=[])

        result = _generate_model_summary(backend, identity_vec=[])

        assert "identity vector is not available" in result

    def test_partial_predictions_passed(self, patch_run_all_safe):
        patch_run_all_safe(
            [_fake_result(True) for _ in range(9)] + [_fake_result(False) for _ in range(3)]
        )
        backend = _StubBackend(entities=[])

        result = _generate_model_summary(backend, identity_vec=[0.5])

        assert "9/12 predictions" in result

    def test_zero_entities(self, patch_run_all_safe):
        patch_run_all_safe([_fake_result(True) for _ in range(12)])
        backend = _StubBackend(entities=[])

        result = _generate_model_summary(backend, identity_vec=[0.5])

        assert "0 ontology entities" in result


class TestGenerateModelSummaryErrorHandling:
    def test_backend_error_does_not_raise(self, patch_run_all_safe):
        patch_run_all_safe([_fake_result(True) for _ in range(12)])
        backend = _StubBackend(raise_error=True)

        result = _generate_model_summary(backend, identity_vec=[0.5])

        assert result == "Unable to generate model summary."

    def test_prediction_runner_error_does_not_raise(self, monkeypatch):
        monkeypatch.setattr(
            model_tab,
            "run_all_safe",
            lambda: (_ for _ in ()).throw(RuntimeError("prove failed")),
        )
        backend = _StubBackend(entities=[])

        result = _generate_model_summary(backend, identity_vec=[0.5])

        assert result == "Unable to generate model summary."
