"""
Structured JSON logging for the Nomos core — standard library only (#161).

Design goals (matching ``#161``):

- **Zero dependencies:** built on :mod:`logging` + :mod:`json` only. The
  algorithmic core stays dependency-free and deterministic.
- **Stable schema:** every record serializes to the same key order:
  ``timestamp``, ``level``, ``logger``, ``message``, then sorted structured
  extras, then ``exception`` (if any).
- **Deterministic:** timestamps are ISO-8601 UTC (``Z`` suffix), key order is
  fixed, and non-JSON-native values are coerced with ``str()`` — the same
  inputs always produce byte-identical log lines. Logging never feeds back
  into decision logic (see the determinism test in ``tests/test_observability.py``).
- **Secret redaction:** values under sensitive key names (API keys, tokens,
  passwords, private keys, authorization headers) and well-known secret
  shapes (OpenAI ``sk-...`` keys, ``Bearer`` tokens, AWS ``AKIA...`` keys,
  PEM private key blocks) are replaced with ``[REDACTED]`` everywhere in the
  output — message text, structured extras, and exception traces alike.
- **Two output modes:** compact JSON (one object per line — production/SIEM)
  and indented JSON (local debugging).

Usage::

    from nomos.observability import configure_logging

    configure_logging(fmt="json", level=logging.INFO)

    logger = logging.getLogger("nomos.speaker")
    logger.info("governance_decision", extra={"phase": "decision", "action": "shutdown"})

Output::

    {"timestamp": "2026-08-11T15:04:05.123Z", "level": "INFO", "logger": "nomos.speaker",
     "message": "governance_decision", "action": "shutdown", "phase": "decision"}
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import math
import re
import sys
import traceback
from typing import Any

__all__ = [
    "JsonFormatter",
    "RESERVED_EXTRA_KEYS",
    "configure_logging",
]


_RESERVED_EXTRA_KEYS = frozenset(
    {
        "timestamp",
        "level",
        "logger",
        "message",
        "exception",
    }
)
"""Key names the formatter owns; structured extras may never collide with them."""

RESERVED_EXTRA_KEYS = _RESERVED_EXTRA_KEYS
"""Public alias so callers can strip colliding keys before passing ``extra``."""

_STANDARD_RECORD_ATTRS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "taskName",
        "message",
    }
)
"""Structured extras are everything else in ``record.__dict__`` (and no more)."""

_SECRET_KEY_RE = re.compile(
    r"(?i).*(api[_-]?key|secret|passw(ord|d)?|pwd|token|private[_-]?key|"
    r"authorization|credential|bearer|access[_-]?key|signing[_-]?key|"
    r"session[_-]?id).*"
)
"""Key-name based redaction: any key containing one of these words is redacted."""

_SECRET_VALUE_PATTERNS = (
    # OpenAI-style API keys: sk-abcdef...
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    # Bearer tokens in header values / messages.
    re.compile(r"Bearer[ \t]+[A-Za-z0-9._~+/-]{10,}"),
    # AWS access key IDs.
    re.compile(r"AKIA[0-9A-Z]{16}"),
    # PEM private key blocks (multi-line, any key type).
    re.compile(
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
        re.DOTALL,
    ),
)
"""Value-shape based redaction applied to every string in the output."""

_REDACTED = "[REDACTED]"


def _redact_string(text: str) -> str:
    """Replace known secret shapes inside ``text`` with ``[REDACTED]``."""
    redacted = text
    for pattern in _SECRET_VALUE_PATTERNS:
        redacted = pattern.sub(_REDACTED, redacted)
    return redacted


def _redact_value(value: Any, key: str = "") -> Any:
    """Recursively redact ``value``; ``key`` triggers name-based redaction.

    The return value keeps the exact structural shape (dict/list scalars) so
    the log line stays parseable JSON.
    """
    if _SECRET_KEY_RE.match(key):
        return _REDACTED
    if isinstance(value, dict):
        return {k: _redact_value(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_value(v, "") for v in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value


def _safe(value: Any) -> Any:
    """Coerce ``value`` to a strictly JSON-serializable form.

    Only native JSON scalars/containers are kept as-is; everything else is
    converted deterministically via ``str()`` (datetimes become ISO-8601,
    non-finite floats become strings, custom objects become their repr).
    """
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    if isinstance(value, (set, frozenset)):
        return [_safe(v) for v in sorted(value, key=repr)]
    return str(value)


def _iso_utc_now() -> str:
    """Current time as ISO-8601 UTC with millisecond precision (``Z`` suffix)."""
    now = _dt.datetime.now(_dt.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class JsonFormatter(logging.Formatter):
    """Emit one deterministic JSON object per log record.

    Schema (fixed key order)::

        timestamp  ISO-8601 UTC, e.g. 2026-08-11T15:04:05.123Z
        level      record levelname (e.g. INFO)
        logger     record logger name (e.g. nomos.speaker)
        message    the formatted log message
        ...        every structured extra, sorted alphabetically
        exception  traceback text, only when an exception is attached

    Secrets are redacted at formatting time (both message text and nested
    structured values), so nothing sensitive reaches the output even if a
    caller forgets to scrub its own data.
    """

    def __init__(self, pretty: bool = False):
        """Args:
            pretty: indent the JSON with two spaces instead of one line.
        """
        super().__init__()
        self.pretty = pretty

    @staticmethod
    def _extra_fields(record: logging.LogRecord) -> dict[str, Any]:
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _STANDARD_RECORD_ATTRS and k not in _RESERVED_EXTRA_KEYS
        }
        return {k: extras[k] for k in sorted(extras)}

    @staticmethod
    def _exception_text(record: logging.LogRecord) -> str:
        if record.exc_info:
            return _redact_string(
                "".join(traceback.format_exception(*record.exc_info)).rstrip()
            )
        if record.exc_text:
            return _redact_string(record.exc_text)
        return ""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": _iso_utc_now(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(self._extra_fields(record))
        exception = self._exception_text(record)
        if exception:
            payload["exception"] = exception

        redacted = _redact_value(_safe(payload))

        if self.pretty:
            return json.dumps(redacted, ensure_ascii=False, indent=2)
        return json.dumps(redacted, ensure_ascii=False)


class _PlainFormatter(logging.Formatter):
    """Human-readable one-liner for local development (no JSON)."""

    def __init__(self) -> None:
        super().__init__("%(levelname)s %(name)s: %(message)s")


_FORMATS = {
    "json": JsonFormatter(pretty=False),
    "json-pretty": JsonFormatter(pretty=True),
    "plain": _PlainFormatter(),
}

_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


def configure_logging(
    fmt: str = "plain",
    level: str | int = logging.INFO,
    logger_names: tuple[str, ...] = ("nomos",),
) -> None:
    """Install the Nomos log handler on the given logger names (stdlib only).

    Args:
        fmt: One of ``"plain"`` (local dev), ``"json"`` (one object per
            line, production/SIEM), or ``"json-pretty"`` (indented JSON).
        level: Logging level: ``"DEBUG"``/``"INFO"``/``"WARNING"``/``"ERROR"``
            or a numeric ``logging`` constant.
        logger_names: Logger names to propagate through (default: only
            ``nomos`` — third-party loggers are left untouched).

    Returns:
        None. Idempotent: repeated calls replace the previous Nomos handler
        instead of stacking duplicates.
    """
    if isinstance(level, str):
        level = _LOG_LEVELS[level.upper()]
    if fmt not in _FORMATS:
        raise ValueError(f"unknown log format {fmt!r}; choose from {sorted(_FORMATS)}")

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_FORMATS[fmt])
    handler.setLevel(level)

    for name in logger_names:
        logger = logging.getLogger(name)
        logger.setLevel(level)
        for existing in list(logger.handlers):
            if getattr(existing, "_nomos_handler", False):
                logger.removeHandler(existing)
        handler._nomos_handler = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
        logger.propagate = True
