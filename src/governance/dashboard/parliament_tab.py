"""
Dashboard Tab 2: Parliament live viewer.

Loads a JSONL file from ``results/`` (written during eval) and replays it
step-by-step or auto-plays. Shows the grid world, Parliament member scores,
vetoes, and a reward/violations timeline.

Workflow:
  1. Train an agent on Colab (exports ``live_governance.jsonl``)
  2. Download the JSONL to ``results/``
  3. Open this tab, select the file, and replay

Real-world analogy:
    A flight data recorder (black box) replay. Every decision, score,
    and veto is recorded and can be replayed step by step to understand
    what the Parliament was thinking at each moment.
"""

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

from ..ontology.backend import OntologyBackend

_src = os.path.join(os.path.dirname(__file__), "..", "..")
if _src not in sys.path:
    sys.path.insert(0, os.path.abspath(_src))

import streamlit as st
import altair as alt
import pandas as pd
import numpy as np

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(__file__)))), "results")


def _find_log_files() -> List[str]:
    if not os.path.isdir(RESULTS_DIR):
        return []
    files = []
    for f in os.listdir(RESULTS_DIR):
        if f.startswith("live_") and f.endswith(".jsonl"):
            files.append(f)
    return sorted(files)


def _load_log(filepath: str) -> List[Dict]:
    full_path = os.path.join(RESULTS_DIR, filepath)
    if not os.path.exists(full_path):
        return []
    steps = []
    with open(full_path) as f:
        for line in f:
            line = line.strip()
            if line:
                steps.append(json.loads(line))
    return steps


def _render_grid(step_data: Dict, size: int = 10):
    grid = step_data.get("grid", [])
    pos = step_data.get("agent_pos", [0, 0])
    grid_size = max(len(grid), 1)
    grid_display = np.zeros((grid_size, grid_size, 3), dtype=np.uint8)
    for x in range(grid_size):
        for y in range(grid_size):
            if y < len(grid) and x < len(grid[y]):
                tile = grid[x][y]
                if tile == 0:
                    grid_display[x, y] = [240, 240, 230]
                elif tile == 1:
                    grid_display[x, y] = [46, 204, 113]
                elif tile == 2:
                    grid_display[x, y] = [231, 76, 60]
                elif tile == 3:
                    grid_display[x, y] = [100, 100, 100]
    if pos and len(pos) == 2:
        px, py = int(pos[0]), int(pos[1])
        if 0 <= px < grid_size and 0 <= py < grid_size:
            grid_display[px, py] = [52, 152, 219]
    st.image(grid_display.astype(np.uint8), width=300, caption=f"Step {step_data.get('step', '?')}")


def _render_scores(step_data: Dict):
    scores = step_data.get("scores", {})
    vetoed_by = step_data.get("vetoed_by", [])
    is_default = step_data.get("is_default", False)
    falsification_counts = step_data.get("falsification_counts", {})
    veto_count = step_data.get("veto_count", 0)

    if is_default:
        st.info("**Parliament blocked this action** — no proposal reached consensus")
        if falsification_counts:
            st.caption(f"Falsifications detected: {falsification_counts}")
        if veto_count:
            st.caption(f"Total vetoes this episode: {veto_count}")
        return

    if not scores:
        st.caption("No scores recorded")
        return

    score_df = pd.DataFrame({
        "member": list(scores.keys()),
        "score": list(scores.values()),
    })
    chart = alt.Chart(score_df).mark_bar().encode(
        x="member:N",
        y="score:Q",
        color=alt.condition(
            alt.datum.score > 0.5,
            alt.value("#2ecc71"),
            alt.value("#e74c3c"),
        ),
    ).properties(height=200, title="Parliament Member Scores")
    st.altair_chart(chart, use_container_width=True)


def _log_step_to_backend(backend: Optional[OntologyBackend], step: Dict):
    if backend is None:
        return
    try:
        eid = backend.add_entity("decision", {
            "step": step.get("step", 0),
            "action": step.get("action", -1),
            "reward": step.get("reward", 0.0),
            "violations": step.get("violations", 0),
            "is_default": step.get("is_default", False),
            "apples_collected": step.get("apples_collected", 0),
            "total_reward": step.get("total_reward", 0.0),
        })
        scores = step.get("scores", {})
        for member_id, score in scores.items():
            backend.add_entity("member_score", {
                "decision_id": eid,
                "member": member_id,
                "score": score,
            })
    except Exception:
        pass


def render_parliament_tab(backend: Optional[OntologyBackend] = None):
    st.header("🏛️ Parliament Live")
    st.caption("Replay an experiment episode step-by-step. Load a JSONL log file from `results/`.")

    log_files = _find_log_files()

    if not log_files:
        st.info(
            "No live log files found in `results/`. "
            "Train an agent on Colab first, then download the `live_*.jsonl` file."
        )
        if st.button("Load demo data (no file needed)"):
            st.session_state.parliament_steps = _generate_demo_steps()
            st.session_state.parliament_step_index = 0
            st.rerun()

        st.subheader("Or: Run a quick local demo")

        from governance.experiments.gym_env import GovernanceGridWorld
        env = GovernanceGridWorld(size=6, seed=42)
        obs, _ = env.reset()

        steps_to_run = st.slider("Steps to simulate", 5, 50, 10)
        if st.button("Run demo"):
            for i in range(steps_to_run):
                action = (env._pos[0] + env._pos[1]) % 4
                obs, reward, terminated, truncated, info =                 env.step(action)
                if terminated:
                    break
            st.session_state.parliament_steps = env.decision_history
            for step_data in env.decision_history:
                _log_step_to_backend(backend, step_data)
            st.session_state.parliament_step_index = 0
            st.rerun()
        return

    selected = st.selectbox("Select log file", log_files)
    if st.button("Reload log"):
        st.session_state.parliament_steps = _load_log(selected)
        st.session_state.parliament_step_index = 0
        st.rerun()

    if "parliament_steps" not in st.session_state:
        st.session_state.parliament_steps = _load_log(selected)
        st.session_state.parliament_step_index = 0

    steps = st.session_state.parliament_steps
    if not steps:
        st.warning("Log file is empty. Run an evaluation first.")
        return

    max_idx = len(steps) - 1
    idx = st.session_state.get("parliament_step_index", 0)
    idx = min(idx, max_idx)

    col_ctl, col_info = st.columns([1, 3])
    with col_ctl:
        step_back = st.button("◀ Back")
        step_fwd = st.button("Forward ▶")
        auto = st.button("Auto-play (1 step/sec)")

    if step_back and idx > 0:
        idx -= 1
    if step_fwd and idx < max_idx:
        idx += 1
    if auto:
        for i in range(idx, max_idx + 1):
            st.session_state.parliament_step_index = i
            time.sleep(0.5)
            st.rerun()

    st.session_state.parliament_step_index = idx
    step_data = steps[idx]
    _log_step_to_backend(backend, step_data)

    col_grid, col_vote = st.columns([1, 2])
    with col_grid:
        grid_data = step_data.get("grid", [])
        gs = len(grid_data) if grid_data else 6
        _render_grid(step_data, size=gs)
    with col_vote:
        _render_scores(step_data)

    reward = step_data.get("reward", 0.0)
    total = step_data.get("total_reward", 0.0)
    violations = step_data.get("violations", 0)
    veto_count = step_data.get("veto_count", 0)
    apples = step_data.get("apples_collected", 0)

    meta_cols = st.columns(5)
    meta_cols[0].metric("Step", f"{idx + 1}/{len(steps)}")
    meta_cols[1].metric("Reward", f"{reward:.1f}")
    meta_cols[2].metric("Total", f"{total:.1f}")
    meta_cols[3].metric("Apples", apples)
    meta_cols[4].metric("Violations", violations, delta_color="inverse")

    st.divider()
    st.caption("Reward / Violations Timeline")

    timeline_df = pd.DataFrame(steps[:idx + 1])
    if "total_reward" in timeline_df.columns and "violations" in timeline_df.columns:
        tl = timeline_df[["step", "total_reward", "violations"]].melt(
            id_vars="step", var_name="metric", value_name="value"
        )
        chart = alt.Chart(tl).mark_line().encode(
            x="step:Q",
            y="value:Q",
            color="metric:N",
        ).properties(height=150)
        st.altair_chart(chart, use_container_width=True)


def _generate_demo_steps() -> List[Dict]:
    steps = []
    pos = [0, 0]
    for i in range(20):
        pos = [(pos[0] + 1) % 6, (pos[1] + i) % 6]
        steps.append({
            "step": i + 1,
            "agent_pos": pos,
            "action": i % 4,
            "action_name": ["up", "down", "left", "right"][i % 4],
            "reward": 1.0 if i % 3 == 0 else 0.0,
            "total_reward": sum(1.0 for j in range(i + 1) if j % 3 == 0),
            "violations": sum(1 for j in range(i + 1) if j % 5 == 0),
            "veto_count": sum(1 for j in range(i + 1) if j % 4 == 0),
            "is_default": i % 4 == 0,
            "apples_collected": sum(1 for j in range(i + 1) if j % 3 == 0),
            "scores": {"reward": 0.7, "safety": 0.9, "integrity": 0.8,
                       "planning": 0.6, "curiosity": 0.3, "social": 0.7, "memory": 0.8},
            "vetoed_by": [],
            "falsification_counts": {},
            "grid": [[0] * 6 for _ in range(6)],
        })
    return steps
