"""Geographic access explorer."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_loader import load_all
from src.geospatial import POLICY_COLORS
from src.ui_components import page_header, source_caption, unavailable_block
from src.visualizations import apply_layout, distance_hist, policy_choropleth

page_header(
    "Geographic Access Explorer",
    "County-level distance proxy from Census cartographic centroids to the nearest "
    "non-ban state. This is not clinic travel time.",
)

data = load_all()
tables = data["tables"]
statuses = data["statuses"]

if not statuses["county_access"].available:
    unavailable_block(statuses["county_access"])
    st.stop()
if not statuses["state_metrics"].available:
    unavailable_block(statuses["state_metrics"])
    st.stop()

county = tables["county_access"]
metrics = tables["state_metrics"]

st.warning(
    "Access metric = great-circle miles from county centroid to nearest state centroid "
    "where abortion is not totally banned (KFF policy × Census boundaries). "
    "It does **not** use facility locations unless Mode B facility data is imported."
)

c1, c2, c3 = st.columns(3)
c1.metric("Counties", f"{len(county):,}")
c2.metric(
    "Median miles (all counties)",
    f"{county['miles_to_nearest_nonban_state'].median():.0f}",
)
banned = county[~county["allows_in_state"]]
c3.metric(
    "Median miles (ban-state counties)",
    f"{banned['miles_to_nearest_nonban_state'].median():.0f}" if len(banned) else "n/a",
)

st.plotly_chart(policy_choropleth(metrics), use_container_width=True)
source_caption("State fill = KFF policy category.")

st.plotly_chart(distance_hist(county), use_container_width=True)

st.markdown("### State summary of county distances")
state_view = (
    metrics[
        [
            "state_abbr",
            "state_name",
            "policy_category",
            "mean_miles_to_nonban",
            "median_miles_to_nonban",
            "counties",
            "counties_zero_miles",
        ]
    ]
    .sort_values("mean_miles_to_nonban", ascending=False)
)
st.dataframe(state_view, use_container_width=True, hide_index=True)

st.markdown("### Filter counties")
states = ["(all)"] + sorted(county["state_abbr"].unique())
sel = st.selectbox("State", states)
view = county if sel == "(all)" else county[county["state_abbr"] == sel]
st.dataframe(
    view[
        [
            "county_name",
            "state_abbr",
            "policy_category",
            "miles_to_nearest_nonban_state",
            "nearest_nonban_state",
            "allows_in_state",
        ]
    ].sort_values("miles_to_nearest_nonban_state", ascending=False),
    use_container_width=True,
    hide_index=True,
)

# Optional scatter: state mean distance vs provision rate
scatter_df = metrics.dropna(subset=["mean_miles_to_nonban", "provision_rate_per_1000"])
if not scatter_df.empty:
    fig = px.scatter(
        scatter_df,
        x="mean_miles_to_nonban",
        y="provision_rate_per_1000",
        hover_name="state_abbr",
        color="policy_category",
        color_discrete_map=POLICY_COLORS,
        labels={
            "mean_miles_to_nonban": "Mean county miles to non-ban state",
            "provision_rate_per_1000": "Provision rate per 1,000",
        },
    )
    st.plotly_chart(apply_layout(fig, "Observational: distance proxy vs provision rate"), use_container_width=True)
    st.caption("Association only — not causal. Ban states typically lack provision estimates.")

if statuses["facilities"].available:
    st.success(f"Facility file loaded ({statuses['facilities'].message}). Mode B enabled on Simulator page.")
else:
    unavailable_block(statuses["facilities"])
