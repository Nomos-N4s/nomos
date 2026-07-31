"""
Dashboard Tab 5: Agent trace viewer.

Loads trace JSONL files from ``results/agent/traces/`` produced by
``write_trace_jsonl`` and renders:

- Timeline view with arm comparison and veto highlighting
- Veto heatmap (committee member x step, colour-coded by score)
- Contract lifecycle trace (PROPOSED -> ENACTED -> ACTIVE / ...)
- Side-by-side replay (governed vs ungoverned at the same step)
- Self-contained HTML export for review without a Streamlit server

Real-world analogy:
    The flight recorder playback screen. Pick a recording (run), scrub
    through the timeline, watch which control surfaces (committee
    members) intervened, and export the black-box readout for the
    investigators.
"""

import os

import altair as alt
import pandas as pd
import streamlit as st

from ..agents.trace import (
    TRACE_SCHEMA_VERSION,
    build_run_viewer_html,
    build_viewer_data_from_events,
    load_trace_jsonl,
)

TRACES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "results",
    "agent",
    "traces",
)


def _trace_files() -> list[str]:
    """Sorted list of trace JSONL files in the traces directory."""
    if not os.path.isdir(TRACES_DIR):
        return []
    return sorted(
        os.path.join(TRACES_DIR, name) for name in os.listdir(TRACES_DIR) if name.endswith(".jsonl")
    )


def _load_run(path: str) -> tuple[str, dict]:
    """Load a trace file into viewer data."""
    run_id = os.path.splitext(os.path.basename(path))[0]
    events = load_trace_jsonl(path)
    return run_id, build_viewer_data_from_events(events, run_id)


def _events_dataframe(viewer: dict) -> pd.DataFrame:
    """Condensed per-event rows for the timeline table."""
    rows = []
    for step in viewer["steps"]:
        for arm in ("governed", "ungoverned"):
            event = step[arm]
            if event is None:
                continue
            rows.append(
                {
                    "step": event["step"],
                    "arm": event["arm"],
                    "agent_action": event["agent_action"]["action"],
                    "decision": event["decision"]["action"],
                    "vetoed": event["decision"]["vetoed"],
                    "veto_reason": event["veto_reason"] or "",
                    "latency_ms": event["latency_ms"],
                }
            )
    return pd.DataFrame(rows)


def _scores_dataframe(viewer: dict) -> pd.DataFrame:
    """Member x step committee scores for the heatmap."""
    rows = []
    for step in viewer["steps"]:
        event = step["governed"]
        if event is None:
            continue
        for member_id, score in event["committee_scores"].items():
            rows.append({"member": member_id, "step": step["step"], "score": score})
    return pd.DataFrame(rows)


def _contracts_dataframe(viewer: dict) -> pd.DataFrame:
    """Contract lifecycle rows (state changes only)."""
    rows = []
    seen: dict[str, str] = {}
    for step in viewer["steps"]:
        event = step["governed"]
        if event is None:
            continue
        for contract in event["contract_state"]:
            contract_id = contract["contract_id"]
            if seen.get(contract_id) != contract["state"]:
                rows.append(
                    {
                        "step": step["step"],
                        "contract": contract_id,
                        "state": contract["state"],
                        "restricted_indices": contract["restricted_indices"],
                        "timelock_blocks": contract["timelock_blocks"],
                    }
                )
                seen[contract_id] = contract["state"]
    return pd.DataFrame(rows)


def _render_timeline(viewer: dict) -> None:
    st.subheader("Timeline")
    events = _events_dataframe(viewer)
    if events.empty:
        st.info("This trace contains no events.")
        return
    only_vetoes = st.checkbox("Show vetoed steps only", key="trace_veto_filter")
    if only_vetoes:
        events = events[events["vetoed"]]
    st.dataframe(events, use_container_width=True, hide_index=True)


def _render_heatmap(viewer: dict) -> None:
    st.subheader("Veto heatmap (committee member x step)")
    scores = _scores_dataframe(viewer)
    if scores.empty:
        st.info("No governed-arm committee scores in this trace.")
        return
    chart = (
        alt.Chart(scores)
        .mark_rect()
        .encode(
            x=alt.X("step:O", title="Step"),
            y=alt.Y("member:N", title="Committee member"),
            color=alt.Color(
                "score:Q",
                title="Score",
                scale=alt.Scale(
                    scheme="redyellowgreen",
                    domain=[-1.0, 0.0, 1.0],
                ),
            ),
            tooltip=["step", "member", "score"],
        )
        .properties(height=max(80, 28 * len(viewer["members"])))
    )
    st.altair_chart(chart, use_container_width=True)
    st.caption("Red = score below typical veto thresholds; green = strong support.")


def _render_contracts(viewer: dict) -> None:
    st.subheader("Contract lifecycle")
    contracts = _contracts_dataframe(viewer)
    if contracts.empty:
        st.info("No Ulysses Contracts were registered in this run.")
        return
    st.dataframe(contracts, use_container_width=True, hide_index=True)


def _render_replay(viewer: dict) -> None:
    st.subheader("Side-by-side replay")
    num_steps = viewer["num_steps"]
    if num_steps == 0:
        st.info("No steps to replay.")
        return
    step_index = st.slider("Step", 0, num_steps - 1, 0, key="trace_replay_slider")
    step = viewer["steps"][step_index]
    col_gov, col_ung = st.columns(2)
    with col_gov:
        st.markdown("**Governed**")
        if step["governed"] is not None:
            st.json(step["governed"])
        else:
            st.caption("No governed event.")
    with col_ung:
        st.markdown("**Ungoverned**")
        if step["ungoverned"] is not None:
            st.json(step["ungoverned"])
        else:
            st.caption("No ungoverned event.")


def _render_export(run_id: str, viewer: dict) -> None:
    st.subheader("Export")
    html = build_run_viewer_html(viewer)
    st.download_button(
        "Download self-contained HTML viewer",
        html,
        file_name=f"{run_id}_viewer.html",
        mime="text/html",
        key="trace_html_export",
    )
    st.caption(
        "The HTML file embeds all trace data — no Streamlit server needed to review the run."
    )


def render_agent_tab(backend=None) -> None:
    """Render the agent trace viewer tab.

    Args:
        backend: Ontology backend (accepted for tab-signature
            compatibility; traces are read from local files).
    """
    st.header("🧭 Agent Trace Viewer")
    st.caption("Inspect governed vs ungoverned runs step by step.")

    trace_files = _trace_files()
    if not trace_files:
        st.info(
            "No traces found in `results/agent/traces/`. Run a harness comparison and "
            "call `write_trace_jsonl(pairs, run_id)` to produce them."
        )
        return

    selected = st.selectbox("Trace file", trace_files, format_func=os.path.basename)
    run_id, viewer = _load_run(selected)

    st.markdown(
        f"**Run:** `{run_id}` — {viewer['num_steps']} steps, "
        f"{len(viewer['members'])} committee members, "
        f"schema v{viewer.get('schema_version', TRACE_SCHEMA_VERSION)}"
    )

    _render_timeline(viewer)
    st.divider()
    _render_heatmap(viewer)
    st.divider()
    _render_contracts(viewer)
    st.divider()
    _render_replay(viewer)
    st.divider()
    _render_export(run_id, viewer)
