"""
Health, readiness, and Prometheus metrics endpoints for ``runner serve``.

These endpoints exist only for the long-lived server process started by
``python -m src.nomos.runner serve``. They are read-only observability
surfaces and are never imported by, or wired into, the deterministic
decision path (:mod:`.speaker`). A load balancer or Kubernetes probe talks
to this module; the Speaker never does.

Endpoints:
    ``GET /healthz`` — liveness: is the process alive and has the
        parliament configuration been loaded? This should almost never
        fail; if it does, the orchestrator should restart the pod.
    ``GET /readyz`` — readiness: is the Speaker initialised, is the TEE
        watchdog heartbeat healthy (no deadlock), and is the ontology
        backend reachable? This can flip to "not ready" and back without
        a restart — it just pauses traffic.
    ``GET /metrics`` — Prometheus exposition format, produced via the
        optional ``observability`` extra (``prometheus-client``). If the
        extra isn't installed, this returns ``503`` with a clear message
        instead of crashing the server.

Real-world analogy:
    The health/ready/metrics trio every Kubernetes-deployed service
    exposes: liveness restarts a stuck pod, readiness controls whether
    traffic is routed to it, and metrics feed a monitoring dashboard.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .ontology.backend import OntologyBackend
from .speaker import SpeakerStateMachine
from .tee.watchdog import DeadlockBreaker, WatchdogState, WatchdogTimer


@dataclass
class ServerState:
    """Read-mostly state polled by the health endpoints.

    Populated once when ``runner serve`` starts. The decision path may
    update ``watchdog`` (via heartbeats) and ``deadlock_breaker`` (via
    ``record_cycle``) as it runs, but nothing here is required for, or
    touched by, an actual governance decision.

    Attributes:
        parliament_loaded: True once the parliament configuration (members,
            contracts, thresholds) has been parsed and built successfully.
        speaker: The running :class:`~.speaker.SpeakerStateMachine`, or
            ``None`` if it hasn't been built yet.
        watchdog: The TEE heartbeat watchdog.
        deadlock_breaker: The TEE deadlock breaker.
        backend: The ontology storage backend (memory or Neo4j).
        started_at: Unix timestamp when the server process started.
    """

    parliament_loaded: bool = False
    speaker: SpeakerStateMachine | None = None
    watchdog: WatchdogTimer | None = None
    deadlock_breaker: DeadlockBreaker | None = None
    backend: OntologyBackend | None = None
    started_at: float = field(default_factory=time.time)

    @property
    def uptime_seconds(self) -> float:
        """Seconds since this state (and thus the server) was created."""
        return time.time() - self.started_at


def _watchdog_check(state: ServerState) -> tuple[bool, str]:
    """Return (is_healthy, detail) for the TEE heartbeat watchdog."""
    if state.watchdog is None:
        return False, "watchdog not configured"
    wd_state = state.watchdog.check()
    healthy = wd_state == WatchdogState.NORMAL
    return healthy, wd_state.name


def _deadlock_check(state: ServerState) -> tuple[bool, str]:
    """Return (is_healthy, detail) for the deadlock breaker.

    Fails closed: an unconfigured deadlock breaker is a readiness failure,
    mirroring ``_watchdog_check`` and ``_backend_check``.
    """
    if state.deadlock_breaker is None:
        return False, "deadlock breaker not configured"
    healthy = not state.deadlock_breaker.is_deadlocked
    detail = f"stalled_cycles={state.deadlock_breaker.stalled_cycles}"
    return healthy, detail


def _backend_check(state: ServerState) -> tuple[bool, str]:
    """Return (is_healthy, detail) for the ontology backend."""
    if state.backend is None:
        return False, "backend not configured"
    try:
        reachable = state.backend.ping()
    except Exception as exc:  # noqa: BLE001 - any backend failure means not-ready
        return False, f"ping raised: {exc}"
    return bool(reachable), "reachable" if reachable else "unreachable"


def healthz_payload(state: ServerState) -> tuple[int, dict[str, Any]]:
    """Build the ``/healthz`` (liveness) response: (status_code, body)."""
    ok = state.parliament_loaded
    body = {
        "status": "ok" if ok else "not_ready",
        "parliament_loaded": state.parliament_loaded,
        "uptime_s": round(state.uptime_seconds, 3),
    }
    return (200 if ok else 503), body


def readyz_payload(state: ServerState) -> tuple[int, dict[str, Any]]:
    """Build the ``/readyz`` (readiness) response: (status_code, body)."""
    speaker_ready = state.speaker is not None
    watchdog_ok, watchdog_detail = _watchdog_check(state)
    deadlock_ok, deadlock_detail = _deadlock_check(state)
    backend_ok, backend_detail = _backend_check(state)

    checks = {
        "speaker": {
            "ok": speaker_ready,
            "detail": "ready" if speaker_ready else "not initialised",
        },
        "watchdog": {"ok": watchdog_ok, "detail": watchdog_detail},
        "deadlock_breaker": {"ok": deadlock_ok, "detail": deadlock_detail},
        "backend": {"ok": backend_ok, "detail": backend_detail},
    }
    all_ok = all(c["ok"] for c in checks.values())
    body = {"status": "ready" if all_ok else "not_ready", "checks": checks}
    return (200 if all_ok else 503), body


_METRICS_UNAVAILABLE_MESSAGE = (
    "Prometheus metrics are unavailable: the 'observability' extra is not "
    "installed.\nInstall it with: pip install nomos[observability]\n"
)


def metrics_payload(state: ServerState) -> tuple[int, str, str]:
    """Build the ``/metrics`` response: (status_code, content_type, body_text).

    Returns ``503`` with a plain-text explanation if ``prometheus-client``
    (the ``observability`` extra) is not installed, instead of raising.
    """
    try:
        from prometheus_client import (
            CONTENT_TYPE_LATEST,
            CollectorRegistry,
            Gauge,
            generate_latest,
        )
    except ImportError:
        return 503, "text/plain; charset=utf-8", _METRICS_UNAVAILABLE_MESSAGE

    registry = CollectorRegistry()

    def _gauge(name: str, doc: str, value: float):
        Gauge(name, doc, registry=registry).set(value)

    _gauge(
        "governance_parliament_loaded",
        "1 if parliament state is loaded, else 0",
        1 if state.parliament_loaded else 0,
    )
    _gauge("governance_uptime_seconds", "Process uptime in seconds", state.uptime_seconds)

    watchdog_ok, _ = _watchdog_check(state)
    _gauge(
        "governance_watchdog_healthy",
        "1 if the TEE heartbeat watchdog is healthy, else 0",
        1 if watchdog_ok else 0,
    )

    stalled = state.deadlock_breaker.stalled_cycles if state.deadlock_breaker else 0
    _gauge(
        "governance_deadlock_stalled_cycles",
        "Consecutive governance cycles without a decision",
        stalled,
    )
    cold_boots = state.deadlock_breaker.total_cold_boots if state.deadlock_breaker else 0
    _gauge("governance_cold_boots_total", "Total cold boots triggered", cold_boots)

    backend_ok, _ = _backend_check(state)
    _gauge(
        "governance_backend_reachable",
        "1 if the ontology backend is reachable, else 0",
        1 if backend_ok else 0,
    )

    return 200, CONTENT_TYPE_LATEST, generate_latest(registry).decode("utf-8")


def make_handler(state: ServerState) -> type[BaseHTTPRequestHandler]:
    """Build a ``BaseHTTPRequestHandler`` subclass bound to ``state``.

    A factory (rather than a module-level class) because
    ``http.server`` handlers are instantiated per-request by the server
    with no constructor hook for extra arguments — binding ``state`` via
    closure is the standard workaround.
    """

    class HealthHandler(BaseHTTPRequestHandler):
        server_version = "GovernanceHealthServer/1.0"

        def log_message(self, fmt: str, *args: Any) -> None:
            # Quiet by default; probes hit this endpoint frequently and
            # stdout logging would drown out real server output.
            pass

        def _write_json(self, status: int, body: dict[str, Any]) -> None:
            payload = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _write_text(self, status: int, content_type: str, body: str) -> None:
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802 - required name by http.server
            if self.path == "/healthz":
                status, body = healthz_payload(state)
                self._write_json(status, body)
            elif self.path == "/readyz":
                status, body = readyz_payload(state)
                self._write_json(status, body)
            elif self.path == "/metrics":
                status, content_type, body = metrics_payload(state)
                self._write_text(status, content_type, body)
            else:
                self._write_json(404, {"error": "not found"})

    return HealthHandler


def build_server(
    state: ServerState, host: str = "127.0.0.1", port: int = 8000
) -> ThreadingHTTPServer:
    """Construct (but do not run) a threaded HTTP server bound to ``state``.

    Callers should call ``.serve_forever()`` on the result, and
    ``.server_close()`` when done (see ``cmd_serve`` in ``runner.py``).
    """
    handler_cls = make_handler(state)
    return ThreadingHTTPServer((host, port), handler_cls)
