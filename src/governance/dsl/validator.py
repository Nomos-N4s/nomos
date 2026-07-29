from __future__ import annotations

from src.governance.dsl.errors import DSLValidationError
from src.governance.dsl.models import (
    DSLContractConfig,
    DSLMemberConfig,
    DSLSpeakerConfig,
    ParliamentConfig,
)

_VALID_ENFORCEMENT_MODES = frozenset({"soft", "hard", "constitutional"})


def validate(config: ParliamentConfig) -> None:
    _validate_members(config.members)
    _validate_contracts(config.contracts)
    _validate_speaker(config.speaker)


def _validate_members(members: tuple[DSLMemberConfig, ...]) -> None:
    seen: set[str] = set()
    for member in members:
        if not member.member_id:
            raise DSLValidationError("member has empty member_id")
        if member.member_id in seen:
            raise DSLValidationError(f"duplicate member identifier '{member.member_id}'")
        seen.add(member.member_id)

        if member.budget <= 0:
            raise DSLValidationError(
                f"member '{member.member_id}': budget must be positive, got {member.budget}"
            )
        if not 0.0 <= member.veto_threshold <= 1.0:
            raise DSLValidationError(
                f"member '{member.member_id}': veto_threshold must be in [0.0, 1.0], "
                f"got {member.veto_threshold}"
            )
        if not 0.0 <= member.weight <= 1.0:
            raise DSLValidationError(
                f"member '{member.member_id}': weight must be in [0.0, 1.0], got {member.weight}"
            )


def _validate_contracts(contracts: tuple[DSLContractConfig, ...]) -> None:
    seen: set[str] = set()
    for contract in contracts:
        if not contract.contract_id:
            raise DSLValidationError("contract has empty contract_id")
        if contract.contract_id in seen:
            raise DSLValidationError(f"duplicate contract identifier '{contract.contract_id}'")
        seen.add(contract.contract_id)

        if not 0.0 <= contract.enactment_threshold <= 1.0:
            raise DSLValidationError(
                f"contract '{contract.contract_id}': enactment_threshold must be in "
                f"[0.0, 1.0], got {contract.enactment_threshold}"
            )
        if not 0.0 <= contract.revocation_threshold <= 1.0:
            raise DSLValidationError(
                f"contract '{contract.contract_id}': revocation_threshold must be in "
                f"[0.0, 1.0], got {contract.revocation_threshold}"
            )
        if contract.enforcement_mode not in _VALID_ENFORCEMENT_MODES:
            raise DSLValidationError(
                f"contract '{contract.contract_id}': enforcement_mode must be one of "
                f"{sorted(_VALID_ENFORCEMENT_MODES)}, got '{contract.enforcement_mode}'"
            )
        for idx in contract.restricted_indices:
            if idx < 0:
                raise DSLValidationError(
                    f"contract '{contract.contract_id}': restricted_indices must be "
                    f"non-negative, got {idx}"
                )


def _validate_speaker(speaker: DSLSpeakerConfig) -> None:
    if not 0.0 <= speaker.majority_threshold <= 1.0:
        raise DSLValidationError(
            f"speaker: majority_threshold must be in [0.0, 1.0], got {speaker.majority_threshold}"
        )
    if not 0.0 <= speaker.supermajority_threshold <= 1.0:
        raise DSLValidationError(
            f"speaker: supermajority_threshold must be in [0.0, 1.0], "
            f"got {speaker.supermajority_threshold}"
        )
    if speaker.max_rounds <= 0:
        raise DSLValidationError(
            f"speaker: max_rounds must be a positive integer, got {speaker.max_rounds}"
        )
