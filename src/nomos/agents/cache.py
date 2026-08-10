"""
Content-addressed response cache for agent benchmark runs.

LLM runs are non-deterministic and costly. This module makes them
reproducible by caching each validated :class:`~.base.AgentAction`
under a content address derived from everything that determines the
response:

- ``model`` — the provider-prefixed model string
- ``prompt_hash`` — SHA-256 of the full rendered prompt (system prompt
  plus observation; any textual change re-keys the cache)
- ``temperature`` — the sampling temperature

Entries are stored as ``{cache_dir}/{sha256}.json`` where the hash is
computed over the canonical JSON of the key triple, so the file name
itself is the content address. Replays with an identical cache
directory reuse stored responses without a single model call, making
bit-identical trajectory replay possible for reviewers.

Real-world analogy:
    A flight recorder's data cartridge. The tower can replay the
    exact flight (same prompts, same responses) without asking the
    pilot to fly again.
"""

import hashlib
import json
import os
from typing import Any, Final

from .base import AgentAction, AgentBackend

#: Default location for cached responses.
DEFAULT_CACHE_DIR: Final[str] = "results/agent/cache"

#: File name of the replay-verification manifest, written to the
#: report output directory.
CACHE_MANIFEST_NAME: Final[str] = "cache_manifest.json"

#: Bumped when the on-disk entry format changes incompatibly.
CACHE_SCHEMA_VERSION: Final[int] = 1


def hash_prompt(system_prompt: str, observation: str) -> str:
    """SHA-256 over the full rendered prompt.

    Args:
        system_prompt: The scenario briefing (constant per scenario).
        observation: The user prompt (state render) shown to the agent.

    Returns:
        Hex SHA-256 digest. Any change to either part re-keys the cache.
    """
    return hashlib.sha256(f"{system_prompt}\n{observation}".encode()).hexdigest()


class ResponseCache:
    """Content-addressed store of validated agent responses.

    Args:
        cache_dir: Directory holding ``{sha256}.json`` entries.
            Created on demand. Defaults to :data:`DEFAULT_CACHE_DIR`.
    """

    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR):
        self.cache_dir = cache_dir
        self.hits = 0
        self.misses = 0

    # ------------------------------------------------------------------
    # Keying
    # ------------------------------------------------------------------

    @staticmethod
    def key_for(model: str, prompt_hash: str, temperature: float | None) -> str:
        """Content address for a response.

        Args:
            model: Provider-prefixed model string (``"stub"`` for
                deterministic backends).
            prompt_hash: SHA-256 of the rendered prompt.
            temperature: Sampling temperature (``None`` when the
                backend has no temperature).

        Returns:
            Hex SHA-256 digest of the canonical key triple.
        """
        canonical = json.dumps(
            {"model": model, "prompt_hash": prompt_hash, "temperature": temperature},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def path_for(self, key: str) -> str:
        """Absolute entry path for a content address."""
        return os.path.join(self.cache_dir, f"{key}.json")

    # ------------------------------------------------------------------
    # Read / write
    # ------------------------------------------------------------------

    def lookup(self, model: str, prompt_hash: str, temperature: float | None) -> AgentAction | None:
        """Return the cached response for a key, or ``None`` on a miss.

        Args:
            model: Model string.
            prompt_hash: Prompt SHA-256.
            temperature: Sampling temperature.

        Returns:
            The stored :class:`AgentAction`, or ``None`` if absent or
            malformed (malformed entries are treated as misses and
            silently overwritten by :meth:`store`).
        """
        path = self.path_for(self.key_for(model, prompt_hash, temperature))
        if not os.path.exists(path):
            self.misses += 1
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            response = data["response"]
            action = AgentAction(
                action_index=response["action_index"],
                confidence=response["confidence"],
                rationale=response["rationale"],
            )
        except (OSError, KeyError, TypeError, ValueError):
            self.misses += 1
            return None
        self.hits += 1
        return action

    def store(
        self,
        model: str,
        prompt_hash: str,
        temperature: float | None,
        action: AgentAction,
    ) -> str:
        """Persist a response under its content address (write-through).

        Args:
            model: Model string.
            prompt_hash: Prompt SHA-256.
            temperature: Sampling temperature.
            action: The validated :class:`AgentAction` to store.

        Returns:
            Path of the written entry.
        """
        key = self.key_for(model, prompt_hash, temperature)
        path = self.path_for(key)
        payload = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "key": {"model": model, "prompt_hash": prompt_hash, "temperature": temperature},
            "response": {
                "action_index": action.action_index,
                "confidence": action.confidence,
                "rationale": action.rationale,
            },
        }
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        return path

    def stats(self) -> dict[str, int]:
        """Hit and miss counters, useful for verifying replay behavior."""
        return {"hits": self.hits, "misses": self.misses}

    def clear(self) -> None:
        """Remove all entries and reset counters (tests, cache wipes)."""
        if os.path.isdir(self.cache_dir):
            for name in os.listdir(self.cache_dir):
                if name.endswith(".json"):
                    os.remove(os.path.join(self.cache_dir, name))
        self.hits = 0
        self.misses = 0


class CachedBackend(AgentBackend):
    """Backend wrapper: replay cached responses, populate on first run.

    The wrapped backend (stub or LLM adapter) is only invoked on a
    cache miss. Key fields are resolved from explicit arguments,
    falling back to the wrapped backend's attributes — adapters carry
    ``model``, ``temperature``, and ``system_prompt``, so the wrapper
    works for any backend unchanged.

    Args:
        backend: The inner :class:`AgentBackend` to wrap.
        cache: The :class:`ResponseCache` to use. Created with
            ``cache_dir`` when omitted.
        cache_dir: Cache directory (only used when ``cache`` is None).
        system_prompt: Scenario briefing. Defaults to the backend's
            ``system_prompt`` attribute (``""`` for backends that have
            none).
        model: Model string. Defaults to the backend's ``model``
            attribute, falling back to the backend id.
        temperature: Sampling temperature. Defaults to the backend's
            ``temperature`` attribute (``None`` when absent).
    """

    def __init__(
        self,
        backend: AgentBackend,
        cache: ResponseCache | None = None,
        cache_dir: str = DEFAULT_CACHE_DIR,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ):
        self._backend = backend
        self._cache = cache or ResponseCache(cache_dir)
        self._system_prompt = (
            system_prompt if system_prompt is not None else getattr(backend, "system_prompt", "")
        )
        self._model = model or getattr(backend, "model", backend.backend_id)
        if temperature is not None:
            self._temperature = temperature
        else:
            self._temperature = getattr(backend, "temperature", None)
        self.backend_id = f"{backend.backend_id}+cache"

    def select_action(self, context: dict[str, Any]) -> AgentAction:
        """Return a cached response when present, else call the backend.

        Args:
            context: The standard backend context; requires
                ``OBSERVATION_KEY`` (the rendered user prompt).

        Returns:
            The :class:`AgentAction` from cache or the inner backend.
        """
        observation = context["observation"]
        prompt_hash = hash_prompt(self._system_prompt, observation)
        cached = self._cache.lookup(self._model, prompt_hash, self._temperature)
        if cached is not None:
            return cached
        action = self._backend.select_action(context)
        self._cache.store(self._model, prompt_hash, self._temperature, action)
        return action

    def reset(self) -> None:
        """Forward to the inner backend (stubs re-seed on reset)."""
        self._backend.reset()

    def cache_stats(self) -> dict[str, int]:
        """Aggregated hit/miss counters of the underlying cache."""
        return self._cache.stats()


def write_cache_manifest(cache_dir: str, manifest_path: str) -> dict[str, Any]:
    """Write the replay-verification manifest for a cache directory.

    Maps every entry's file name to its SHA-256 digest so reviewers
    can confirm a replayed cache is bit-identical
    (``sha256sum -c <manifest>`` style verification).

    Args:
        cache_dir: The cache directory to hash.
        manifest_path: Destination JSON file.

    Returns:
        The manifest dict written.
    """
    files: dict[str, str] = {}
    if os.path.isdir(cache_dir):
        for name in sorted(os.listdir(cache_dir)):
            if not name.endswith(".json"):
                continue
            path = os.path.join(cache_dir, name)
            try:
                with open(path, "rb") as f:
                    digest = hashlib.sha256(f.read()).hexdigest()
            except OSError:
                continue
            files[name] = digest
    manifest = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "total_entries": len(files),
        "files": files,
    }
    os.makedirs(os.path.dirname(manifest_path) or ".", exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    return manifest
