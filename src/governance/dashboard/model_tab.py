"""
model_tab.py — Tab 1: Formal model viewer.

Displays the I = <O, C_core, K, P> tuple with live values
from the ontology backend. Each component is expandable.
"""

import json
import streamlit as st
import altair as alt
import pandas as pd

from ..prove.predictions import ALL_PREDICTIONS
from ..prove.runner import run_all
from ..ontology.backend import OntologyBackend
from ..identity.core import IdentityCore, CoreCommitment, CommitmentType, CommitmentThreshold, EnforcementMode


def render_model_tab(backend: OntologyBackend):
    st.header(r"Formal Model $\mathcal{I} = \langle \mathcal{O}, \mathcal{C}_{\text{core}}, \mathcal{K}, \mathcal{P} \rangle$")
    st.caption("The Identity Layer tuple with live values from the ontology backend.")

    col1, col2, col3, col4 = st.columns(4)

    entities = backend.get_entities_by_type("action")
    identity_vec = backend.get_identity_vector()

    with col1:
        st.metric(r"$\mathcal{O}$ (Ontology)", f"{len(entities)} entities",
                  help="Action namespace with runtime integrity hashes")
        if entities:
            with st.expander("Entity list"):
                for e in entities[:20]:
                    st.code(f"{e.get('type', '?')}: {e.get('name', 'unnamed')}")

    with col2:
        core = IdentityCore()
        core.add_commitment(CoreCommitment(
            CommitmentType.VALUE_PRINCIPLE, "Always classify honestly",
            CommitmentThreshold.SUPERMAJORITY, EnforcementMode.INTEGRITY_VETO,
        ))
        st.metric(r"$\mathcal{C}_{\text{core}}$", f"{len(core.commitments)} commitments",
                  help="Core commitments (read-only)")
        with st.expander("Commitments"):
            for c in core.commitments:
                st.markdown(f"- **{c.type.value}**: {c.statement[:50]}...")

    with col3:
        st.metric(r"$\mathcal{K}$ (Extended Knowledge)", "bootstrapped",
                  help="Extended ontology from genesis bootstrapping")

    with col4:
        from ..identity.params import DEFAULT_PARAMETER_ENVELOPE
        params = DEFAULT_PARAMETER_ENVELOPE.snapshot()
        st.metric(r"$\mathcal{P}$ (Parameters)", f"{len(params)} params",
                  help=f"Bounds: quorum={params.get('quorum_threshold', '?')}")
        with st.expander("Parameter values"):
            for k, v in params.items():
                st.metric(k, v)

    st.divider()

    col_vec, col_prove = st.columns([3, 2])

    with col_vec:
        st.subheader("Identity Vector")
        if identity_vec:
            vec_df = pd.DataFrame({
                "dimension": [f"d{i}" for i in range(len(identity_vec))],
                "value": identity_vec,
            })
            chart = alt.Chart(vec_df).mark_bar().encode(
                x="dimension:N",
                y="value:Q",
                color=alt.condition(
                    alt.datum.value > 0.5,
                    alt.value("#2ecc71"),
                    alt.value("#e74c3c"),
                ),
            ).properties(height=200)
            st.altair_chart(chart, use_container_width=True)

    with col_prove:
        st.subheader("Formal Predictions")
        st.caption("12 predictions from Chapters 2-4")
        results = run_all_safe()
        passed = sum(1 for r in results if r.passed)
        st.metric(f"{passed}/12 PASS", f"{passed * 100 // 12}%",
                  delta=f"{12 - passed} remaining" if passed < 12 else "All verified")
        for r in results:
            status = "✅" if r.passed else "❌"
            st.caption(f"{status} **P{r.id:02d}** ({r.chapter} §{r.section})")
            st.caption(f"   {r.description}")


@st.cache_data
def run_all_safe():
    from ..prove.runner import run_all
    return run_all()
