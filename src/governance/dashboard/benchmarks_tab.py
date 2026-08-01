"""
Dashboard Tab 3: Benchmark comparison.

Loads ``benchmark_results.json`` from ``results/`` and displays:
- Side-by-side reward comparison with confidence intervals
- Violation counts per scenario-strategy
- Cohen's d effect sizes between governance and baselines
- Formal prediction verification (``prove.py``) — always available

Real-world analogy:
    A clinical trial results page. Each treatment arm (strategy) is shown
    with its outcome (reward), side effects (violations), and statistical
    significance (effect sizes).
"""

import json
import os
from typing import Any

import pandas as pd
import streamlit as st

from ..ontology.backend import OntologyBackend

RESULTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "results"
)


def _load_benchmark() -> dict[str, Any] | None:
    path = os.path.join(RESULTS_DIR, "benchmark_results.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _load_prove_results() -> list[dict] | None:
    path = os.path.join(RESULTS_DIR, "prove_results.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f).get("predictions", [])


def _load_all_results() -> dict[str, list[Any]]:
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


def _log_benchmark_to_backend(backend: OntologyBackend | None, benchmarks: dict):
    if backend is None or not benchmarks:
        return
    try:
        for item in benchmarks.get("aggregates", []):
            backend.add_entity(
                "benchmark",
                {
                    "strategy": item.get("strategy"),
                    "scenario": item.get("scenario"),
                    "mean_reward": item.get("mean_reward", 0),
                    "std_reward": item.get("std_reward", 0),
                    "mean_violations": item.get("mean_violations", 0),
                    "num_seeds": item.get("num_seeds", 0),
                },
            )
    except Exception:
        pass


def render_benchmarks_tab(
    backend: OntologyBackend | None = None,
    show_statistics: bool = False,
):
    st.header("📊 Benchmark Results")
    st.caption("Statistical comparison between governance and baselines.")

    if show_statistics:
     st.info(
        "Statistical summaries are enabled."
    )
     
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
                    st.caption(
                        f"**P{r['id']:02d}** ({r['chapter']} §{r['section']}): {r['description']}"
                    )
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

    aggregates = benchmarks.get("aggregates", [])
    if not aggregates:
        st.info("No aggregates found in benchmark data.")
        return

    agg_df = pd.DataFrame(aggregates)
    effect_sizes = benchmarks.get("effect_sizes", [])

    if show_statistics:
        st.subheader("📈 Summary Statistics")

        avg_reward = agg_df["mean_reward"].mean() if not agg_df.empty else None
        num_scenarios = len(agg_df["scenario"].unique())
        num_effect_sizes = len(effect_sizes)

        c1, c2, c3 = st.columns(3)
        c1.metric("Average Reward", f"{avg_reward:.2f}" if avg_reward is not None else "N/A")
        c2.metric("Scenarios", str(num_scenarios))
        c3.metric("Effect-size comparisons", str(num_effect_sizes))

        st.divider()

    st.subheader("Per-Scenario Results")
    for scenario in agg_df["scenario"].unique():
        sub = agg_df[agg_df["scenario"] == scenario]
        with st.expander(scenario, expanded=True):
            display = sub.rename(
                columns={
                    "strategy": "Strategy",
                    "mean_reward": "Reward",
                    "std_reward": "σ",
                    "mean_violations": "Violations",
                    "mean_deadlocks": "Deadlocks",
                    "num_seeds": "Seeds",
                }
            )
            if show_statistics:
                if "ci_lower" in display.columns and "ci_upper" in display.columns:
                    display["95% CI"] = (
                        display["ci_lower"].round(2).astype(str)
                        + " – "
                        + display["ci_upper"].round(2).astype(str)
                    )
            display = display.drop(
                columns=["ci_lower", "ci_upper"],
                errors="ignore",
            )
            st.dataframe(display, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Aggregate Comparison")
    pivot = agg_df.pivot_table(
        index="strategy",
        columns="scenario",
        values="mean_reward",
        aggfunc="first",
    )
    st.dataframe(pivot, use_container_width=True)

    if show_statistics:
        st.divider()
        st.subheader("📈 Statistical Analysis")

        if effect_sizes:
            es_df = pd.DataFrame(effect_sizes)

            def significance_stars(p):
                if pd.isna(p):
                    return "N/A"
                if p < 0.001:
                    return "***"
                if p < 0.01:
                    return "**"
                if p < 0.05:
                    return "*"
                return "ns"

            p_col = None
            for candidate in (
                "p_value_corrected",
                "p_value_holm",
                "p_value_raw",
            ):
                if candidate in es_df.columns:
                    p_col = candidate
                    break

            es_df["Significance"] = "N/A"
            if p_col:
                es_df["Significance"] = es_df[p_col].apply(significance_stars)

            if "significant" in es_df.columns:
                es_df["Significant"] = es_df["significant"].map(
                    {
                        True: "✅",
                        False: "❌",
                    }
                )

            columns = [
                c
                for c in (
                    "scenario",
                    "governance_vs",
                    "cohens_d",
                    "interpretation",
                    "Significance",
                    "Significant",
                )
                if c in es_df.columns
            ]

            st.dataframe(
                es_df[columns],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No statistical comparison data available.")