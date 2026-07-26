"""
benchmarks_tab.py — Tab 3: Benchmark comparison.

Loads benchmark_results.json from results/ and displays:
  - Side-by-side reward comparison (±CI)
  - Violation counts
  - Statistical summary
"""

import json
import os
from typing import Any, Dict, List, Optional

from ..ontology.backend import OntologyBackend

import streamlit as st
import altair as alt
import pandas as pd
import numpy as np

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(__file__)))), "results")


def _load_benchmark() -> Optional[Dict[str, Any]]:
    path = os.path.join(RESULTS_DIR, "benchmark_results.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _load_prove_results() -> Optional[List[Dict]]:
    path = os.path.join(RESULTS_DIR, "prove_results.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f).get("predictions", [])


def _load_all_results() -> Dict[str, List[Any]]:
    results_dir = RESULTS_DIR
    data = {}
    if not os.path.isdir(results_dir):
        return data
    for f in os.listdir(results_dir):
        if f.startswith("results_") and f.endswith(".json"):
            name = f.replace("results_", "").replace(".json", "")
            path = os.path.join(results_dir, f)
            with open(path) as fh:
                data[name] = json.load(fh)
    return data


def _log_benchmark_to_backend(backend: Optional[OntologyBackend], benchmarks: Dict):
    if backend is None or not benchmarks:
        return
    try:
        for mode, data in benchmarks.items():
            backend.add_entity("benchmark", {
                "mode": mode,
                "avg_reward": data.get("avg_reward", 0),
                "std_reward": data.get("std_reward", 0),
                "avg_violations": data.get("avg_violations", 0),
                "n_seeds": data.get("n_seeds", 0),
            })
    except Exception:
        pass


def render_benchmarks_tab(backend: Optional[OntologyBackend] = None):
    st.header("📊 Benchmark Results")
    st.caption("Statistical comparison between governance and baselines.")

    benchmarks = _load_benchmark()
    _log_benchmark_to_backend(backend, benchmarks)

    if benchmarks is None:
        st.info(
            "No benchmark results found in `results/`. "
            "Run the benchmark on Colab first:\n\n"
            "```\npython -m src.governance.experiments.rl_adversary benchmark --seeds 42 43 44\n```\n\n"
            "Or upload `benchmark_results.json` to the `results/` directory."
        )
        st.divider()
        st.subheader("Prove.py Results (always available)")

        prove_results = _load_prove_results()
        if prove_results:
            prove_df = pd.DataFrame(prove_results)
            st.metric("Predictions PASS", f"{sum(prove_df['passed'])}/{len(prove_df)}")
            col1, col2 = st.columns(2)
            with col1:
                pass_df = prove_df[prove_df["passed"]]
                st.success(f"✅ {len(pass_df)} PASS")
                for _, r in pass_df.iterrows():
                    st.caption(f"**P{r['id']:02d}** ({r['chapter']} §{r['section']}): {r['description']}")
            with col2:
                fail_df = prove_df[~prove_df["passed"]]
                if len(fail_df) > 0:
                    st.error(f"❌ {len(fail_df)} FAIL")
                    for _, r in fail_df.iterrows():
                        st.caption(f"**P{r['id']:02d}**: {r['description']} — {r['evidence']}")
                else:
                    st.success("All predictions verified.")

        all_results = _load_all_results()
        if all_results:
            st.subheader("Training Results")
            for mode, data in all_results.items():
                eval_data = data.get("eval", {})
                with st.expander(f"{mode}"):
                    st.json(eval_data.get("metrics_per_episode", []))
        return

    gov = benchmarks.get("governance", {})
    no_gov = benchmarks.get("no_governance", {})

    col_g, col_n = st.columns(2)
    with col_g:
        st.metric("🏛️ Governance",
                  f"{gov.get('avg_reward', 0):.2f} ± {gov.get('std_reward', 0):.2f}",
                  help=f"Violations: {gov.get('avg_violations', 0):.2f}")
    with col_n:
        st.metric("⚡ No Governance",
                  f"{no_gov.get('avg_reward', 0):.2f} ± {no_gov.get('std_reward', 0):.2f}",
                  help=f"Violations: {no_gov.get('avg_violations', 0):.2f}")

    st.divider()

    comparison_df = pd.DataFrame([
        {"mode": "Governance", "avg_reward": gov.get("avg_reward", 0),
         "std_reward": gov.get("std_reward", 0),
         "avg_violations": gov.get("avg_violations", 0)},
        {"mode": "No Governance", "avg_reward": no_gov.get("avg_reward", 0),
         "std_reward": no_gov.get("std_reward", 0),
         "avg_violations": no_gov.get("avg_violations", 0)},
    ])

    col_chart, col_stats = st.columns(2)
    with col_chart:
        st.subheader("Reward Comparison")
        chart = alt.Chart(comparison_df).mark_bar().encode(
            x="mode:N",
            y="avg_reward:Q",
            color="mode:N",
        ).properties(height=300)
        error = alt.Chart(comparison_df).mark_errorbar(extent="ci").encode(
            x="mode:N",
            y=alt.Y("avg_reward:Q", scale=alt.Scale(zero=False)),
        )
        st.altair_chart(chart + error, use_container_width=True)

    with col_stats:
        st.subheader("Constraints")
        chart2 = alt.Chart(comparison_df).mark_bar().encode(
            x="mode:N",
            y="avg_violations:Q",
            color="mode:N",
        ).properties(height=300)
        st.altair_chart(chart2, use_container_width=True)

    st.divider()
    st.subheader("Per-Seed Details")
    for mode, data in benchmarks.items():
        with st.expander(f"{mode} ({data.get('n_seeds', 0)} seeds)"):
            evals = data.get("eval_results", [])
            if evals:
                evals_df = pd.DataFrame(evals)
                st.dataframe(evals_df)
