"""Hypothetical policy scenario simulator."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis import POLICY_LABELS, POLICY_ORDER
from src.data_loader import load_all
from src.simulations import mode_a_policy_shift, mode_b_facility_access
from src.ui_components import hypo_banner, page_header, unavailable_block
from src.visualizations import scenario_comparison_bars

page_header(
    "Policy Scenario Simulator",
    "Illustrative what-if tools. Outputs are hypothetical and must not be read as forecasts.",
)
hypo_banner()

data = load_all()
tables = data["tables"]
statuses = data["statuses"]

if not statuses["state_metrics"].available:
    unavailable_block(statuses["state_metrics"])
    st.stop()

metrics = tables["state_metrics"]
county = tables.get("county_access")
facilities = tables.get("facilities")

mode = st.radio("Simulation mode", ["Mode A — Policy reclassification", "Mode B — Facility closures"])

if mode.startswith("Mode A"):
    st.markdown("### Mode A — always available")
    from_cats = st.multiselect(
        "Reclassify states currently in…",
        options=POLICY_ORDER,
        default=["total_ban"],
        format_func=lambda x: POLICY_LABELS.get(x, x),
    )
    to_cat = st.selectbox(
        "…to policy category",
        options=[c for c in POLICY_ORDER if c != "total_ban"] or POLICY_ORDER,
        index=min(2, len(POLICY_ORDER) - 1),
        format_func=lambda x: POLICY_LABELS.get(x, x),
    )
    elasticity = st.slider(
        "Illustrative elasticity per restrictiveness step",
        min_value=0.0,
        max_value=0.5,
        value=0.15,
        step=0.05,
        help="User-chosen parameter. Not estimated from these data.",
    )
    if st.button("Run Mode A scenario", type="primary"):
        hypo_banner("Mode A results below.")
        result = mode_a_policy_shift(metrics, from_cats, to_cat, elasticity)
        st.dataframe(result.summary, use_container_width=True, hide_index=True)
        st.plotly_chart(scenario_comparison_bars(result.details), use_container_width=True)
        with st.expander("Assumptions"):
            for a in result.assumptions:
                st.markdown(f"- {a}")
        with st.expander("Warnings"):
            for w in result.warnings:
                st.markdown(f"- {w}")
        st.dataframe(result.details, use_container_width=True, hide_index=True)

else:
    st.markdown("### Mode B — requires facility coordinates")
    if not statuses["facilities"].available:
        unavailable_block(statuses["facilities"])
        st.info(
            "To enable Mode B, place a real facility CSV at "
            "`reproaccess/data/raw/ansirh_facilities.csv` with columns "
            "`facility_id,name,state_abbr,latitude,longitude`, then re-run "
            "`scripts/build_geographic_metrics.py`. Coordinates are never fabricated."
        )
    else:
        if county is None:
            unavailable_block(statuses["county_access"])
            st.stop()
        close_states = st.multiselect(
            "Hypothetically close facilities in states",
            options=sorted(facilities["state_abbr"].unique()),
            default=[],
        )
        if st.button("Run Mode B scenario", type="primary"):
            hypo_banner("Mode B results below.")
            result = mode_b_facility_access(county, facilities, close_states)
            st.dataframe(result.summary, use_container_width=True, hide_index=True)
            with st.expander("Assumptions"):
                for a in result.assumptions:
                    st.markdown(f"- {a}")
            with st.expander("Warnings"):
                for w in result.warnings:
                    st.markdown(f"- {w}")
            if not result.details.empty:
                st.dataframe(result.details.head(500), use_container_width=True, hide_index=True)
