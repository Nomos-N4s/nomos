"""
Streamlit dashboard for the Governance Layer.

Provides a visual interface for exploring the formal model, replaying
Parliament decisions, viewing benchmark comparisons, and inspecting RL
training results.

Usage:
    ``streamlit run src/governance/dashboard/app.py``

Auto-detects Neo4j Aura if ``NEO4J_URI`` is present in ``.env``;
falls back to in-memory storage.
"""

import os
import sys

# Streamlit runs as a script, so relative imports fail.
# Add src/ to sys.path for absolute package imports.
_src = os.path.join(os.path.dirname(__file__), "..", "..")
if _src not in sys.path:
    sys.path.insert(0, os.path.abspath(_src))

import streamlit as st

from governance.ontology.memory_backend import MemoryBackend

st.set_page_config(
    page_title="Governance Layer — Formal Framework",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _neo4j_available() -> bool:
    """Auto-detect Neo4j: check if .env has NEO4J_URI."""
    env_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", ".env"
    )

    if not os.path.exists(env_path):
        return False

    with open(env_path) as f:
        for line in f:
            if line.strip().startswith("NEO4J_URI") and "=" in line:
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return True

    return False


@st.cache_resource
def get_ontology_backend():
    if _neo4j_available():
        try:
            from governance.ontology.neo4j_backend import Neo4jBackend

            backend = Neo4jBackend()
            backend.get_identity_vector()
            return backend

        except Exception as e:
            st.sidebar.warning(
                f"Neo4j connection failed: {e}. Falling back to memory."
            )
            return MemoryBackend()

    return MemoryBackend()


def main():
    backend = get_ontology_backend()

    st.sidebar.title("🏛️ Governance Layer")
    st.sidebar.caption("Formal Framework for Self-Governing AI")

    use_neo4j = "Neo4jBackend" in str(type(backend))
    backend_type = "Neo4j Aura" if use_neo4j else "Memory (local)"
    st.sidebar.info(f"**Ontology**: {backend_type}")

    # One global toggle for the dashboard
    show_statistics = st.sidebar.toggle(
        "Show Statistics",
        value=False,
        help="Display confidence intervals, effect sizes, and significance annotations.",
    )

    if not backend.get_identity_vector():
        backend.set_identity_vector([1.0, 1.0, 1.0, 0.95, 0.9])

    tab_names = [
        "📐 Formal Model",
        "🏛️ Parliament Live",
        "📊 Benchmarks",
        "🤖 RL Training",
    ]

    tab_model, tab_parliament, tab_benchmarks, tab_rl = st.tabs(tab_names)

    with tab_model:
        from governance.dashboard.model_tab import render_model_tab

        render_model_tab(backend)

    with tab_parliament:
        from governance.dashboard.parliament_tab import render_parliament_tab

        render_parliament_tab(backend)

    with tab_benchmarks:
        from governance.dashboard.benchmarks_tab import render_benchmarks_tab

        render_benchmarks_tab(
            backend,
            show_statistics=show_statistics,
        )

    with tab_rl:
        from governance.dashboard.rl_tab import render_rl_tab

        render_rl_tab(
            backend,
            show_statistics=show_statistics,
        )


if __name__ == "__main__":
    main()