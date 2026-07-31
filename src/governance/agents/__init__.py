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

The :class:`~.harness.GovernorComparisonHarness` pairs a backend against
itself with and without governance, so the effect of the Parliament can
be measured on identical trials, and :mod:`~.metrics` turns the paired
traces into violation rates, reward preservation, veto precision/recall,
latency percentiles, and LLM-as-judge alignment statistics. Results are
reported to ``results/agent/`` by :mod:`~.report`.
"""

from .base import AgentAction, AgentBackend
from .harness import ActionSpace, ArmResult, GovernorComparisonHarness, PairResult
from .metrics import (
    AgentPairMetrics,
    AgentSummary,
    JudgeAlignmentMetrics,
    JudgeAssessment,
    compute_pair_metrics,
    judge_alignment,
    latency_percentiles,
    oracle_would_violate,
    sample_judge_steps,
    summarize_pairs,
)
from .report import run_agent_analysis
from .stub import StubBackend

__all__ = [
    "AgentAction",
    "AgentBackend",
    "ActionSpace",
    "ArmResult",
    "PairResult",
    "GovernorComparisonHarness",
    "StubBackend",
    "AgentPairMetrics",
    "AgentSummary",
    "JudgeAssessment",
    "JudgeAlignmentMetrics",
    "compute_pair_metrics",
    "judge_alignment",
    "latency_percentiles",
    "oracle_would_violate",
    "sample_judge_steps",
    "summarize_pairs",
    "run_agent_analysis",
]
