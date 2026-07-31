"""
Agent validation benchmark pipeline.

``run_agent_benchmark`` drives the governed/ungoverned comparison
harness across all four LLM-native scenarios, optionally through a
content-addressed response cache, and writes the full artifact set
(reports + cache manifest) to ``results/agent/``.

The pipeline is the single entry point shared by three consumers:

- the CLI (``python -m src.governance.runner agent``)
- the ``benchmark-agent-smoke`` CI job
- the test suite (smoke-pipeline tests)

Real-world analogy:
    The standard operating procedure for a flight-test campaign: every
    exercise (scenario) is flown with the same instrumentation
    (harness), the same pilot (backend), and the same flight recorder
    (cache) — so the campaign can be re-flown identically by any
    reviewer.
"""

import os
from collections.abc import Callable, Sequence
from typing import Any, cast

from ..committee.members import (
    ExampleCuriosityMember,
    ExampleIntegrityMember,
    ExampleMemoryMember,
    ExamplePlanningMember,
    ExampleRewardMember,
    ExampleSafetyMember,
    ExampleSocialMember,
)
from ..experiments.base import ExperimentScenario
from ..identity.core import (
    CommitmentThreshold,
    CommitmentType,
    CoreCommitment,
    EnforcementMode,
    IdentityCore,
)
from ..speaker import SpeakerStateMachine
from ..tee.watchdog import DeadlockBreaker
from .base import AgentBackend
from .cache import (
    CACHE_MANIFEST_NAME,
    DEFAULT_CACHE_DIR,
    CachedBackend,
    write_cache_manifest,
)
from .harness import GovernorComparisonHarness, PairResult
from .report import AGENT_REPORT_DIR, run_agent_analysis
from .scenarios import (
    DeadlockMazeLLM,
    DriftLabLLM,
    GridWorldLLM,
    LLMScenario,
    TemptationBankLLM,
)

#: The four LLM-native validation scenarios, in benchmark order.
ALL_AGENT_SCENARIOS: list[type[LLMScenario]] = [
    GridWorldLLM,
    TemptationBankLLM,
    DriftLabLLM,
    DeadlockMazeLLM,
]

#: The identity commitment exercised by the DriftLab scenario.
DRIFT_COMMITMENT_TEXT = "Always classify honestly"

#: Threshold of stalled cycles before the deadlock breaker fires.
DEADLOCK_BREAKER_CYCLES = 5


def build_agent_speaker() -> SpeakerStateMachine:
    """Build the standard seven-member Parliament for agent runs.

    All seven framework members (reward, safety, curiosity, planning,
    memory, social, integrity) score the agent's proposals. Each member
    reads its own metadata key with a safe default, so proposals from
    any scenario's action space are scored without crash.

    Returns:
        A :class:`~..speaker.SpeakerStateMachine` with the full
        parliament and the ``stand_still`` fallback action used by all
        four LLM-native scenarios.
    """
    members = [
        ExampleRewardMember(),
        ExampleSafetyMember(),
        ExampleCuriosityMember(),
        ExamplePlanningMember(),
        ExampleMemoryMember(),
        ExampleSocialMember(),
        ExampleIntegrityMember(),
    ]
    return SpeakerStateMachine(
        members={member.member_id: member for member in members},
        default_action="stand_still",
    )


def build_scenario(
    scenario_cls: type[LLMScenario], speaker: SpeakerStateMachine, seed: int = 0
) -> LLMScenario:
    """Build a fresh scenario instance with its required collaborators.

    Two scenarios need construction-time collaborators beyond the
    Speaker: DriftLabLLM receives an :class:`IdentityCore` preloaded
    with its core commitment (Chapter 4), and DeadlockMazeLLM receives
    a :class:`DeadlockBreaker` (Chapter 4 liveness exception).

    Args:
        scenario_cls: One of the four LLM-native scenario classes.
        speaker: The governance Speaker.
        seed: RNG seed for stochastic scenarios (GridWorld, DriftLab).

    Returns:
        A freshly constructed scenario instance.
    """
    if scenario_cls is DriftLabLLM:
        identity = IdentityCore()
        identity.add_commitment(
            CoreCommitment(
                CommitmentType.VALUE_PRINCIPLE,
                DRIFT_COMMITMENT_TEXT,
                CommitmentThreshold.SUPERMAJORITY,
                EnforcementMode.INTEGRITY_VETO,
                affected_action_indices=[0],
            )
        )
        return DriftLabLLM(speaker, identity, seed=seed)
    if scenario_cls is DeadlockMazeLLM:
        return DeadlockMazeLLM(speaker, DeadlockBreaker(threshold_cycles=DEADLOCK_BREAKER_CYCLES))
    if scenario_cls is GridWorldLLM:
        return GridWorldLLM(speaker, seed=seed)
    return TemptationBankLLM(speaker)


def stub_backend_factory(_scenario: LLMScenario) -> AgentBackend:
    """Default backend factory: deterministic stub for every scenario.

    The stub is seeded and script-free, so both arms of every pair
    consume identical, reproducible action streams.

    Args:
        _scenario: The scenario being run (unused; kept for the
            factory protocol).

    Returns:
        A fresh :class:`~.stub.StubBackend`.
    """
    from .stub import StubBackend

    return StubBackend(seed=0)


def run_agent_benchmark(
    *,
    scenarios: Sequence[type[LLMScenario]] = ALL_AGENT_SCENARIOS,
    seeds: int = 1,
    steps: int = 100,
    backend_factory: Callable[[LLMScenario], AgentBackend] | None = None,
    use_cache: bool = True,
    cache_dir: str = DEFAULT_CACHE_DIR,
    output_dir: str = AGENT_REPORT_DIR,
) -> dict[str, Any]:
    """Run the full agent validation benchmark and write all artifacts.

    For every scenario and seed, a governed/ungoverned pair is run
    through the harness. The backend is built fresh per pair (scenario
    system prompts differ), and — when ``use_cache`` — wrapped in a
    :class:`CachedBackend` so re-runs with the same cache directory
    replay stored responses without a single backend call.

    Args:
        scenarios: Scenario classes to run (default: all four).
        seeds: Number of seed pairs per scenario.
        steps: Steps per arm.
        backend_factory: Builds the backend for a scenario; receives
            a freshly built scenario instance (its ``system_prompt``
            briefs the agent). Defaults to the deterministic stub.
        use_cache: Wrap backends in the response cache.
        cache_dir: Cache directory (shared across scenarios; entries
            are keyed by model, prompt hash, and temperature).
        output_dir: Where the report artifacts are written.

    Returns:
        Dict with keys ``pairs`` (all :class:`PairResult` objects),
        ``analysis`` (the :func:`~.report.run_agent_analysis` result),
        ``cache_stats`` (aggregated hit/miss counters), and
        ``manifest_path`` (the written cache manifest, or ``None`` when
        caching is disabled).

    Raises:
        ValueError: If ``seeds`` or ``steps`` is less than one.
    """
    if seeds < 1:
        raise ValueError(f"seeds must be >= 1, got {seeds}")
    if steps < 1:
        raise ValueError(f"steps must be >= 1, got {steps}")

    factory = backend_factory or stub_backend_factory
    pairs: list[PairResult] = []
    cache_stats = {"hits": 0, "misses": 0}

    for scenario_cls in scenarios:
        for seed in range(seeds):
            speaker = build_agent_speaker()
            scenario = build_scenario(scenario_cls, speaker, seed)
            backend = factory(scenario)
            if use_cache:
                backend = CachedBackend(backend, cache_dir=cache_dir)
            harness = GovernorComparisonHarness(
                lambda sp, cls=scenario_cls, s=seed: build_scenario(cls, sp, s),
                backend,
                scenario_cls.action_space(),
                speaker,
                observation_fn=lambda scenario: _render_observation(scenario),
            )
            pair = harness.run_pair(seed=seed, steps=steps)
            pairs.append(pair)
            if use_cache:
                stats = cast(CachedBackend, backend).cache_stats()
                cache_stats["hits"] += stats["hits"]
                cache_stats["misses"] += stats["misses"]

    analysis = run_agent_analysis(pairs, output_dir=output_dir)
    manifest_path = os.path.join(output_dir, CACHE_MANIFEST_NAME)
    if use_cache:
        write_cache_manifest(cache_dir, manifest_path)
    else:
        manifest_path = None

    return {
        "pairs": pairs,
        "analysis": analysis,
        "cache_stats": cache_stats,
        "manifest_path": manifest_path,
    }


def _render_observation(scenario: ExperimentScenario) -> str:
    """Render the LLM-native observation text for the harness.

    The harness types observations as the base scenario; the agent
    scenarios narrow it to the LLM renderer.

    Args:
        scenario: The live scenario instance.

    Returns:
        The textual state render shown to the agent.
    """
    return cast(LLMScenario, scenario).render_observation()
