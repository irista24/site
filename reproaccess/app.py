"""ReproAccess — abortion-care access & policy analytics (Streamlit entrypoint)."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_loader import load_all
from src.ui_components import inject_theme, page_header, source_caption, unavailable_block

st.set_page_config(
    page_title="ReproAccess",
    page_icon="R",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()
page_header(
    "Abortion-care access & policy analytics",
    "Public-data dashboard for exploring provision estimates, state policy, "
    "and geographic access proxies. Observational analytics only — not clinical advice.",
)

data = load_all()
statuses = data["statuses"]

st.markdown("### Data readiness")
cols = st.columns(3)
keys = [
    "state_policy",
    "monthly_provision",
    "state_population",
    "state_metrics",
    "county_access",
    "facilities",
]
for i, key in enumerate(keys):
    status = statuses[key]
    with cols[i % 3]:
        icon = "✓" if status.available else "!"
        st.markdown(f"**{icon} {status.name}**")
        st.caption(status.message)
        if not status.available and key == "facilities":
            unavailable_block(status)

st.markdown("---")
st.markdown(
    """
    Use the sidebar to open:
    1. **Overview** — national snapshot and trends  
    2. **Geographic Access** — county distance proxy & maps  
    3. **Policy Analysis** — observational comparisons (+ optional regression)  
    4. **Scenario Simulator** — hypothetical Mode A (always) / Mode B (if facilities)  
    5. **Methodology** — sources, limitations, data dictionary  
    """
)

manifest = data.get("manifest") or {}
if manifest:
    source_caption(
        f"Source manifest generated {manifest.get('generated', 'n/a')}. "
        "See Methodology for URLs and extraction dates."
    )

st.sidebar.title("ReproAccess")
st.sidebar.caption("Public-health analytics · no login required")
st.sidebar.markdown(
    "All simulation outputs are **hypothetical**. "
    "Observational associations are **not causal**."
)
