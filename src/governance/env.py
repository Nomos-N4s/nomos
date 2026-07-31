"""
Project-root ``.env`` loading (thin wrapper over python-dotenv).

The LLM adapter (PydanticAI) reads credentials from the process
environment only; it never reads ``.env`` files. This module makes
agent runs pick up ``OPENROUTER_API_KEY`` and ``GOVERNANCE_LLM_MODEL``
from ``.env`` at the repository root, and it is the single shared
loader for every other backend that reads ``.env`` (Neo4j).

Precedence: real environment variables always win — ``.env`` values
are applied with ``load_dotenv(override=False)`` (``setdefault``
semantics). Parsing quirks (quoting, ``#`` comments, ``export``
prefix, ``$VAR`` interpolation) are handled by python-dotenv.

Real-world analogy:
    The pre-flight checklist card taped to the pilot's console: it
    reminds you to load the flight plan and keys *before* starting
    the engine, and it never overrides what the tower (the real
    environment) has already told you.
"""

from pathlib import Path

from dotenv import dotenv_values, load_dotenv

#: The ``.env`` file lives at the repository root (gitignored).
_ENV_FILE_NAME = ".env"


def project_root() -> Path:
    """Path of the repository root (three levels up from this file)."""
    return Path(__file__).resolve().parents[2]


def load_project_env(env_path: str | Path | None = None) -> dict[str, str]:
    """Load ``key=value`` entries from the project ``.env`` into the process.

    Parsing is delegated to python-dotenv (quotes, ``#`` comments,
    ``export`` prefix, ``$VAR`` interpolation). Existing environment
    variables take precedence over ``.env`` values (``override=False``
    semantics) — the real shell environment is authoritative.

    Args:
        env_path: Override for the ``.env`` path (tests). Defaults to
            ``<repo root>/.env``.

    Returns:
        The ``(key, value)`` pairs parsed from the file, for
        inspection. Interpolation is applied with environment
        precedence, matching what is written to ``os.environ``.
    """
    path = Path(env_path) if env_path is not None else project_root() / _ENV_FILE_NAME
    load_dotenv(path, override=False)
    return {k: v for k, v in dotenv_values(path).items() if v is not None}
