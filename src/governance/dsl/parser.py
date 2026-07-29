from __future__ import annotations

from pathlib import Path
from typing import Any

from src.governance.dsl.errors import DSLParseError
from src.governance.dsl.models import (
    DSLContractConfig,
    DSLMemberConfig,
    DSLSpeakerConfig,
    ParliamentConfig,
)


class _Node:
    __slots__ = ("name", "value", "children")

    def __init__(self, name: str, value: Any = None) -> None:
        self.name = name
        self.value = value
        self.children: list[_Node] = []


def parse_string(text: str) -> ParliamentConfig:
    tokens = _tokenize(text)
    forest = _parse_forest(tokens)
    _validate_root(forest)
    return _build(forest[0])


def parse_file(path: str | Path) -> ParliamentConfig:
    return parse_string(Path(path).read_text(encoding="utf-8"))


# -- Tokenizer --

def _tokenize(text: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        result.append((len(line) - len(line.lstrip()), stripped))
    if not result:
        raise DSLParseError("empty document")
    return result


# -- Block parser (indentation-aware) --

def _parse_forest(tokens: list[tuple[int, str]]) -> list[_Node]:
    forest: list[_Node] = []
    stack: list[tuple[int, list[_Node]]] = [(-1, forest)]

    for indent, text in tokens:
        while indent <= stack[-1][0]:
            stack.pop()

        if text.endswith(":"):
            name = text[:-1].strip()
            if not name:
                raise DSLParseError("empty section name")
            node = _Node(name)
            stack[-1][1].append(node)
            stack.append((indent, node.children))
        else:
            if ":" not in text:
                raise DSLParseError(f"expected key: value pair, got '{text}'")
            key, _, raw = text.partition(":")
            key = key.strip()
            if not key:
                raise DSLParseError(f"empty key in '{text}'")
            value = _parse_value(raw.strip())
            stack[-1][1].append(_Node(key, value))

    return forest


def _parse_value(raw: str) -> Any:
    if not raw:
        raise DSLParseError("empty value")

    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return ()
        return tuple(_parse_atom(x.strip()) for x in inner.split(",") if x.strip())

    return _parse_atom(raw)


def _parse_atom(raw: str) -> Any:
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        return raw[1:-1]

    try:
        return int(raw)
    except ValueError:
        pass

    try:
        return float(raw)
    except ValueError:
        pass

    return raw


# -- Root validation --

def _validate_root(forest: list[_Node]) -> None:
    if not forest:
        raise DSLParseError("empty document")
    if len(forest) != 1 or forest[0].name != "parliament":
        names = [n.name for n in forest]
        raise DSLParseError(f"root must be a single 'parliament' section, got {names}")


# -- Build phase --

_MEMBER = "member "
_CONTRACT = "contract "


def _build(root: _Node) -> ParliamentConfig:
    members: list[DSLMemberConfig] = []
    contracts: list[DSLContractConfig] = []
    speaker: DSLSpeakerConfig | None = None

    for node in root.children:
        if node.name.startswith(_MEMBER):
            members.append(_build_member(node))
        elif node.name.startswith(_CONTRACT):
            contracts.append(_build_contract(node))
        elif node.name == "speaker":
            speaker = _build_speaker(node)
        else:
            raise DSLParseError(f"unexpected section '{node.name}' in parliament")

    if speaker is None:
        raise DSLParseError("missing required 'speaker' section")

    return ParliamentConfig(
        members=tuple(members),
        contracts=tuple(contracts),
        speaker=speaker,
    )


def _extract_kvs(children: list[_Node]) -> dict[str, Any]:
    """Extract leaf children as key-value pairs, return remaining section children."""
    result: dict[str, Any] = {}
    for child in children:
        if not child.children:
            result[child.name] = child.value
    return result


def _build_member(node: _Node) -> DSLMemberConfig:
    mid = node.name[len(_MEMBER):].strip()
    if not mid:
        raise DSLParseError("member section missing identifier")

    fields = _extract_kvs(node.children)

    config: dict[str, Any] = {}
    for child in node.children:
        if child.children and child.name == "config":
            config = _extract_kvs(child.children)
            break

    return DSLMemberConfig(
        member_id=mid,
        class_name=_require(fields, "class", mid),
        budget=_require(fields, "budget", mid),
        veto_threshold=_require(fields, "veto_threshold", mid),
        weight=_require(fields, "weight", mid),
        config=config,
    )


def _build_contract(node: _Node) -> DSLContractConfig:
    cid = node.name[len(_CONTRACT):].strip()
    if not cid:
        raise DSLParseError("contract section missing identifier")

    fields = _extract_kvs(node.children)
    return DSLContractConfig(
        contract_id=cid,
        restricted_indices=tuple(_require(fields, "restricted_indices", cid)),
        enactment_threshold=_require(fields, "enactment_threshold", cid),
        revocation_threshold=_require(fields, "revocation_threshold", cid),
        enforcement_mode=_require(fields, "enforcement_mode", cid),
    )


def _build_speaker(node: _Node) -> DSLSpeakerConfig:
    fields = _extract_kvs(node.children)
    return DSLSpeakerConfig(
        default_action=_require(fields, "default_action", "speaker"),
        majority_threshold=_require(fields, "majority_threshold", "speaker"),
        supermajority_threshold=_require(fields, "supermajority_threshold", "speaker"),
        max_rounds=_require(fields, "max_rounds", "speaker"),
    )


def _require(fields: dict[str, Any], key: str, section: str) -> Any:
    if key not in fields:
        raise DSLParseError(f"'{section}' section missing required field '{key}'")
    return fields[key]
