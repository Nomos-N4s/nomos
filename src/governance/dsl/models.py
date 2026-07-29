from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DSLMemberConfig:
    member_id: str
    class_name: str
    budget: int
    veto_threshold: float
    weight: float
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DSLContractConfig:
    contract_id: str
    restricted_indices: tuple[int, ...]
    enactment_threshold: float
    revocation_threshold: float
    enforcement_mode: str


@dataclass(frozen=True)
class DSLSpeakerConfig:
    default_action: str
    majority_threshold: float
    supermajority_threshold: float
    max_rounds: int


@dataclass(frozen=True)
class ParliamentConfig:
    members: tuple[DSLMemberConfig, ...]
    contracts: tuple[DSLContractConfig, ...]
    speaker: DSLSpeakerConfig
