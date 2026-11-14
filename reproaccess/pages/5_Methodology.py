"""Methodology and data quality page."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_loader import load_all
from src.ui_components import page_header, unavailable_block

page_header(
    "Methodology & Data Quality",
    "Sources, extraction dates, expected schemas, and analytical limitations.",
)

data = load_all()
statuses = data["statuses"]
manifest = data.get("manifest") or {}
dictionary = data.get("data_dictionary") or {}

st.markdown(
    """
### Principles
- **Real public data only** — Guttmacher OSF provision estimates, KFF policy indicators,
  Census population estimates, and Census cartographic boundaries.
- **No fabricated coordinates or outcomes** — facility Mode B requires a user-supplied CSV.
- **Unavailable ≠ synthetic** — missing sources show an explicit unavailable state.
- **Observational ≠ causal** — regressions and group comparisons are associations.
- **Simulations are hypothetical** — clearly labeled; not forecasts.
"""
)

st.markdown("### Source manifest")
if manifest:
    st.json(manifest)
else:
    st.warning("Source manifest not found. Run `python scripts/ingest_data.py`.")

st.markdown("### Dataset status")
for key, status in statuses.items():
    label = "Available" if status.available else "Unavailable"
    st.markdown(f"**[{label}] {status.name}** — {status.message}")
    if status.source_url:
        st.caption(f"Source: {status.source_url}")
    if not status.available:
        st.code(status.expected_format)

st.markdown("### KFF CSV workflow")
st.markdown(
    """
KFF State Health Facts indicators are interactive. This project ships a curated extraction of
the published gestational-limits and waiting-period tables (with as-of dates in the file).

If you prefer a fresh manual export:
1. Open [Gestational Limits](https://www.kff.org/state-health-policy-data/state-indicator/gestational-limit-abortions/)
   and [Waiting Periods](https://www.kff.org/other/state-indicator/mandatory-waiting-periods/).
2. Use the table view / download controls if available, or copy the state table.
3. Save as `data/raw/kff_abortion_policy.csv` with at least:
   `state_name,state_abbr,state_fips,statutory_limit,policy_category,mandatory_waiting_period,waiting_period_length,source_url,extraction_date,is_synthetic`
4. Set `is_synthetic=false` for all observed rows.
5. Re-run `python scripts/clean_data.py` and `python scripts/build_geographic_metrics.py`.
"""
)

st.markdown("### Geographic access metric")
st.markdown(
    """
Distance proxy = great-circle miles from each county's cartographic centroid to the nearest
**non-ban state centroid** (states where `policy_category != total_ban`).

This is a coarse policy-geography measure. It is **not** driving time to a clinic and does not
incorporate telehealth, cost, or capacity.
"""
)

st.markdown("### Optional ANSIRH facilities")
st.markdown(
    """
Place `data/raw/ansirh_facilities.csv` with columns:
`facility_id,name,state_abbr,latitude,longitude`.

Coordinates must be real; the pipeline refuses to impute missing lat/lon.
"""
)

st.markdown("### Data dictionary")
if dictionary:
    st.json(dictionary)
else:
    st.caption("Run clean_data.py to generate data_dictionary.json")

st.markdown("### Citation reminders")
st.markdown(
    """
- Guttmacher Institute, Monthly Abortion Provision Study (OSF: https://osf.io/k4x7t/).
- KFF, Abortion in the United States Dashboard / State Health Facts.
- U.S. Census Bureau, Cartographic Boundary Files and State Age-Sex Population Estimates.
"""
)
