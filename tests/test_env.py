"""Tests for the project-root ``.env`` loader (python-dotenv wrapper)."""

import os

import pytest

from src.governance.env import load_project_env, project_root


def _write_env(tmp_path, lines: list[str]) -> str:
    env_path = tmp_path / ".env"
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(env_path)


def test_project_root_points_at_repository_root() -> None:
    assert project_root().name == "governance-layer"
    assert (project_root() / "pyproject.toml").is_file()


def test_loads_simple_key_values(tmp_path, monkeypatch) -> None:
    env_path = _write_env(
        tmp_path, ["OPENROUTER_API_KEY=sk-or-v1-abc123", "GOVERNANCE_LLM_MODEL=openrouter:m:free"]
    )
    parsed = load_project_env(env_path)
    assert parsed["OPENROUTER_API_KEY"] == "sk-or-v1-abc123"
    assert parsed["GOVERNANCE_LLM_MODEL"] == "openrouter:m:free"
    assert os.environ["OPENROUTER_API_KEY"] == "sk-or-v1-abc123"


def test_existing_env_variable_wins(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-from-shell")
    env_path = _write_env(tmp_path, ["OPENROUTER_API_KEY=sk-or-v1-from-file"])
    parsed = load_project_env(env_path)
    assert parsed["OPENROUTER_API_KEY"] == "sk-or-v1-from-file"
    assert os.environ["OPENROUTER_API_KEY"] == "sk-or-v1-from-shell"


def test_comments_and_blank_lines_skipped(tmp_path, monkeypatch) -> None:
    env_path = _write_env(
        tmp_path,
        ["# comment", "", "   ", "KEY=value", "# another comment"],
    )
    parsed = load_project_env(env_path)
    assert parsed == {"KEY": "value"}


def test_quoted_and_export_prefix_values(tmp_path, monkeypatch) -> None:
    env_path = _write_env(tmp_path, ['QUOTED="a value"', "export EXPORTED=plain"])
    parsed = load_project_env(env_path)
    assert parsed["QUOTED"] == "a value"
    assert parsed["EXPORTED"] == "plain"


def test_hash_inside_value_preserved(tmp_path, monkeypatch) -> None:
    env_path = _write_env(tmp_path, ["TOKEN=abc#def#ghi"])
    parsed = load_project_env(env_path)
    assert parsed["TOKEN"] == "abc#def#ghi"


def test_missing_env_file_returns_empty(tmp_path, monkeypatch) -> None:
    missing = str(tmp_path / "does-not-exist.env")
    assert load_project_env(missing) == {}


def test_interpolation_uses_existing_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BASE_URL", "https://example.org")
    env_path = _write_env(tmp_path, ["API_ENDPOINT=${BASE_URL}/v1"])
    parsed = load_project_env(env_path)
    assert parsed["API_ENDPOINT"] == "https://example.org/v1"
