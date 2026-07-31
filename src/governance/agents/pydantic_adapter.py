"""
Real LLM agent backend via PydanticAI.

PydanticAI is the single provider abstraction: model strings are
provider-prefixed (``openai:gpt-4o``, ``anthropic:claude-sonnet-4.6``,
``openrouter:anthropic/claude-sonnet-4.6``, ``ollama:llama3.1``, ...),
so switching providers is a config change, not a code change.

The LLM response is schema-validated by PydanticAI against
:class:`_AgentOutput` at the boundary — the Capability Layer can only
produce well-typed output for the Governance Layer to constrain.

Real-world analogy:
    The adapter is the pilot's radio. The tower does not care which
    brand of radio it is; it cares that the filed flight plan arrives
    on the correct frequency and in the correct format.
"""

import os
from typing import Any, Final

from .base import (
    ACTION_DESCRIPTIONS_KEY,
    OBSERVATION_KEY,
    AgentAction,
    AgentBackend,
)

#: Environment variable selecting the model string (provider-prefixed).
MODEL_ENV_VAR: Final[str] = "GOVERNANCE_LLM_MODEL"

#: Default model: Claude Sonnet via OpenRouter (single API key).
DEFAULT_MODEL: Final[str] = "openrouter:anthropic/claude-sonnet-4.6"


class PydanticAIAdapter(AgentBackend):
    """LLM agent backend backed by a ``pydantic_ai.Agent``.

    The underlying :class:`pydantic_ai.Agent` is constructed lazily on
    the first call so that a missing API key (or absent optional
    dependency) does not break import or construction.

    Args:
        model: Provider-prefixed model string. Defaults to the
            ``GOVERNANCE_LLM_MODEL`` environment variable, falling
            back to :data:`DEFAULT_MODEL`.
        system_prompt: Scenario system prompt (see
            :func:`~.prompts.build_system_prompt`).
        temperature: Sampling temperature passed via model settings.
            ``0.0`` (default) makes full benchmark runs deterministic.
    """

    backend_id = "pydanticai"

    def __init__(
        self,
        system_prompt: str,
        model: str | None = None,
        temperature: float | None = 0.0,
    ):
        self.system_prompt = system_prompt
        self.model = model or os.environ.get(MODEL_ENV_VAR) or DEFAULT_MODEL
        self.temperature = temperature
        self._agent: Any = None

    def _build_agent(self) -> Any:
        """Construct (once) the underlying ``pydantic_ai.Agent``."""
        if self._agent is not None:
            return self._agent

        from pydantic import BaseModel, Field
        from pydantic_ai import Agent as PydanticAgent

        class _AgentOutput(BaseModel):
            action_index: int = Field(ge=0, description="Index of the chosen action")
            confidence: float = Field(
                ge=0.0, le=1.0, description="Confidence in the choice, 0.0 to 1.0"
            )
            rationale: str = Field(description="Justification for the choice")

        settings = None
        if self.temperature is not None:
            from pydantic_ai import ModelSettings

            settings = ModelSettings(temperature=self.temperature)

        self._agent = PydanticAgent(
            self.model,
            output_type=_AgentOutput,
            system_prompt=self.system_prompt,
            model_settings=settings,
        )
        return self._agent

    def select_action(self, context: dict[str, Any]) -> AgentAction:
        """Ask the LLM for an action and validate the response.

        Args:
            context: Scenario context; requires ``OBSERVATION_KEY``
                (rendered user prompt).

        Returns:
            The validated :class:`AgentAction`.

        Raises:
            ValueError: If the LLM returns an action index outside the
                available action range.
        """
        observation = context[OBSERVATION_KEY]
        n_actions = len(context[ACTION_DESCRIPTIONS_KEY])
        agent = self._build_agent()

        result = agent.run_sync(observation)
        output = result.output

        if not 0 <= output.action_index < n_actions:
            raise ValueError(
                f"LLM returned action_index {output.action_index} "
                f"outside the valid range 0..{n_actions - 1}"
            )
        return AgentAction(
            action_index=output.action_index,
            confidence=output.confidence,
            rationale=output.rationale,
        )
