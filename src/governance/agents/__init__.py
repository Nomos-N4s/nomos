"""
Agent backends for the LLM <-> Parliament integration benchmark.

An agent backend is the Capability Layer's decision engine: given the
current world state, it produces a single :class:`AgentAction`. The
Governance Layer then constrains that action through the Speaker.

Real-world analogy:
    The pilot (the agent) flies the plane; air traffic control (the
    Parliament) approves or vetoes each manoeuvre before it happens.

Backends ship in three flavours:

- :class:`~.base.AgentBackend` — the abstract protocol
- :class:`~.stub.StubBackend` — deterministic fake agent (CI, tests)
- :class:`~.pydantic_adapter.PydanticAIAdapter` — real LLM agent via
  PydanticAI (provider-agnostic: OpenAI, Anthropic, OpenRouter, ...)
"""

from .base import AgentAction, AgentBackend
from .stub import StubBackend

__all__ = ["AgentAction", "AgentBackend", "StubBackend"]
