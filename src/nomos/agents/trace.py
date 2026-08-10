"""
Governance trace writer, viewer data structures, and HTML export.

Turns paired harness runs into an inspectable, replayable audit trail:

- ``results/agent/traces/{run_id}.jsonl`` — one JSON event per step per
  arm with the agent action, proposal, committee scores, decision, veto
  reason, contract lifecycle snapshot, and backend latency.
- In-memory *viewer data* — the canonical per-step paired structure
  consumed by the dashboard tab and the HTML export.
- ``{run_id}_viewer.html`` — a self-contained, dependency-free HTML
  viewer (timeline, veto heatmap, contract lifecycle, side-by-side
  replay) that needs no Streamlit server to review a run.

The event schema extends the required keys
``{step, arm, agent_action, proposal, committee_scores, decision,
veto_reason, contract_state, latency_ms}`` with ``observation`` — the
rendered state text — so the replay view can compare governed vs
ungoverned state at the same step.

Real-world analogy:
    The flight recorder of a governed agent. Each line is one timestamped
    instrument reading (step, arm), and the exported HTML is the
    accident-investigator's dashboard: the strip chart (timeline), the
    control-surfaces log (heatmap), the maintenance records (contracts),
    and the playback knob (replay).
"""

import json
import os
from typing import Any

from .harness import PairResult, StepLogEntry

#: Schema version stamped into every trace artifact.
TRACE_SCHEMA_VERSION = 1

#: Required keys of every JSONL trace event.
TRACE_KEYS = [
    "step",
    "arm",
    "agent_action",
    "proposal",
    "committee_scores",
    "decision",
    "veto_reason",
    "contract_state",
    "latency_ms",
    "observation",
]

#: Default output directory for trace artifacts.
TRACE_DIR = os.path.join("results", "agent", "traces")


# ----------------------------------------------------------------------
# Trace events
# ----------------------------------------------------------------------


def build_trace_event(entry: StepLogEntry) -> dict[str, Any]:
    """Convert one logged step into a trace event dict.

    Args:
        entry: One step of one arm from the harness log.

    Returns:
        A JSON-serialisable event dict (see :data:`TRACE_KEYS`).
    """
    veto_reason = None
    if entry.vetoed:
        veto_reason = (
            f"vetoed by {', '.join(entry.vetoers)}" if entry.vetoers else "default fallback"
        )
    return {
        "step": entry.step,
        "arm": entry.arm,
        "observation": entry.observation,
        "agent_action": {
            "action": str(entry.proposed_action),
            "action_index": entry.agent_action_index,
            "confidence": entry.confidence,
            "rationale": entry.rationale,
        },
        "proposal": (
            {
                "action": str(entry.proposed_action),
                "metadata": dict(entry.proposal_metadata),
            }
            if entry.arm == "governed"
            else None
        ),
        "committee_scores": {
            member_id: round(score, 3) for member_id, score in entry.committee_scores.items()
        },
        "decision": {
            "action": str(entry.decision_action),
            "is_default": entry.is_default,
            "vetoed": entry.vetoed,
        },
        "veto_reason": veto_reason,
        "contract_state": [dict(c) for c in entry.contract_state],
        "latency_ms": round(entry.select_latency * 1000.0, 3),
    }


def _events_for_pairs(pairs: list[PairResult]) -> list[dict[str, Any]]:
    """Flatten pairs into step-major, governed-then-ungoverned events."""
    events = []
    for pair in pairs:
        for governed_entry, ungoverned_entry in zip(pair.governed.log, pair.ungoverned.log):
            events.append(build_trace_event(governed_entry))
            events.append(build_trace_event(ungoverned_entry))
    return events


def write_trace_jsonl(pairs: list[PairResult], run_id: str, output_dir: str = TRACE_DIR) -> str:
    """Write one JSON event per line to ``{output_dir}/{run_id}.jsonl``.

    Args:
        pairs: All governed/ungoverned pairs of the run.
        run_id: Stable run identifier (e.g. ``"temptation_bank_seed0"``).
        output_dir: Output directory (default ``results/agent/traces``).

    Returns:
        The written file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{run_id}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for event in _events_for_pairs(pairs):
            f.write(json.dumps(event))
            f.write("\n")
    return path


def load_trace_jsonl(path: str) -> list[dict[str, Any]]:
    """Load trace events from a JSONL file, preserving line order.

    Args:
        path: Path to a trace JSONL file.

    Returns:
        The parsed events.
    """
    events = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events


# ----------------------------------------------------------------------
# Viewer data
# ----------------------------------------------------------------------


def build_viewer_data_from_events(events: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    """Build the canonical viewer structure from trace events.

    Args:
        events: Trace events (from :func:`load_trace_jsonl` or the
            harness logs).
        run_id: Stable run identifier.

    Returns:
        A dict with ``run_id``, ``schema_version``, ``num_steps``,
        ``members`` (ordered member ids), ``contract_ids`` (ordered),
        and ``steps`` — one entry per step with ``governed`` and
        ``ungoverned`` event dicts.
    """
    by_step: dict[int, dict[str, dict[str, Any]]] = {}
    members: list[str] = []
    contract_ids: list[str] = []
    for event in events:
        step_map = by_step.setdefault(event["step"], {})
        step_map[event["arm"]] = event
        if event["arm"] == "governed":
            for member_id in event["committee_scores"]:
                if member_id not in members:
                    members.append(member_id)
            for contract in event["contract_state"]:
                contract_id = contract["contract_id"]
                if contract_id not in contract_ids:
                    contract_ids.append(contract_id)

    steps = [
        {
            "step": step,
            "governed": step_map.get("governed"),
            "ungoverned": step_map.get("ungoverned"),
        }
        for step in sorted(by_step)
    ]
    return {
        "run_id": run_id,
        "schema_version": TRACE_SCHEMA_VERSION,
        "num_steps": len(steps),
        "members": members,
        "contract_ids": contract_ids,
        "steps": steps,
    }


def build_viewer_data(pairs: list[PairResult], run_id: str) -> dict[str, Any]:
    """Build the canonical viewer structure from paired harness runs.

    Args:
        pairs: All governed/ungoverned pairs of the run.
        run_id: Stable run identifier.

    Returns:
        The same structure as :func:`build_viewer_data_from_events`.
    """
    return build_viewer_data_from_events(_events_for_pairs(pairs), run_id)


# ----------------------------------------------------------------------
# Self-contained HTML viewer
# ----------------------------------------------------------------------

_VIEWER_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--fg:#1f2937;--bg:#f9fafb;--line:#e5e7eb;--veto:#b91c1c;--veto-bg:#fee2e2;--good-bg:#dcfce7;--mid-bg:#fef3c7;--bad-bg:#fee2e2;--muted:#6b7280;}
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--fg);background:var(--bg);margin:0;padding:24px;}
h1{font-size:1.4rem;margin:0 0 4px;}
h2{font-size:1.05rem;margin:32px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px;}
.sub{color:var(--muted);font-size:.85rem;margin-bottom:16px;}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:8px;}
.cell{border:1px solid var(--line);border-radius:6px;padding:8px 10px;background:#fff;}
.cell .step-label{font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;}
.cell.veto{border-color:var(--veto);border-left:4px solid var(--veto);background:var(--veto-bg);}
.mono{font-family:ui-monospace,Consolas,monospace;font-size:.82rem;}
table.heat{border-collapse:collapse;font-size:.78rem;}
table.heat th,table.heat td{border:1px solid var(--line);padding:3px 6px;text-align:center;min-width:34px;}
table.heat th{background:#f3f4f6;}
.cell-good{background:var(--good-bg);}.cell-mid{background:var(--mid-bg);}.cell-bad{background:var(--bad-bg);}
.cell-veto{outline:2px solid var(--veto);}
.contract-events{border:1px solid var(--line);border-radius:6px;background:#fff;padding:8px 10px;margin-bottom:8px;}
#replay-slider{width:100%;}
.panel{border:1px solid var(--line);border-radius:6px;background:#fff;padding:10px;}
.panel .ob{white-space:pre-wrap;font-size:.8rem;background:#f3f4f6;border-radius:6px;padding:8px;margin-top:6px;}
footer{color:#9ca3af;font-size:.75rem;margin-top:32px;}
</style>
</head>
<body>
<h1>__TITLE__</h1>
<div class="sub" id="subtitle"></div>

<h2>Timeline</h2>
<div id="timeline"></div>

<h2>Veto heatmap (committee member x step)</h2>
<div id="heatmap"></div>

<h2>Contract lifecycle</h2>
<div id="contracts"></div>

<h2>Side-by-side replay</h2>
<div class="sub" id="replay-label"></div>
<input id="replay-slider" type="range" min="0" value="0">
<div class="grid">
  <div class="panel" id="replay-gov"></div>
  <div class="panel" id="replay-ung"></div>
</div>

<footer>Nomos — self-contained trace viewer (schema v__SCHEMA__)</footer>
<script id="trace-data" type="application/json">__DATA__</script>
<script>
"use strict";
const DATA = JSON.parse(document.getElementById("trace-data").textContent);

function esc(v){return String(v).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}

function agentText(ev){
  if(!ev){return "<div class='step-label'>no event</div>";}
  const aa = ev.agent_action, d = ev.decision;
  let html = "<div class='step-label'>step " + ev.step + " - " + ev.arm + "</div>";
  html += "<div class='mono'>agent: " + esc(aa.action) + " (idx " + aa.action_index + ", conf " + aa.confidence.toFixed(2) + ")</div>";
  html += "<div class='mono'>decision: " + esc(d.action) + (d.is_default ? " (default)" : "") + "</div>";
  if(ev.veto_reason){html += "<div class='mono' style='color:var(--veto)'>" + esc(ev.veto_reason) + "</div>";}
  if(ev.latency_ms){html += "<div class='mono'>latency: " + ev.latency_ms + " ms</div>";}
  return html;
}

function renderTimeline(){
  document.getElementById("timeline").innerHTML = DATA.steps.map(function(s){
    const cls = s.governed && s.governed.decision.vetoed ? " cell veto" : " cell";
    return "<div class='grid'><div class='" + cls + "'>" + agentText(s.governed) + "</div>"
         + "<div class='cell'>" + agentText(s.ungoverned) + "</div></div>";
  }).join("");
}

function scoreClass(v){return v < 0.4 ? "cell-bad" : v < 0.6 ? "cell-mid" : "cell-good";}

function renderHeatmap(){
  const wrap = document.getElementById("heatmap");
  if(!DATA.members.length){wrap.innerHTML = "<p>No governed-arm committee scores recorded.</p>";return;}
  let html = "<table class='heat'><tr><th>member / step</th>";
  DATA.steps.forEach(function(s){html += "<th>" + s.step + "</th>";});
  html += "</tr>";
  DATA.members.forEach(function(member){
    html += "<tr><th>" + esc(member) + "</th>";
    DATA.steps.forEach(function(s){
      const ev = s.governed, score = ev ? ev.committee_scores[member] : undefined;
      if(score === undefined){html += "<td>-</td>";return;}
      const veto = ev.vetoed && ev.veto_reason.indexOf(member) !== -1;
      html += "<td class='" + scoreClass(score) + (veto ? " cell-veto" : "") + "' title='step "
            + s.step + " " + member + ": " + score.toFixed(3) + (veto ? " (vetoed)" : "") + "'>"
            + score.toFixed(2) + "</td>";
    });
    html += "</tr>";
  });
  html += "</table><p class='sub'>Colour: score magnitude (green &gt;= 0.6, amber 0.4-0.6, red &lt; 0.4); red outline = this member vetoed.</p>";
  wrap.innerHTML = html;
}

function renderContracts(){
  const wrap = document.getElementById("contracts");
  if(!DATA.contract_ids.length){wrap.innerHTML = "<p>No Ulysses Contracts were registered in this run.</p>";return;}
  wrap.innerHTML = DATA.contract_ids.map(function(cid){
    const seen = {}, events = [];
    DATA.steps.forEach(function(s){
      const ev = s.governed; if(!ev){return;}
      ev.contract_state.forEach(function(c){
        if(c.contract_id !== cid){return;}
        if(seen[cid] !== c.state){events.push("step " + s.step + ": " + c.state);seen[cid] = c.state;}
      });
    });
    return "<div class='contract-events'><span class='mono'>" + esc(cid) + "</span> - "
         + (events.join(" &rarr; ") || "no state changes") + "</div>";
  }).join("");
}

function replayPanel(ev){
  if(!ev){return "<div class='panel'><div class='step-label'>no event</div></div>";}
  let html = "<div class='panel'><div class='step-label'>step " + ev.step + " - " + ev.arm + "</div>";
  html += agentText(ev);
  html += "<div class='ob'>" + esc(ev.observation) + "</div>";
  if(ev.proposal){html += "<div class='mono'>proposal metadata: " + esc(JSON.stringify(ev.proposal.metadata)) + "</div>";}
  if(Object.keys(ev.committee_scores).length){html += "<div class='mono'>scores: " + esc(JSON.stringify(ev.committee_scores)) + "</div>";}
  if(ev.contract_state.length){html += "<div class='mono'>contracts: " + esc(JSON.stringify(ev.contract_state)) + "</div>";}
  return html + "</div>";
}

function renderReplay(step){
  const s = DATA.steps[step];
  document.getElementById("replay-gov").innerHTML = replayPanel(s ? s.governed : null);
  document.getElementById("replay-ung").innerHTML = replayPanel(s ? s.ungoverned : null);
  document.getElementById("replay-label").textContent = "step " + step + " of " + (DATA.num_steps - 1);
}

function init(){
  document.getElementById("subtitle").textContent = "run " + DATA.run_id + " · schema v" + DATA.schema_version
    + " · " + DATA.num_steps + " steps";
  renderTimeline();
  renderHeatmap();
  renderContracts();
  const slider = document.getElementById("replay-slider");
  slider.max = Math.max(0, DATA.num_steps - 1);
  slider.addEventListener("input", function(){renderReplay(parseInt(slider.value, 10));});
  renderReplay(0);
}
document.addEventListener("DOMContentLoaded", init);
</script>
</body>
</html>
"""


def build_run_viewer_html(viewer_data: dict[str, Any], title: str | None = None) -> str:
    """Build the self-contained HTML document for viewer data.

    Args:
        viewer_data: From :func:`build_viewer_data` or
            :func:`build_viewer_data_from_events`.
        title: Page title (defaults to ``"Governance Trace — {run_id}"``).

    Returns:
        The complete HTML document as a string.
    """
    run_id = viewer_data.get("run_id", "run")
    title = title or f"Governance Trace — {run_id}"
    payload = json.dumps(viewer_data).replace("</", "<\\/")
    return (
        _VIEWER_TEMPLATE.replace("__TITLE__", title)
        .replace("__SCHEMA__", str(viewer_data.get("schema_version", TRACE_SCHEMA_VERSION)))
        .replace("__DATA__", payload)
    )


def write_run_viewer_html(
    pairs: list[PairResult],
    run_id: str,
    output_dir: str = TRACE_DIR,
    title: str | None = None,
) -> str:
    """Write the self-contained HTML viewer for a run.

    Args:
        pairs: All governed/ungoverned pairs of the run.
        run_id: Stable run identifier.
        output_dir: Output directory (default ``results/agent/traces``).
        title: Page title override.

    Returns:
        The written file path (``{output_dir}/{run_id}_viewer.html``).
    """
    viewer_data = build_viewer_data(pairs, run_id)
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{run_id}_viewer.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_run_viewer_html(viewer_data, title))
    return path
