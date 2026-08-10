"""
OpenRouter model catalog verification.

Free-model pins can silently leave the ``:free`` tier — a pinned slug
that drops out of the catalog breaks a run mid-benchmark. This module
guards against that by verifying a model pin against OpenRouter's
official catalog (``https://openrouter.ai/api/v1/models``) *before* a
run starts, and — per project policy — rejects paid models outright.

The catalog is fetched once per process (module-level cache) and only
for ``openrouter:``-prefixed pins; other providers are skipped without
a network call.

Real-world analogy:
    Pre-flight fuel and registration check. The pilot verifies the
    aircraft is airworthy and the flight plan's aircraft type is
    valid *before* taxiing out — not halfway down the runway.
"""

import functools
import json
import urllib.request
from collections.abc import Callable
from typing import Any, Final

#: Official OpenRouter catalog endpoint.
MODELS_API_URL: Final[str] = "https://openrouter.ai/api/v1/models"

#: Models whose pricing object reports zero prompt cost (free tier).
_FREE_PROMPT_PRICES: Final[tuple[Any, ...]] = ("0", 0)

#: Seconds to wait for the catalog response.
CATALOG_TIMEOUT_S: Final[float] = 10.0


class ModelVerificationError(ValueError):
    """Raised when a model pin cannot be verified as available and free."""


def _fetch_models_json(url: str = MODELS_API_URL) -> dict[str, Any]:
    """Fetch and parse the live OpenRouter model catalog.

    Args:
        url: Catalog endpoint (overridable for tests).

    Returns:
        The parsed catalog JSON (``{"data": [...]}``).

    Raises:
        OSError: When the endpoint cannot be reached.
        ValueError: When the response is not valid JSON.
    """
    with urllib.request.urlopen(url, timeout=CATALOG_TIMEOUT_S) as response:
        return json.loads(response.read().decode("utf-8"))


@functools.lru_cache(maxsize=1)
def _load_catalog() -> dict[str, Any]:
    """Fetch the catalog once per process (lru-cached)."""
    return _fetch_models_json()


def _is_free(entry: dict[str, Any], slug: str) -> bool:
    """True when the entry is free per slug suffix or zero pricing."""
    if slug.endswith(":free"):
        return True
    price = entry.get("pricing", {}).get("prompt")
    return price in _FREE_PROMPT_PRICES


def verify_model_available(
    model: str,
    fetcher: Callable[[], dict[str, Any]] | None = None,
) -> None:
    """Verify an ``openrouter:`` model pin exists and is free.

    Non-OpenRouter pins (``ollama:...``, ``openai:...``) are skipped
    without a network call — the guard is about the project's
    OpenRouter free-tier policy.

    Args:
        model: Provider-prefixed model string.
        fetcher: Catalog fetcher (injectable for tests). Defaults to
            the live endpoint with a per-process cache.

    Raises:
        ModelVerificationError: When the catalog is unreachable, the
            pin is absent from it, or the pin resolves to a paid model.
    """
    if not model.startswith("openrouter:"):
        return
    slug = model.removeprefix("openrouter:")

    try:
        catalog = (fetcher or _load_catalog)()
    except (OSError, ValueError) as e:
        raise ModelVerificationError(
            f"cannot verify model pin {model!r}: OpenRouter catalog unreachable ({e}). "
            "Fix the network, then re-run."
        ) from e

    entries = {entry.get("id"): entry for entry in catalog.get("data", [])}
    entry = entries.get(slug)
    if entry is None:
        raise ModelVerificationError(
            f"model pin {model!r} not found in the OpenRouter catalog. "
            "The model may have left the free tier; update the pin or set "
            "GOVERNANCE_LLM_MODEL to a current one."
        )
    if not _is_free(entry, slug):
        price = entry.get("pricing", {}).get("prompt", "?")
        raise ModelVerificationError(
            f"model pin {model!r} is not free (prompt price ${price}/M tokens). "
            "Project policy is free models only; pick an OpenRouter :free variant."
        )
