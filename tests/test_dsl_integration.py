"""Integration tests for the DSL config → Speaker pipeline."""

from pathlib import Path

import pytest

from src.governance.dsl import ParliamentConfig, parse_file, validate
from src.governance.runner import (
    _build_contracts,
    _import_member_class,
    build_from_config,
)


def test_build_from_config_gridworld() -> None:
    speaker = build_from_config("examples/grid_world.parliament")
    assert set(speaker.members) == {"reward", "safety", "planning", "integrity"}
    assert speaker.default_action == "emergency_shutdown"
    assert speaker.majority_threshold == 0.5
    assert speaker.supermajority_threshold == 0.66
    assert speaker.max_rounds == 3


def test_build_from_config_temptation_bank() -> None:
    speaker = build_from_config("examples/temptation_bank.parliament")
    assert set(speaker.members) == {"reward", "safety", "integrity"}
    assert speaker.default_action == "reject_loan"


def test_build_from_config_drift_lab() -> None:
    speaker = build_from_config("examples/drift_lab.parliament")
    assert set(speaker.members) == {"reward", "integrity", "curiosity"}
    assert speaker.default_action == "maintain_course"


def test_build_from_config_deadlock_maze() -> None:
    speaker = build_from_config("examples/deadlock_maze.parliament")
    assert set(speaker.members) == {"safety", "integrity", "planning"}
    assert speaker.max_rounds == 5
    assert speaker.supermajority_threshold == 0.75


def test_config_overrides_member_params() -> None:
    """Verify that DSL budget/veto/weight override the class defaults."""
    speaker = build_from_config("examples/grid_world.parliament")
    reward = speaker.members["reward"]
    assert reward.budget == 3
    assert reward.veto_threshold == 0.0
    assert reward.weight == 1.0

    safety = speaker.members["safety"]
    assert safety.budget == 5
    assert safety.veto_threshold == 0.5
    assert safety.weight == 2.0


def test_build_from_config_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        build_from_config("examples/nonexistent.parliament")


def test_build_from_config_invalid_config_raises() -> None:
    text = """parliament:
  member m:
    class: ExampleRewardMember
    budget: -1
    veto_threshold: 0.5
    weight: 1.0
  speaker:
    default_action: x
    majority_threshold: 0.5
    supermajority_threshold: 0.66
    max_rounds: 3
"""
    path = Path("examples/_bad_test.parliament")
    try:
        path.write_text(text, encoding="utf-8")
        from src.governance.dsl.errors import DSLValidationError

        with pytest.raises(DSLValidationError, match="budget must be positive"):
            build_from_config(str(path))
    finally:
        path.unlink(missing_ok=True)


def test_import_member_class_short_name() -> None:
    cls = _import_member_class("ExampleRewardMember")
    assert cls.__name__ == "ExampleRewardMember"


def test_import_member_class_without_example_prefix() -> None:
    """Short name without 'Example' prefix should auto-resolve."""
    cls = _import_member_class("RewardMember")
    assert cls.__name__ == "ExampleRewardMember"


def test_import_member_class_fully_qualified() -> None:
    cls = _import_member_class("governance.committee.members.ExampleSafetyMember")
    assert cls.__name__ == "ExampleSafetyMember"


def test_import_member_class_not_found() -> None:
    with pytest.raises(ImportError, match="cannot import"):
        _import_member_class("NonExistentMember")


def test_build_contracts() -> None:
    config = parse_file("examples/grid_world.parliament")
    contracts = _build_contracts(config)
    assert len(contracts) == 1
    c = contracts[0]
    assert c.contract_id == "poison_ban"
    assert c.restricted_indices == {2}
    assert c.enforcement_mode == "hard"


def test_build_contracts_multiple() -> None:
    config = parse_file("examples/temptation_bank.parliament")
    contracts = _build_contracts(config)
    assert len(contracts) == 1
    assert contracts[0].contract_id == "ban_loans"


def test_all_example_files_parse_valid() -> None:
    for path in Path("examples").glob("*.parliament"):
        config = parse_file(str(path))
        assert isinstance(config, ParliamentConfig)
        validate(config)
        assert len(config.members) >= 1
        assert config.speaker.default_action is not None


def test_build_from_config_all_examples() -> None:
    for path in Path("examples").glob("*.parliament"):
        speaker = build_from_config(str(path))
        assert len(speaker.members) >= 1
        assert speaker.default_action is not None
