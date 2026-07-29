from pathlib import Path

import pytest

from src.governance.dsl import (
    DSLContractConfig,
    DSLMemberConfig,
    DSLParseError,
    DSLSpeakerConfig,
    DSLValidationError,
    ParliamentConfig,
    parse_file,
    parse_string,
    validate,
)

_VALID_PARLIAMENT = """
parliament:
  member reward:
    class: RewardMember
    budget: 100
    veto_threshold: 0.5
    weight: 1.0
  speaker:
    default_action: emergency_shutdown
    majority_threshold: 0.5
    supermajority_threshold: 0.66
    max_rounds: 3
"""


def test_parse_minimal_parliament() -> None:
    config = parse_string(_VALID_PARLIAMENT)
    assert len(config.members) == 1
    assert len(config.contracts) == 0
    assert config.speaker.max_rounds == 3


def test_parse_multiple_members() -> None:
    text = """
parliament:
  member reward:
    class: RewardMember
    budget: 50
    veto_threshold: 0.5
    weight: 1.0
  member safety:
    class: SafetyMember
    budget: 80
    veto_threshold: 0.3
    weight: 0.8
  speaker:
    default_action: shutdown
    majority_threshold: 0.5
    supermajority_threshold: 0.66
    max_rounds: 3
"""
    config = parse_string(text)
    assert len(config.members) == 2
    assert config.members[0].member_id == "reward"
    assert config.members[1].member_id == "safety"


def test_parse_contracts() -> None:
    text = """
parliament:
  member m:
    class: M
    budget: 10
    veto_threshold: 0.5
    weight: 1.0
  contract a:
    restricted_indices: [0, 1, 2]
    enactment_threshold: 0.66
    revocation_threshold: 1.0
    enforcement_mode: hard
  contract b:
    restricted_indices: []
    enactment_threshold: 0.5
    revocation_threshold: 0.8
    enforcement_mode: soft
  speaker:
    default_action: x
    majority_threshold: 0.5
    supermajority_threshold: 0.66
    max_rounds: 3
"""
    config = parse_string(text)
    assert len(config.contracts) == 2
    assert config.contracts[0].contract_id == "a"
    assert config.contracts[0].restricted_indices == (0, 1, 2)
    assert config.contracts[0].enforcement_mode == "hard"
    assert config.contracts[1].restricted_indices == ()


def test_parse_config_key_values() -> None:
    text = """
parliament:
  member m:
    class: M
    budget: 10
    veto_threshold: 0.5
    weight: 1.0
    config:
      learning_rate: 0.01
      batch_size: 32
      optimizer: adam
  speaker:
    default_action: x
    majority_threshold: 0.5
    supermajority_threshold: 0.66
    max_rounds: 3
"""
    config = parse_string(text)
    cfg = config.members[0].config
    assert cfg["learning_rate"] == 0.01
    assert cfg["batch_size"] == 32
    assert cfg["optimizer"] == "adam"


@pytest.mark.parametrize("mode", ["soft", "hard", "constitutional"])
def test_all_enforcement_modes(mode: str) -> None:
    text = f"""
parliament:
  member m:
    class: M
    budget: 10
    veto_threshold: 0.5
    weight: 1.0
  contract c:
    restricted_indices: [0]
    enactment_threshold: 0.66
    revocation_threshold: 1.0
    enforcement_mode: {mode}
  speaker:
    default_action: x
    majority_threshold: 0.5
    supermajority_threshold: 0.66
    max_rounds: 3
"""
    config = parse_string(text)
    assert config.contracts[0].enforcement_mode == mode


def test_parse_with_comments() -> None:
    text = """
# This is a comment
parliament:
  # Another comment
  member m:
    class: M
    budget: 10
    veto_threshold: 0.5
    weight: 1.0
  speaker:
    default_action: x
    majority_threshold: 0.5
    supermajority_threshold: 0.66
    max_rounds: 3
"""
    config = parse_string(text)
    assert len(config.members) == 1


def test_parse_file(tmp_path: Path) -> None:
    path = tmp_path / "test.parliament"
    path.write_text(_VALID_PARLIAMENT, encoding="utf-8")
    config = parse_file(path)
    assert len(config.members) == 1


def test_parse_quoted_string_value() -> None:
    text = """
parliament:
  member m:
    class: "My Member"
    budget: 10
    veto_threshold: 0.5
    weight: 1.0
  speaker:
    default_action: x
    majority_threshold: 0.5
    supermajority_threshold: 0.66
    max_rounds: 3
"""
    config = parse_string(text)
    assert config.members[0].class_name == "My Member"


def test_malformed_syntax_raises_error() -> None:
    with pytest.raises(DSLParseError):
        parse_string("parliament:\n  member:\n    class:\n")


def test_unexpected_section() -> None:
    with pytest.raises(DSLParseError, match="unexpected section"):
        parse_string("parliament:\n  foo:\n    x: 1\n")


def test_missing_speaker() -> None:
    with pytest.raises(DSLParseError, match="missing required.*speaker"):
        parse_string("parliament:\n  member m:\n    class: M\n    budget: 10\n    veto_threshold: 0.5\n    weight: 1.0\n")


def test_parse_full_output_structure() -> None:
    config = parse_string(_VALID_PARLIAMENT)
    assert isinstance(config, ParliamentConfig)
    assert isinstance(config.members[0], DSLMemberConfig)
    assert isinstance(config.speaker, DSLSpeakerConfig)


# -- Error tests (parse, not validate) --

def test_empty_document() -> None:
    with pytest.raises(DSLParseError, match="empty"):
        parse_string("")


def test_missing_root() -> None:
    with pytest.raises(DSLParseError, match="root must be"):
        parse_string("foo: bar\n")


def test_empty_kv_key() -> None:
    with pytest.raises(DSLParseError, match="empty key"):
        parse_string("parliament:\n  : value\n")


def test_kv_without_colon() -> None:
    with pytest.raises(DSLParseError, match="expected key: value"):
        parse_string("parliament:\n  member m:\n    budget\n")


def test_missing_member_id() -> None:
    with pytest.raises(DSLParseError):
        parse_string("parliament:\n  member:\n    class: M\n    budget: 10\n    veto_threshold: 0.5\n    weight: 1.0\n  speaker:\n    default_action: x\n    majority_threshold: 0.5\n    supermajority_threshold: 0.66\n    max_rounds: 3\n")


def test_missing_required_field() -> None:
    with pytest.raises(DSLParseError, match="missing required field"):
        parse_string("parliament:\n  member m:\n    class: M\n    budget: 10\n    weight: 1.0\n  speaker:\n    default_action: x\n    majority_threshold: 0.5\n    supermajority_threshold: 0.66\n    max_rounds: 3\n")


# -- Validator tests (direct config construction) --

def _make_config(
    members: tuple[DSLMemberConfig, ...] = (),
    contracts: tuple[DSLContractConfig, ...] = (),
    speaker: DSLSpeakerConfig = DSLSpeakerConfig(
        default_action="x", majority_threshold=0.5, supermajority_threshold=0.66, max_rounds=3
    ),
) -> ParliamentConfig:
    return ParliamentConfig(members=members, contracts=contracts, speaker=speaker)


def test_validate_duplicate_member_id() -> None:
    config = _make_config(
        members=(
            DSLMemberConfig(member_id="m", class_name="M", budget=10, veto_threshold=0.5, weight=1.0),
            DSLMemberConfig(member_id="m", class_name="N", budget=20, veto_threshold=0.5, weight=1.0),
        )
    )
    with pytest.raises(DSLValidationError, match="duplicate member identifier.*m"):
        validate(config)


def test_validate_duplicate_contract_id() -> None:
    config = _make_config(
        members=(DSLMemberConfig(member_id="m", class_name="M", budget=10, veto_threshold=0.5, weight=1.0),),
        contracts=(
            DSLContractConfig(contract_id="c", restricted_indices=(0,), enactment_threshold=0.66, revocation_threshold=1.0, enforcement_mode="hard"),
            DSLContractConfig(contract_id="c", restricted_indices=(1,), enactment_threshold=0.5, revocation_threshold=0.8, enforcement_mode="soft"),
        )
    )
    with pytest.raises(DSLValidationError, match="duplicate contract identifier.*c"):
        validate(config)


@pytest.mark.parametrize("budget", [0, -5])
def test_validate_budget_range(budget: int) -> None:
    config = _make_config(
        members=(DSLMemberConfig(member_id="m", class_name="M", budget=budget, veto_threshold=0.5, weight=1.0),)
    )
    with pytest.raises(DSLValidationError, match="budget must be positive"):
        validate(config)


@pytest.mark.parametrize("field,bad", [
    ("veto_threshold", -0.1),
    ("veto_threshold", 1.5),
    ("weight", -0.1),
    ("weight", 1.5),
])
def test_validate_member_ranges(field: str, bad: float) -> None:
    kwargs: dict = {"member_id": "m", "class_name": "M", "budget": 10, "veto_threshold": 0.5, "weight": 1.0}
    kwargs[field] = bad
    config = _make_config(members=(DSLMemberConfig(**kwargs),))
    with pytest.raises(DSLValidationError):
        validate(config)


@pytest.mark.parametrize("field,bad", [
    ("enactment_threshold", -0.1),
    ("enactment_threshold", 1.5),
    ("revocation_threshold", -0.1),
    ("revocation_threshold", 1.5),
])
def test_validate_contract_ranges(field: str, bad: float) -> None:
    kwargs: dict = {
        "contract_id": "c", "restricted_indices": (0,),
        "enactment_threshold": 0.66, "revocation_threshold": 1.0, "enforcement_mode": "hard",
    }
    kwargs[field] = bad
    config = _make_config(
        members=(DSLMemberConfig(member_id="m", class_name="M", budget=10, veto_threshold=0.5, weight=1.0),),
        contracts=(DSLContractConfig(**kwargs),)
    )
    with pytest.raises(DSLValidationError):
        validate(config)


def test_validate_invalid_enforcement_mode() -> None:
    config = _make_config(
        members=(DSLMemberConfig(member_id="m", class_name="M", budget=10, veto_threshold=0.5, weight=1.0),),
        contracts=(DSLContractConfig(contract_id="c", restricted_indices=(0,), enactment_threshold=0.66, revocation_threshold=1.0, enforcement_mode="invalid"),)
    )
    with pytest.raises(DSLValidationError, match="enforcement_mode"):
        validate(config)


def test_validate_negative_restricted_index() -> None:
    config = _make_config(
        members=(DSLMemberConfig(member_id="m", class_name="M", budget=10, veto_threshold=0.5, weight=1.0),),
        contracts=(DSLContractConfig(contract_id="c", restricted_indices=(-1,), enactment_threshold=0.66, revocation_threshold=1.0, enforcement_mode="hard"),)
    )
    with pytest.raises(DSLValidationError, match="non-negative"):
        validate(config)


@pytest.mark.parametrize("field,bad", [
    ("majority_threshold", -0.1),
    ("majority_threshold", 1.5),
    ("supermajority_threshold", -0.1),
    ("supermajority_threshold", 1.5),
    ("max_rounds", 0),
    ("max_rounds", -1),
])
def test_validate_speaker_params(field: str, bad: float | int) -> None:
    kwargs: dict = {
        "default_action": "x", "majority_threshold": 0.5,
        "supermajority_threshold": 0.66, "max_rounds": 3,
    }
    kwargs[field] = bad
    config = _make_config(
        members=(DSLMemberConfig(member_id="m", class_name="M", budget=10, veto_threshold=0.5, weight=1.0),),
        speaker=DSLSpeakerConfig(**kwargs)
    )
    with pytest.raises(DSLValidationError):
        validate(config)
