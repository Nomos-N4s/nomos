from __future__ import annotations

from pathlib import Path

from lark import Lark, Token, Transformer, UnexpectedInput

from src.governance.dsl.errors import DSLParseError
from src.governance.dsl.models import (
    DSLContractConfig,
    DSLMemberConfig,
    DSLSpeakerConfig,
    ParliamentConfig,
)


class ParliamentTransformer(Transformer):
    @staticmethod
    def _skip(items: list) -> list:
        return [i for i in items if not isinstance(i, Token)]

    # -- Terminal handlers --

    def INT(self, token: Token) -> int:
        return int(token.value)

    def FLOAT(self, token: Token) -> float:
        return float(token.value)

    def ESCAPED_STRING(self, token: Token) -> str:
        return token.value[1:-1]

    def CNAME(self, token: Token) -> str:
        return str(token.value)

    def ENFORCEMENT_MODE(self, token: Token) -> str:
        return str(token.value)

    # -- Rule handlers --

    def start(self, items: list) -> ParliamentConfig:
        return items[0]

    def parliament(self, items: list) -> ParliamentConfig:
        items = self._skip(items)
        members: list[DSLMemberConfig] = []
        contracts: list[DSLContractConfig] = []
        speaker: DSLSpeakerConfig | None = None
        for item in items:
            if isinstance(item, DSLMemberConfig):
                members.append(item)
            elif isinstance(item, DSLContractConfig):
                contracts.append(item)
            elif isinstance(item, DSLSpeakerConfig):
                speaker = item
        return ParliamentConfig(
            members=tuple(members),
            contracts=tuple(contracts),
            speaker=speaker,
        )

    def member_def(self, items: list) -> DSLMemberConfig:
        items = self._skip(items)
        config: dict[str, int | float | str] = {}
        for kv in items[5:]:
            if isinstance(kv, tuple) and len(kv) == 2:
                config[kv[0]] = kv[1]
        return DSLMemberConfig(
            member_id=items[0],
            class_name=items[1],
            budget=items[2],
            veto_threshold=items[3],
            weight=items[4],
            config=config,
        )

    def contract_def(self, items: list) -> DSLContractConfig:
        items = self._skip(items)
        restricted_indices = tuple(items[1:-3])
        enactment_threshold: float = items[-3]
        revocation_threshold: float = items[-2]
        enforcement_mode: str = items[-1]
        return DSLContractConfig(
            contract_id=items[0],
            restricted_indices=restricted_indices,
            enactment_threshold=enactment_threshold,
            revocation_threshold=revocation_threshold,
            enforcement_mode=enforcement_mode,
        )

    def speaker_config(self, items: list) -> DSLSpeakerConfig:
        items = self._skip(items)
        return DSLSpeakerConfig(
            default_action=items[0],
            majority_threshold=items[1],
            supermajority_threshold=items[2],
            max_rounds=items[3],
        )

    def key_value(self, items: list) -> tuple[str, int | float | str]:
        items = self._skip(items)
        return (items[0], items[1])

    def value(self, items: list) -> int | float | str:
        items = self._skip(items)
        return items[0]


_GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"
_parser = Lark.open(
    str(_GRAMMAR_PATH),
    parser="lalr",
    maybe_placeholders=False,
)
_transformer = ParliamentTransformer()


def parse_string(text: str) -> ParliamentConfig:
    try:
        tree = _parser.parse(text)
        return _transformer.transform(tree)
    except UnexpectedInput as e:
        raise DSLParseError(
            str(e), line=getattr(e, "line", None), column=getattr(e, "column", None)
        ) from e


def parse_file(path: str | Path) -> ParliamentConfig:
    text = Path(path).read_text(encoding="utf-8")
    return parse_string(text)
