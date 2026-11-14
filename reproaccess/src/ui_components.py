"""Shared Streamlit UI components and theme helpers."""

from __future__ import annotations

from typing import Iterable

import streamlit as st

from src.data_loader import DatasetStatus

NAVY = "#1B2A4A"
TEAL = "#2F6F6F"
BG = "#FFFbf7"
CARD_BORDER = "#E5E0D8"


CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');
html, body, [class*="css"] {{
  font-family: 'Source Sans 3', 'Helvetica Neue', Arial, sans-serif;
  color: {NAVY};
}}
.stApp {{
  background: linear-gradient(180deg, {BG} 0%, #FFFFFF 40%, #F3F7F7 100%);
}}
h1, h2, h3 {{
  font-family: 'Fraunces', Georgia, serif !important;
  color: {NAVY} !important;
}}
.ra-hero {{
  padding: 1.25rem 1.5rem;
  border-left: 4px solid {TEAL};
  background: rgba(255,255,255,0.85);
  margin-bottom: 1rem;
}}
.ra-meta {{
  color: #6B7280;
  font-size: 0.9rem;
}}
.ra-callout {{
  border: 1px solid {CARD_BORDER};
  background: #fff;
  padding: 0.9rem 1rem;
  margin: 0.75rem 0;
}}
.ra-warn {{
  border-left: 4px solid #C47B5B;
  background: #FFF8F3;
  padding: 0.75rem 1rem;
  margin: 0.75rem 0;
}}
.ra-hypo {{
  border-left: 4px solid #7B2D26;
  background: #FDF6F5;
  padding: 0.75rem 1rem;
  margin: 0.75rem 0;
  font-weight: 600;
}}
div[data-testid="stMetric"] {{
  background: white;
  border: 1px solid {CARD_BORDER};
  padding: 0.75rem;
}}
</style>
"""


def inject_theme() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    inject_theme()
    st.markdown(
        f"""
        <div class="ra-hero">
          <div style="font-size:0.85rem; letter-spacing:0.08em; text-transform:uppercase; color:{TEAL}; font-weight:700;">
            ReproAccess
          </div>
          <h1 style="margin:0.2rem 0 0.4rem 0;">{title}</h1>
          <div class="ra-meta">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def source_caption(text: str) -> None:
    st.caption(text)


def unavailable_block(status: DatasetStatus) -> None:
    st.markdown(
        f"""
        <div class="ra-warn">
          <strong>Data unavailable:</strong> {status.name}<br/>
          {status.message}<br/>
          <span class="ra-meta">Expected format: {status.expected_format}</span><br/>
          <span class="ra-meta">Source: {status.source_url or "n/a"}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hypo_banner(extra: str = "") -> None:
    st.markdown(
        f"""
        <div class="ra-hypo">
          HYPOTHETICAL OUTPUT — illustrative scenario only. Not a forecast of real-world health outcomes.
          {extra}
        </div>
        """,
        unsafe_allow_html=True,
    )


def causal_disclaimer() -> None:
    st.info(
        "Associations shown on this page are observational. "
        "They are not causal estimates of policy effects on health outcomes."
    )


def metric_row(items: Iterable[tuple[str, str]]) -> None:
    item_list = list(items)
    cols = st.columns(max(len(item_list), 1))
    for col, (label, value) in zip(cols, item_list):
        col.metric(label, value)
