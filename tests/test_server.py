import json
import urllib.error
import urllib.request

import pytest

from src.nomos.ontology.memory_backend import MemoryBackend
from src.nomos.server import (
    ServerState,
    build_server,
    healthz_payload,
    metrics_payload,
    readyz_payload,
)
from src.nomos.tee.watchdog import DeadlockBreaker, WatchdogState, WatchdogTimer


def _default_state(**overrides) -> ServerState:
    state = ServerState(
        parliament_loaded=True,
        speaker=object(),  # any non-None sentinel; payload only checks `is not None`
        watchdog=WatchdogTimer(heartbeat_timeout_ms=1000.0),
        deadlock_breaker=DeadlockBreaker(threshold_cycles=5),
        backend=MemoryBackend(),
    )
    state.watchdog.heartbeat()
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


class TestHealthzPayload:
    def test_ok_when_parliament_loaded(self):
        state = _default_state()
        status, body = healthz_payload(state)
        assert status == 200
        assert body["status"] == "ok"
        assert body["parliament_loaded"] is True
        assert body["uptime_s"] >= 0

    def test_503_when_parliament_not_loaded(self):
        state = _default_state(parliament_loaded=False)
        status, body = healthz_payload(state)
        assert status == 503
        assert body["status"] == "not_ready"

    def test_liveness_ignores_speaker_and_watchdog(self):
        # /healthz is liveness only: it should not care about readiness deps.
        state = _default_state(speaker=None, watchdog=None, backend=None)
        status, _ = healthz_payload(state)
        assert status == 200


class TestReadyzPayload:
    def test_ready_when_everything_healthy(self):
        state = _default_state()
        status, body = readyz_payload(state)
        assert status == 200
        assert body["status"] == "ready"
        assert body["checks"]["speaker"]["ok"] is True
        assert body["checks"]["watchdog"]["ok"] is True
        assert body["checks"]["deadlock_breaker"]["ok"] is True
        assert body["checks"]["backend"]["ok"] is True

    def test_not_ready_when_speaker_missing(self):
        state = _default_state(speaker=None)
        status, body = readyz_payload(state)
        assert status == 503
        assert body["checks"]["speaker"]["ok"] is False

    def test_not_ready_when_watchdog_missing_heartbeat(self):
        watchdog = WatchdogTimer(heartbeat_timeout_ms=1.0)
        watchdog._last_heartbeat -= 1.0  # force elapsed time past the timeout
        state = _default_state(watchdog=watchdog)
        status, body = readyz_payload(state)
        assert status == 503
        assert body["checks"]["watchdog"]["ok"] is False
        assert body["checks"]["watchdog"]["detail"] == WatchdogState.HEARTBEAT_MISSED.name

    def test_reflects_deadlock_breaker_state(self):
        """Acceptance criterion: readiness reflects deadlock-breaker state."""
        breaker = DeadlockBreaker(threshold_cycles=2)
        breaker.record_cycle(decision_produced=False)
        breaker.record_cycle(decision_produced=False)
        assert breaker.is_deadlocked

        state = _default_state(deadlock_breaker=breaker)
        status, body = readyz_payload(state)
        assert status == 503
        assert body["checks"]["deadlock_breaker"]["ok"] is False
        assert "stalled_cycles=2" in body["checks"]["deadlock_breaker"]["detail"]

    def test_not_ready_when_deadlock_breaker_missing(self):
        # Fails closed: an unconfigured deadlock breaker is not ready.
        state = _default_state(deadlock_breaker=None)
        status, body = readyz_payload(state)
        assert status == 503
        assert body["checks"]["deadlock_breaker"]["ok"] is False
        assert body["checks"]["deadlock_breaker"]["detail"] == ("deadlock breaker not configured")

    def test_ready_again_after_deadlock_breaker_reset(self):
        breaker = DeadlockBreaker(threshold_cycles=2)
        breaker.record_cycle(decision_produced=False)
        breaker.record_cycle(decision_produced=False)
        breaker.reset()

        state = _default_state(deadlock_breaker=breaker)
        status, body = readyz_payload(state)
        assert status == 200
        assert body["checks"]["deadlock_breaker"]["ok"] is True

    def test_not_ready_when_backend_missing(self):
        state = _default_state(backend=None)
        status, body = readyz_payload(state)
        assert status == 503
        assert body["checks"]["backend"]["ok"] is False

    def test_not_ready_when_backend_ping_raises(self):
        class BrokenBackend(MemoryBackend):
            def ping(self):
                raise RuntimeError("connection refused")

        state = _default_state(backend=BrokenBackend())
        status, body = readyz_payload(state)
        assert status == 503
        assert body["checks"]["backend"]["ok"] is False
        assert "connection refused" in body["checks"]["backend"]["detail"]


class TestMetricsPayload:
    def test_returns_prometheus_exposition_format(self):
        pytest.importorskip("prometheus_client")
        state = _default_state()
        status, content_type, body = metrics_payload(state)
        assert status == 200
        assert "text/plain" in content_type
        assert "governance_parliament_loaded" in body
        assert "governance_watchdog_healthy" in body
        assert "governance_deadlock_stalled_cycles" in body
        assert "governance_backend_reachable" in body

    def test_503_stub_when_prometheus_client_absent(self, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "prometheus_client":
                raise ImportError("simulated: extra not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        state = _default_state()
        status, content_type, body = metrics_payload(state)
        assert status == 503
        assert "text/plain" in content_type
        assert "observability" in body
        assert "pip install" in body


class TestLiveServer:
    """Acceptance criterion: start server, probe endpoints."""

    @pytest.fixture
    def server(self):
        state = _default_state()
        srv = build_server(state, host="127.0.0.1", port=0)  # port=0 -> OS picks a free port
        import threading

        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        try:
            yield srv
        finally:
            srv.shutdown()
            srv.server_close()
            thread.join(timeout=2)

    def _get(self, server, path):
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_healthz_probe(self, server):
        status, body = self._get(server, "/healthz")
        assert status == 200
        assert body["status"] == "ok"

    def test_readyz_probe(self, server):
        status, body = self._get(server, "/readyz")
        assert status == 200
        assert body["status"] == "ready"

    def test_unknown_path_is_404(self, server):
        status, body = self._get(server, "/nope")
        assert status == 404
        assert body["error"] == "not found"

    def test_metrics_probe_responds(self, server):
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/metrics"
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                status = resp.status
        except urllib.error.HTTPError as e:
            status = e.code
        # 200 if prometheus_client is installed, 503 with a clear message if not.
        assert status in (200, 503)
