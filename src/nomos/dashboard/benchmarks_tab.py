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
import altair as alt
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


def _generate_benchmark_summary(benchmarks: dict[str, Any] | None) -> str:
    """
    Generate a natural language summary of benchmark results.
    """

    if benchmarks is None:
        return "No benchmark results available."

    try:
        aggregates = benchmarks.get("aggregates", [])

        if not aggregates:
            return "No benchmark aggregates available."

        df = pd.DataFrame(aggregates)

        required_columns = [
            "strategy",
            "mean_reward",
            "mean_violations",
        ]

        if not all(column in df.columns for column in required_columns):
            return "Incomplete benchmark results."

        governance = df[df["strategy"].str.lower() == "governance"]
        baselines = df[df["strategy"].str.lower() != "governance"]

        if governance.empty or baselines.empty:
            return "Insufficient data to compare governance and baseline strategies."

        summary_lines = []
        scenarios = sorted(set(governance["scenario"]) & set(baselines["scenario"]))

        for scenario in scenarios:
            gov_row = governance[governance["scenario"] == scenario]
            base_rows = baselines[baselines["scenario"] == scenario]

            if gov_row.empty or base_rows.empty:
                continue

            gov_reward = gov_row["mean_reward"].mean()
            gov_violations = gov_row["mean_violations"].mean()

            best_base = base_rows.loc[base_rows["mean_reward"].idxmax()]
            delta = gov_reward - best_base["mean_reward"]

            summary_lines.append(
                f"In {scenario}, governance achieved {gov_reward:.2f} reward "
                f"({gov_violations:.2f} avg. violations), a delta of {delta:+.2f} "
                f"versus the best baseline ({best_base['strategy']}: "
                f"{best_base['mean_reward']:.2f})."
            )

        if not summary_lines:
            return "Insufficient data to compare governance and baseline strategies."

        return " ".join(summary_lines)

    except Exception as e:
        st.warning(f"Benchmark summary generation failed: {e}")
        return "Unable to generate benchmark summary."


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


def _format_optional_metric(value: Any) -> str:
    if pd.isna(value):
        return "N/A"
    return str(value)


def _render_benchmark_comparison(rows: list[dict]):
    row_a, row_b = rows
    label_a = f"{row_a['strategy']} ({row_a['scenario']})"
    label_b = f"{row_b['strategy']} ({row_b['scenario']})"

    st.subheader(f"Comparison: {label_a} vs {label_b}")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(label_a, f"Reward: {row_a['reward']}")
        st.caption(
            f"Violations: {_format_optional_metric(row_a['violations'])} · "
            f"Deadlocks: {_format_optional_metric(row_a['deadlocks'])}"
        )

    with col2:
        st.metric(label_b, f"Reward: {row_b['reward']}")
        st.caption(
            f"Violations: {_format_optional_metric(row_b['violations'])} · "
            f"Deadlocks: {_format_optional_metric(row_b['deadlocks'])}"
        )

    st.divider()
    st.subheader("Δ Difference")

    diff_df = pd.DataFrame(
        {
            "Metric": ["Reward", "Violations", "Deadlocks"],
            label_a: [
                row_a["reward"],
                row_a["violations"],
                row_a["deadlocks"],
            ],
            label_b: [
                row_b["reward"],
                row_b["violations"],
                row_b["deadlocks"],
            ],
        }
    )

    diff_df[label_a] = pd.to_numeric(
        diff_df[label_a],
        errors="coerce",
    )
    diff_df[label_b] = pd.to_numeric(
        diff_df[label_b],
        errors="coerce",
    )

    diff_df["Δ"] = diff_df.apply(
        lambda row: (
            row[label_a] - row[label_b]
            if pd.notna(row[label_a]) and pd.notna(row[label_b])
            else None
        ),
        axis=1,
    )

    bar = (
        alt.Chart(diff_df)
        .mark_bar()
        .encode(
            x=alt.X("Metric:N"),
            y=alt.Y("Δ:Q", title=f"Δ ({label_a} − {label_b})"),
            color=alt.condition(
                alt.datum.Δ > 0,
                alt.value("#2ca02c"),
                alt.value("#d62728"),
            ),
            tooltip=["Metric", "Δ"],
        )
        .properties(height=250)
    )

    st.altair_chart(bar, use_container_width=True)
    st.dataframe(
        diff_df,
        use_container_width=True,
        hide_index=True,
    )

def render_benchmarks_tab(backend: OntologyBackend | None = None):
    st.header("📊 Benchmark Results")
    st.caption("Statistical comparison between governance and baselines.")

    benchmarks = _load_benchmark()
    signature = None
    path = os.path.join(RESULTS_DIR, "benchmark_results.json")
    if benchmarks is not None and os.path.exists(path):
        signature = f"{os.path.getmtime(path)}:{len(benchmarks.get('aggregates', []))}"
    if signature is not None and signature != st.session_state.get("bench_logged_sig"):
        _log_benchmark_to_backend(backend, benchmarks)
        st.session_state["bench_logged_sig"] = signature

    if benchmarks is not None:
        # Auto-generated dashboard summary
        benchmark_summary = _generate_benchmark_summary(benchmarks)

        st.subheader("📌 Summary")
        st.write(benchmark_summary)

        if st.button("📋 Copy Summary", key="benchmark_copy_summary"):
            st.code(benchmark_summary, language="text")

    if benchmarks is None:
        st.info(
            "No benchmark results found in `results/`. "
            "Run the benchmark on Colab first:\n\n"
            "```\npython -m src.nomos.experiments.rl_adversary benchmark --seeds 42 43 44\n```\n\n"
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
                    st.success("All prediction tests pass (Python asserts).")

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

    show_statistics = st.checkbox(
        "Show confidence intervals",
        value=True,
    )

    st.subheader("Per-Scenario Results")

    selected_rows = []

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

            display = display.copy()
            display.insert(0, "Compare", False)

            edited = st.data_editor(
                display,
                key=f"benchmark_compare_{scenario}",
                column_config={
                    "Compare": st.column_config.CheckboxColumn(
                        required=True
                    )
                },
                disabled=[c for c in display.columns if c != "Compare"],
                use_container_width=True,
                hide_index=True,
            )

            picked = edited[edited["Compare"]]

            for _, row in picked.iterrows():
                selected_rows.append(
                    {
                        "scenario": scenario,
                        "strategy": row["Strategy"],
                        "reward": row["Reward"],
                        "violations": row.get("Violations", pd.NA),
                        "deadlocks": row.get("Deadlocks", pd.NA),
                    }
                )

    if selected_rows:
        col_a, col_b = st.columns([4, 1])

        with col_b:
            if st.button(
                "Reset comparison",
                key="benchmark_compare_reset",
            ):
                for scenario in agg_df["scenario"].unique():
                    st.session_state.pop(
                        f"benchmark_compare_{scenario}",
                        None,
                    )
                st.rerun()

    if len(selected_rows) == 2:
        st.divider()
        _render_benchmark_comparison(selected_rows)

    elif len(selected_rows) > 2:
        st.warning(
            f"{len(selected_rows)} rows selected — please select exactly 2 to compare."
        )

    st.divider()
    st.subheader("Aggregate Comparison")

    pivot = agg_df.pivot_table(
        index="strategy",
        columns="scenario",
        values="mean_reward",
        aggfunc="first",
    )

    st.dataframe(
        pivot,
        use_container_width=True,
    )

    effect_sizes = benchmarks.get("effect_sizes", [])

    if effect_sizes:
        st.divider()
        st.subheader("Effect Sizes (Cohen's d)")

        es_df = pd.DataFrame(effect_sizes)

        st.dataframe(
            es_df,
            use_container_width=True,
            hide_index=True,
        )