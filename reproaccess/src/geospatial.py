"""Geospatial helpers for maps and distance metrics."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

POLICY_COLORS = {
    "total_ban": "#7B2D26",
    "early_gestational_limit": "#C47B5B",
    "later_gestational_limit": "#D4A574",
    "viability_or_later": "#5B8A8A",
    "no_gestational_limit": "#2F6F6F",
    "unknown": "#9CA3AF",
}


def load_state_geometries() -> Optional[gpd.GeoDataFrame]:
    shp = RAW / "census_states" / "cb_2023_us_state_20m.shp"
    if not shp.exists():
        return None
    gdf = gpd.read_file(shp)
    gdf = gdf[~gdf["STUSPS"].isin(["PR", "AS", "GU", "MP", "VI", "HI", "AK"])].copy()
    # Keep HI/AK optionally — for continental focus drop them for cleaner choropleth;
    # include all 50+DC for completeness in a second layer if needed.
    return gdf


def load_state_geometries_all() -> Optional[gpd.GeoDataFrame]:
    shp = RAW / "census_states" / "cb_2023_us_state_20m.shp"
    if not shp.exists():
        return None
    gdf = gpd.read_file(shp)
    return gdf[~gdf["STUSPS"].isin(["PR", "AS", "GU", "MP", "VI"])].copy()


def attach_policy(gdf: gpd.GeoDataFrame, policy: pd.DataFrame) -> gpd.GeoDataFrame:
    out = gdf.merge(policy, left_on="STUSPS", right_on="state_abbr", how="left")
    out["fill_color"] = out["policy_category"].map(POLICY_COLORS).fillna(POLICY_COLORS["unknown"])
    return out


def state_geojson_records(state_metrics: pd.DataFrame) -> Optional[gpd.GeoDataFrame]:
    gdf = load_state_geometries_all()
    if gdf is None:
        return None
    return attach_policy(gdf, state_metrics)
