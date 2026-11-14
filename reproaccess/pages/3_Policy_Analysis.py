"""Policy analysis page with optional FE-style regression."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis import (
    POLICY_LABELS,
    correlation_rate_vs_distance,
    optional_panel_regression,
    summarize_by_policy,
)
from src.data_loader import load_all
from src.ui_components import causal_disclaimer, page_header, source_caption, unavailable_block
from src.visualizations import rate_bar

page_header(
    "Policy Analysis",
    "Compare observed provision patterns across KFF policy categories. "
    "Optional regression is exploratory and non-causal.",
)
causal_disclaimer()

data = load_all()
tables = data["tables"]
statuses = data["statuses"]

for key in ("state_metrics", "monthly_provision", "state_policy"):
    if not statuses[key].available:
        unavailable_block(statuses[key])
        st.stop()

metrics = tables["state_metrics"]
provision = tables["monthly_provision"]
policy = tables["state_policy"]

st.markdown("### Descriptive comparisons by policy category")
summary = summarize_by_policy(metrics)
st.dataframe(summary.table, use_container_width=True, hide_index=True)
for note in summary.notes:
    st.caption(f"• {note}")

st.plotly_chart(rate_bar(metrics), use_container_width=True)

corr = correlation_rate_vs_distance(metrics)
if corr.get("ok"):
    st.metric("Pearson r (rate vs mean distance)", f"{corr['pearson_r']:.3f}")
    st.caption(corr["note"])
else:
    st.caption(corr.get("message", "Correlation unavailable"))

st.markdown("### State detail")
show_cols = [
    "state_abbr",
    "state_name",
    "statutory_limit",
    "policy_category",
    "mandatory_waiting_period",
    "waiting_period_length",
    "women_15_44",
    "abortions_latest_month",
    "provision_rate_per_1000",
    "mean_miles_to_nonban",
]
existing = [c for c in show_cols if c in metrics.columns]
st.dataframe(
    metrics[existing].assign(
        policy_label=lambda d: d["policy_category"].map(POLICY_LABELS)
    ),
    use_container_width=True,
    hide_index=True,
)

source_caption(
    "Policy source: KFF State Health Facts gestational limits & waiting periods. "
    "Provision: Guttmacher Monthly Abortion Provision Study. Population: Census popest 2023."
)

st.markdown("### Optional exploratory regression")
st.markdown(
    "Pooled OLS of log monthly abortions on policy category dummies with month fixed effects "
    "and state-clustered standard errors. **Not a causal two-way fixed-effects estimate** — "
    "policy does not vary within state in this KFF snapshot."
)
run = st.checkbox("Run optional regression", value=False)
if run:
    result = optional_panel_regression(provision, policy)
    if not result or not result.get("ok"):
        st.warning((result or {}).get("message", "Regression unavailable"))
    else:
        st.write(
            {
                "n_obs": result["n_obs"],
                "n_states": result["n_states"],
                "r_squared": round(result["r_squared"], 3),
                "formula": result["formula"],
            }
        )
        coef_df = pd.DataFrame(
            {
                "term": list(result["coefficients"].keys()),
                "coefficient": list(result["coefficients"].values()),
                "std_error": [result["std_errors"].get(k) for k in result["coefficients"]],
            }
        )
        st.dataframe(coef_df, use_container_width=True, hide_index=True)
        st.error("Limitations")
        for lim in result["limitations"]:
            st.markdown(f"- {lim}")
