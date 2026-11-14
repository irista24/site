"""Overview dashboard page."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis import monthly_national_trend, summarize_by_policy
from src.data_loader import load_all
from src.ui_components import causal_disclaimer, page_header, source_caption, unavailable_block
from src.visualizations import policy_choropleth, provision_trend, rate_bar

page_header(
    "Overview",
    "National snapshot of policy categories and monthly provision estimates from public sources.",
)
causal_disclaimer()

data = load_all()
tables = data["tables"]
statuses = data["statuses"]

if not statuses["state_metrics"].available:
    unavailable_block(statuses["state_metrics"])
    st.stop()

metrics = tables["state_metrics"]
provision = tables["monthly_provision"]
policy = tables["state_policy"]

# KPI row
n_ban = int((metrics["policy_category"] == "total_ban").sum())
n_protect = int(metrics["policy_category"].isin(["no_gestational_limit", "viability_or_later"]).sum())
latest_month = metrics["latest_provision_month"].iloc[0] if "latest_provision_month" in metrics else None
prov_states = int(metrics["abortions_latest_month"].notna().sum())
total_latest = float(metrics["abortions_latest_month"].sum(skipna=True))

c1, c2, c3, c4 = st.columns(4)
c1.metric("States with total ban (KFF)", f"{n_ban}")
c2.metric("States viability / no limit", f"{n_protect}")
c3.metric("States with provision estimate", f"{prov_states}")
c4.metric(
    "Sum of state medians (latest month)",
    f"{total_latest:,.0f}",
    help="Sum of Guttmacher state medians for reporting states — not a substitute for the published US total.",
)

source_caption(
    f"Policy: KFF State Health Facts (see Methodology). "
    f"Provision latest month: {pd.to_datetime(latest_month).strftime('%Y-%m') if latest_month is not None else 'n/a'}. "
    "Guttmacher Monthly Abortion Provision Study via OSF."
)

left, right = st.columns([1.1, 1])
with left:
    st.plotly_chart(policy_choropleth(metrics), use_container_width=True)
with right:
    summary = summarize_by_policy(metrics)
    st.dataframe(summary.table, use_container_width=True, hide_index=True)
    for note in summary.notes:
        st.caption(f"• {note}")

st.markdown("### Monthly provision trends")
if provision is None:
    unavailable_block(statuses["monthly_provision"])
else:
    states = sorted(provision["state_abbr"].unique())
    pick = st.multiselect(
        "Select states",
        states,
        default=[s for s in ["CA", "NY", "IL", "FL", "GA"] if s in states][:5],
    )
    st.plotly_chart(provision_trend(provision, pick or None), use_container_width=True)
    trend = monthly_national_trend(provision)
    st.line_chart(trend.set_index("month")["abortions_sum_of_state_medians"])
    st.caption(
        "Chart above sums state-level medians for states present in the file each month. "
        "Prefer Guttmacher's published national series for official US totals."
    )

st.markdown("### Latest-month rates")
st.plotly_chart(rate_bar(metrics), use_container_width=True)
st.caption("Rate = latest-month abortions / women ages 15–44 × 1000 (Census 2023 civilian estimates).")
