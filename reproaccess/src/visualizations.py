"""Plotly chart builders with consistent public-health styling."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.analysis import POLICY_LABELS
from src.geospatial import POLICY_COLORS

FONT_FAMILY = "Source Sans 3, Source Sans Pro, Helvetica Neue, Arial, sans-serif"
NAVY = "#1B2A4A"
TEAL = "#2F6F6F"
MUTED = "#6B7280"


def apply_layout(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color=NAVY, family=FONT_FAMILY)),
        font=dict(family=FONT_FAMILY, color=NAVY, size=13),
        paper_bgcolor="#FFFbf7",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=40, r=20, t=60, b=40),
        legend=dict(bgcolor="rgba(255,255,255,0.8)"),
    )
    return fig


def policy_choropleth(state_metrics: pd.DataFrame) -> go.Figure:
    df = state_metrics.copy()
    df["policy_label"] = df["policy_category"].map(POLICY_LABELS)
    color_map = {POLICY_LABELS[k]: v for k, v in POLICY_COLORS.items() if k in POLICY_LABELS}
    fig = px.choropleth(
        df,
        locations="state_abbr",
        locationmode="USA-states",
        color="policy_label",
        color_discrete_map=color_map,
        scope="usa",
        hover_name="state_name",
        hover_data={
            "state_abbr": False,
            "statutory_limit": True,
            "mandatory_waiting_period": True,
            "policy_label": True,
        },
    )
    return apply_layout(fig, "State abortion policy category (KFF)")


def provision_trend(provision: pd.DataFrame, states: list[str] | None = None) -> go.Figure:
    df = provision.copy()
    if states:
        df = df[df["state_abbr"].isin(states)]
    fig = px.line(
        df,
        x="month",
        y="abortions_median",
        color="state_abbr",
        labels={"abortions_median": "Estimated abortions (median)", "month": "Month"},
    )
    fig.update_traces(mode="lines")
    return apply_layout(fig, "Monthly abortion provision estimates (Guttmacher)")


def rate_bar(state_metrics: pd.DataFrame) -> go.Figure:
    df = state_metrics.dropna(subset=["provision_rate_per_1000"]).sort_values(
        "provision_rate_per_1000", ascending=True
    )
    df["policy_label"] = df["policy_category"].map(POLICY_LABELS)
    color_map = {POLICY_LABELS[k]: v for k, v in POLICY_COLORS.items() if k in POLICY_LABELS}
    fig = px.bar(
        df,
        x="provision_rate_per_1000",
        y="state_abbr",
        color="policy_label",
        color_discrete_map=color_map,
        orientation="h",
        labels={"provision_rate_per_1000": "Abortions per 1,000 women 15–44 (latest month)"},
        height=max(500, 14 * len(df)),
    )
    return apply_layout(fig, "Latest-month provision rate by state")


def distance_hist(county_access: pd.DataFrame) -> go.Figure:
    df = county_access.copy()
    fig = px.histogram(
        df,
        x="miles_to_nearest_nonban_state",
        nbins=40,
        color_discrete_sequence=[TEAL],
        labels={"miles_to_nearest_nonban_state": "Miles to nearest non-ban state centroid"},
    )
    return apply_layout(
        fig,
        "County access proxy: distance to nearest non-ban state",
    )


def scenario_comparison_bars(details: pd.DataFrame) -> go.Figure:
    df = details[details["changed"]].copy()
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No states reclassified in this scenario.", showarrow=False)
        return apply_layout(fig, "Scenario comparison")
    melted = df.melt(
        id_vars=["state_abbr"],
        value_vars=["baseline_abortions", "scenario_abortions"],
        var_name="series",
        value_name="abortions",
    )
    melted["series"] = melted["series"].map(
        {
            "baseline_abortions": "Baseline (observed)",
            "scenario_abortions": "Hypothetical scenario",
        }
    )
    fig = px.bar(
        melted.dropna(subset=["abortions"]),
        x="state_abbr",
        y="abortions",
        color="series",
        barmode="group",
        color_discrete_sequence=[NAVY, TEAL],
    )
    return apply_layout(fig, "HYPOTHETICAL: baseline vs scenario abortions")
