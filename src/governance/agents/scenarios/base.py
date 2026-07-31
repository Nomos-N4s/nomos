"""
Shared surface of the LLM-native scenarios.

Every LLM scenario is an :class:`ExperimentScenario` that additionally
exposes:

- ``actions`` — the action enum: ``(action value, LLM-readable
  description)`` pairs, index-aligned with the agent's ``action_index``
- ``render_observation()`` — the textual state render shown to the
  agent
- ``proposal_metadata(action)`` — the structured metadata attached when
  the governed arm submits the agent's action as a proposal, so
  Parliament members can score it
- ``system_prompt()`` — the scenario briefing built from
  ``scenario_name`` and ``rules``

The class-level ``action_space()`` assembles an
:class:`~..harness.ActionSpace` whose metadata resolves against the
live scenario instance, which is how state-dependent signals (tile
risk, drift-adjusted reward) reach the Speaker.

Real-world analogy:
    Each scenario is a standardized flight-deck briefing: the pilot
    gets the same instrument layout (action space) and the same
    air-traffic rules (system prompt) on every flight, so behaviour
    differences between flights are attributable to the pilot.
"""

from abc import abstractmethod
from typing import Any

from ...experiments.base import ExperimentScenario
from ...models import Proposal
from ..harness import ActionSpace, ActionSpaceEntry
from ..prompts import build_system_prompt


class LLMScenario(ExperimentScenario):
    """Abstract base for the four LLM-native validation scenarios.

    Subclasses declare ``scenario_name``, ``rules``, and ``actions``,
    and implement :meth:`render_observation`, :meth:`proposal_metadata`,
    and the scenario mechanics via ``_run_step``.

    Note:
        These scenarios ship no agenda of their own: the agent's chosen
        action *is* the agenda (via the comparison harness). Standalone
        ``step()`` calls therefore fall back to the Speaker's default
        action.
    """

    scenario_name: str = "LLMScenario"
    rules: list[str] = []
    actions: list[tuple[Any, str]] = []

    @abstractmethod
    def render_observation(self) -> str:
        """Render the current state as the observation text."""

    @abstractmethod
    def proposal_metadata(self, action: Any) -> dict[str, Any]:
        """Return the proposal metadata for a chosen action.

        Args:
            action: The action value the agent chose.

        Returns:
            A metadata dict (``risk``, ``expected_reward``,
            ``identity_coherence``, ...) for the Speaker's members.
        """

    @classmethod
    def action_descriptions(cls) -> list[str]:
        """The LLM-readable action descriptions, index-aligned."""
        return [description for _, description in cls.actions]

    @classmethod
    def action_space(cls) -> ActionSpace:
        """Build the harness action space for this scenario.

        Metadata resolves against the live scenario instance, so
        state-dependent signals (tile risk, drift-adjusted reward)
        reach the Speaker at submission time.
        """
        return ActionSpace(
            [
                ActionSpaceEntry(
                    action=action,
                    description=description,
                    metadata=lambda scenario, action=action: scenario.proposal_metadata(action),
                )
                for action, description in cls.actions
            ]
        )

    def system_prompt(self) -> str:
        """The scenario briefing built from name and rules."""
        return build_system_prompt(self.scenario_name, list(self.rules))

    def get_proposals(self, state: Any) -> list[Proposal]:
        """No scenario-authored agenda: the agent drives the parliament."""
        return []
