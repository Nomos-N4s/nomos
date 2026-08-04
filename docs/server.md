---
title: "Health, readiness, and metrics endpoints"
description: "The /healthz, /readyz, and /metrics endpoints exposed by `runner serve`, and how they relate to the TEE watchdog and deadlock breaker."
---

# Server Endpoints

[#server-endpoints](#server-endpoints)

`runner serve` starts a small, read-only HTTP surface for operating the
Governance Layer in a long-running process — for example, behind a
Kubernetes liveness/readiness probe, or scraped by Prometheus. It is
strictly observability: the endpoints below never call
`speaker.run_governance_cycle`, and the decision path never imports this
module.

```
python -m src.governance.runner serve --host 127.0.0.1 --port 8000
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8000` | Bind port |
| `--config` | *(none)* | Path to a `.parliament` config file. Without it, `serve` builds the same example committee used by `runner speaker`. |
| `--heartbeat-timeout-ms` | `100.0` | TEE watchdog heartbeat timeout |
| `--deadlock-threshold` | `100` | Stalled cycles before the deadlock breaker trips |

## `GET /healthz` — liveness

[#healthz](#healthz)

Answers one question: *is the process alive and has the parliament
configuration been loaded?* This should almost never fail. If it does,
the orchestrator should restart the process — the parliament state failed
to build and nothing else here can recover that on its own.

```json
{"status": "ok", "parliament_loaded": true, "uptime_s": 12.4}
```

`200` when `parliament_loaded` is `true`, `503` otherwise.

## `GET /readyz` — readiness

[#readyz](#readyz)

Answers: *should traffic be routed to this process right now?* Unlike
`/healthz`, this can flip between `200` and `503` without a restart — it
just means "give it a moment." Four checks are reported individually:

- **speaker** — has a `SpeakerStateMachine` been built?
- **watchdog** — is the TEE heartbeat watchdog in its `NORMAL` state (not
  `HEARTBEAT_MISSED`, `DEADLOCKED`, or `COLD_BOOT`)?
- **deadlock_breaker** — has the deadlock breaker *not* tripped (fewer
  stalled cycles than its threshold)? This is the "deadlock-breaker
  status" the endpoint is required to reflect correctly.
- **backend** — does the ontology backend (in-memory or Neo4j) respond to
  a `ping()`?

```json
{
  "status": "not_ready",
  "checks": {
    "speaker": {"ok": true, "detail": "ready"},
    "watchdog": {"ok": false, "detail": "HEARTBEAT_MISSED"},
    "deadlock_breaker": {"ok": true, "detail": "stalled_cycles=0"},
    "backend": {"ok": true, "detail": "reachable"}
  }
}
```

`200` only when every check is `ok`; `503` otherwise, with the failing
check(s) visible in the body.

## `GET /metrics` — Prometheus exposition

[#metrics](#metrics)

Exposes the same signals as `/readyz`, in Prometheus text exposition
format, for scraping:

- `governance_parliament_loaded`
- `governance_uptime_seconds`
- `governance_watchdog_healthy`
- `governance_deadlock_stalled_cycles`
- `governance_cold_boots_total`
- `governance_backend_reachable`

This requires the optional `observability` extra:

```
pip install governance-layer[observability]
```

Without it, `/metrics` returns `503` with a plain-text message pointing
to the install command above, instead of crashing the server.

## Design notes

[#design-notes](#design-notes)

- These endpoints are only mounted by `runner serve` — they are not part
  of, and are never imported by, the deterministic decision path in
  `speaker.py`.
- `serve` doesn't run governance cycles itself, so nothing would
  otherwise feed the watchdog a heartbeat. A background thread sends
  heartbeats on the same cadence a live decision loop would, so `/readyz`
  reflects "the process is alive and responsive." A deployment that runs
  decisions in the same process should feed real cycle heartbeats into
  the watchdog instead.
