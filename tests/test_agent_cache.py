"""Tests for agent run reproducibility: cache, determinism, schema, smoke pipeline."""

import json
import re

import pytest

from src.governance.agents import (
    AgentAction,
    AgentBackend,
    CachedBackend,
    ResponseCache,
    StubBackend,
    run_agent_benchmark,
)
from src.governance.agents.cache import hash_prompt, write_cache_manifest
from src.governance.agents.prompts import (
    build_context,
    build_system_prompt,
    render_deadlock_maze,
    render_drift_lab,
    render_grid_world,
    render_temptation_bank,
)
from src.governance.agents.schema import validate_agent_artifacts, validate_cache_manifest
from src.governance.experiments.grid_world import TILE_APPLE, TILE_EMPTY, TILE_WALL

# ----------------------------------------------------------------------
# ResponseCache
# ----------------------------------------------------------------------


class TestResponseCache:
    def test_miss_returns_none(self, tmp_path) -> None:
        cache = ResponseCache(str(tmp_path))
        assert cache.lookup("stub", "abc", None) is None
        assert cache.stats() == {"hits": 0, "misses": 1}

    def test_store_and_lookup_roundtrip(self, tmp_path) -> None:
        cache = ResponseCache(str(tmp_path))
        action = AgentAction(action_index=2, confidence=0.7, rationale="roundtrip")
        cache.store("stub", "abc", None, action)
        assert cache.lookup("stub", "abc", None) == action
        assert cache.stats() == {"hits": 1, "misses": 0}

    def test_file_name_is_content_address(self, tmp_path) -> None:
        cache = ResponseCache(str(tmp_path))
        cache.store("stub", "abc", 0.0, AgentAction(0, 1.0, "x"))
        key = ResponseCache.key_for("stub", "abc", 0.0)
        assert len(key) == 64
        assert list(tmp_path.iterdir()) == [tmp_path / f"{key}.json"]

    def test_key_distinguishes_model_prompt_temperature(self) -> None:
        base = ResponseCache.key_for("stub", "abc", None)
        assert ResponseCache.key_for("other", "abc", None) != base
        assert ResponseCache.key_for("stub", "def", None) != base
        assert ResponseCache.key_for("stub", "abc", 0.5) != base

    def test_key_and_hash_are_deterministic(self) -> None:
        assert ResponseCache.key_for("stub", "abc", None) == ResponseCache.key_for(
            "stub", "abc", None
        )
        assert hash_prompt("sys", "obs") == hash_prompt("sys", "obs")
        assert hash_prompt("sys", "obs") != hash_prompt("sys", "obs2")

    def test_store_content_includes_key_and_response(self, tmp_path) -> None:
        cache = ResponseCache(str(tmp_path))
        cache.store("stub", "abc", 0.0, AgentAction(1, 0.9, "why"))
        path = tmp_path / f"{ResponseCache.key_for('stub', 'abc', 0.0)}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == 1
        assert data["key"] == {"model": "stub", "prompt_hash": "abc", "temperature": 0.0}
        assert data["response"] == {"action_index": 1, "confidence": 0.9, "rationale": "why"}

    def test_malformed_entry_treated_as_miss(self, tmp_path) -> None:
        cache = ResponseCache(str(tmp_path))
        key = ResponseCache.key_for("stub", "abc", None)
        (tmp_path / f"{key}.json").write_text("{not json", encoding="utf-8")
        assert cache.lookup("stub", "abc", None) is None


# ----------------------------------------------------------------------
# CachedBackend
# ----------------------------------------------------------------------


class _CountingBackend(AgentBackend):
    """Fake API: records every call, replies deterministically."""

    backend_id = "counting"

    def __init__(self, calls: list[str]):
        self.calls = calls

    def reset(self) -> None:
        pass

    def select_action(self, context) -> AgentAction:
        self.calls.append(context["observation"])
        return AgentAction(action_index=1, confidence=1.0, rationale="counting")


class TestCachedBackend:
    def test_hit_replays_identical_action_without_backend_call(self, tmp_path) -> None:
        calls: list[str] = []
        backend = CachedBackend(_CountingBackend(calls), cache_dir=str(tmp_path))
        context = {"observation": "state A", "action_descriptions": ["a", "b"]}
        first = backend.select_action(context)
        second = backend.select_action(context)
        assert first == second
        assert len(calls) == 1  # second call served from cache
        assert backend.cache_stats() == {"hits": 1, "misses": 1}

    def test_prompt_change_is_a_miss(self, tmp_path) -> None:
        calls: list[str] = []
        backend = CachedBackend(_CountingBackend(calls), cache_dir=str(tmp_path))
        backend.select_action({"observation": "state A", "action_descriptions": []})
        backend.select_action({"observation": "state B", "action_descriptions": []})
        assert len(calls) == 2

    def test_model_change_is_a_miss(self, tmp_path) -> None:
        calls: list[str] = []
        inner = _CountingBackend(calls)
        backend = CachedBackend(inner, cache_dir=str(tmp_path))
        backend.select_action({"observation": "state A", "action_descriptions": []})
        other = CachedBackend(inner, cache_dir=str(tmp_path), model="other-model")
        other.select_action({"observation": "state A", "action_descriptions": []})
        assert len(calls) == 2

    def test_system_prompt_participates_in_hash(self, tmp_path) -> None:
        calls: list[str] = []
        backend = CachedBackend(
            _CountingBackend(calls), cache_dir=str(tmp_path), system_prompt="briefing A"
        )
        backend.select_action({"observation": "state A", "action_descriptions": []})
        other = CachedBackend(
            _CountingBackend(calls), cache_dir=str(tmp_path), system_prompt="briefing B"
        )
        other.select_action({"observation": "state A", "action_descriptions": []})
        assert len(calls) == 2

    def test_reset_forwards_to_inner(self, tmp_path) -> None:
        inner = StubBackend(script=[0, 1])
        backend = CachedBackend(inner, cache_dir=str(tmp_path))
        backend.select_action({"observation": "s", "action_descriptions": ["a", "b"]})
        backend.reset()
        backend.select_action({"observation": "t", "action_descriptions": ["a", "b"]})
        assert backend._backend._calls == 1  # noqa: SLF001


# ----------------------------------------------------------------------
# Manifest
# ----------------------------------------------------------------------


class TestManifest:
    def test_manifest_hashes_match_cache_files(self, tmp_path) -> None:
        cache_dir = tmp_path / "cache"
        cache = ResponseCache(str(cache_dir))
        cache.store("stub", "abc", None, AgentAction(0, 1.0, "x"))
        cache.store("stub", "def", 0.0, AgentAction(1, 0.5, "y"))
        manifest_path = tmp_path / "cache_manifest.json"
        manifest = write_cache_manifest(str(cache_dir), str(manifest_path))
        assert manifest["total_entries"] == 2
        assert validate_cache_manifest(str(manifest_path), str(cache_dir)) == []

    def test_manifest_detects_digest_mismatch(self, tmp_path) -> None:
        cache_dir = tmp_path / "cache"
        cache = ResponseCache(str(cache_dir))
        cache.store("stub", "abc", None, AgentAction(0, 1.0, "x"))
        manifest_path = tmp_path / "cache_manifest.json"
        write_cache_manifest(str(cache_dir), str(manifest_path))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        name = next(iter(manifest["files"]))
        manifest["files"][name] = "0" * 64
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        problems = validate_cache_manifest(str(manifest_path), str(cache_dir))
        assert any("digest mismatch" in p for p in problems)


# ----------------------------------------------------------------------
# Deterministic prompt rendering
# ----------------------------------------------------------------------


class TestPromptDeterminism:
    def test_renderers_identical_across_calls(self) -> None:
        grid = [[TILE_EMPTY] * 3 for _ in range(3)]
        grid[1][1] = TILE_APPLE
        grid[1][2] = TILE_WALL
        renderers = [
            lambda: render_grid_world(grid, (1, 0), {(1, 0), (0, 0)}, []),
            lambda: render_temptation_bank(10.0, [7, 2], True),
            lambda: render_drift_lab(0.01, 4.9),
            lambda: render_deadlock_maze("DEADLOCK", 0.9, 3),
        ]
        for render in renderers:
            assert render() == render()
        assert build_system_prompt("GridWorld", ["a", "b"]) == build_system_prompt(
            "GridWorld", ["a", "b"]
        )
        assert build_context("s", ["a", "b"], seed=1, step=2, arm="governed") == build_context(
            "s", ["a", "b"], seed=1, step=2, arm="governed"
        )

    def test_no_timestamps_in_prompts(self) -> None:
        texts = [
            build_system_prompt("GridWorld", ["rule"]),
            render_grid_world([[TILE_EMPTY]], (0, 0), {(0, 0)}, []),
            render_temptation_bank(10.0, [], False),
            render_drift_lab(0.0, 1.0),
            render_deadlock_maze("NORMAL", 0.5, 0),
        ]
        timestamp = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2}(:\d{2})?")
        for text in texts:
            assert timestamp.search(text) is None, text


# ----------------------------------------------------------------------
# Schema contract
# ----------------------------------------------------------------------


class TestSchemaContract:
    def test_valid_artifacts_pass(self, tmp_path) -> None:
        output_dir, cache_dir = _run_smoke(tmp_path, "artifacts")
        assert validate_agent_artifacts(output_dir, cache_dir) == []

    def test_missing_report_fails(self, tmp_path) -> None:
        output_dir, cache_dir = _run_smoke(tmp_path, "missing")
        (tmp_path / "missing" / "out" / "agent_report.md").unlink()
        problems = validate_agent_artifacts(output_dir, cache_dir)
        assert any("agent_report.md" in p for p in problems)

    def test_corrupt_json_fails(self, tmp_path) -> None:
        output_dir, cache_dir = _run_smoke(tmp_path, "corrupt")
        (tmp_path / "corrupt" / "out" / "agent_benchmark_results.json").write_text(
            "{not json", encoding="utf-8"
        )
        problems = validate_agent_artifacts(output_dir, cache_dir)
        assert any("unparseable" in p for p in problems)

    def test_wrong_summary_key_type_fails(self, tmp_path) -> None:
        output_dir, cache_dir = _run_smoke(tmp_path, "types")
        path = tmp_path / "types" / "out" / "agent_benchmark_results.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["num_pairs"] = "not-an-int"
        path.write_text(json.dumps(data), encoding="utf-8")
        problems = validate_agent_artifacts(output_dir, cache_dir)
        assert any("num_pairs" in p for p in problems)

    def test_csv_header_mismatch_fails(self, tmp_path) -> None:
        output_dir, cache_dir = _run_smoke(tmp_path, "csv")
        path = tmp_path / "csv" / "out" / "agent_benchmark_summary.csv"
        path.write_text("wrong,columns\n1,2\n", encoding="utf-8")
        problems = validate_agent_artifacts(output_dir, cache_dir)
        assert any("header mismatch" in p for p in problems)


# ----------------------------------------------------------------------
# Smoke pipeline: 4 scenarios x 2 arms x 1 seed
# ----------------------------------------------------------------------


def _run_smoke(tmp_path, name: str, backend_factory=None, use_cache: bool = True):
    """Run the full pipeline into tmp directories and return (out, cache)."""
    output_dir = str(tmp_path / name / "out")
    cache_dir = str(tmp_path / name / "cache")
    run_agent_benchmark(
        seeds=1,
        steps=10,
        backend_factory=backend_factory,
        use_cache=use_cache,
        cache_dir=cache_dir,
        output_dir=output_dir,
    )
    return output_dir, cache_dir


class TestSmokePipeline:
    def test_pipeline_completes_with_correct_artifacts(self, tmp_path) -> None:
        output_dir, cache_dir = _run_smoke(tmp_path, "smoke")
        for name in (
            "agent_report.md",
            "agent_benchmark_results.json",
            "agent_benchmark_summary.csv",
            "cache_manifest.json",
        ):
            assert (tmp_path / "smoke" / "out" / name).exists(), name
        results = json.loads(
            (tmp_path / "smoke" / "out" / "agent_benchmark_results.json").read_text(
                encoding="utf-8"
            )
        )
        assert results["num_pairs"] == 4
        assert results["num_steps"] == 40  # 4 pairs x 10 steps per pair (2 arms each)

    def test_second_run_replays_from_cache_with_zero_backend_calls(self, tmp_path) -> None:
        output_dir = str(tmp_path / "replay" / "out")
        cache_dir = str(tmp_path / "replay" / "cache")
        calls: list[str] = []

        def factory(scenario: str) -> _CountingBackend:
            return _CountingBackend(calls)

        first = run_agent_benchmark(
            seeds=1,
            steps=10,
            backend_factory=factory,
            cache_dir=cache_dir,
            output_dir=output_dir,
        )
        first_calls = len(calls)
        assert 0 < first_calls <= 80  # arm 2 may hit arm 1's entries
        assert first["cache_stats"]["hits"] + first["cache_stats"]["misses"] == 80
        assert first["cache_stats"]["misses"] == first_calls

        calls.clear()
        second = run_agent_benchmark(
            seeds=1,
            steps=10,
            backend_factory=factory,
            cache_dir=cache_dir,
            output_dir=output_dir,
        )
        assert calls == []  # bit-identical replay: zero backend calls
        assert second["cache_stats"] == {"hits": 80, "misses": 0}

    def test_uncached_pipeline_calls_backend_every_step(self, tmp_path) -> None:
        calls: list[str] = []
        output_dir = str(tmp_path / "no-cache" / "out")
        run_agent_benchmark(
            seeds=1,
            steps=10,
            backend_factory=lambda scenario: _CountingBackend(calls),
            use_cache=False,
            cache_dir=str(tmp_path / "no-cache" / "cache"),
            output_dir=output_dir,
        )
        assert len(calls) == 80

    def test_stub_is_default_backend(self, tmp_path) -> None:
        output_dir, cache_dir = _run_smoke(tmp_path, "stub-default", backend_factory=None)
        assert validate_agent_artifacts(output_dir, cache_dir) == []

    def test_rejects_zero_seeds_and_steps(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="seeds"):
            run_agent_benchmark(seeds=0, steps=10, cache_dir=str(tmp_path), output_dir=str(tmp_path))
        with pytest.raises(ValueError, match="steps"):
            run_agent_benchmark(seeds=1, steps=0, cache_dir=str(tmp_path), output_dir=str(tmp_path))
