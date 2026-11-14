#!/usr/bin/env python3
"""Build geographic access metrics from Census boundaries + policy status.

Distance metric (no facility coordinates required):
  For each county, compute great-circle distance from county centroid to the
  nearest state centroid where abortion is not totally banned.

This is a policy-geography proxy, not a clinic-travel-time measure.
Facility-based Mode B metrics are only computed when ANSIRH CSV is present.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
sys.path.insert(0, str(ROOT))


def haversine_miles(lat1, lon1, lat2, lon2):
    r = 3958.7613
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def load_states() -> gpd.GeoDataFrame:
    shp = RAW / "census_states" / "cb_2023_us_state_20m.shp"
    gdf = gpd.read_file(shp)
    gdf = gdf[~gdf["STUSPS"].isin(["PR", "AS", "GU", "MP", "VI"])].copy()
    gdf["centroid"] = gdf.geometry.centroid
    gdf["cent_lon"] = gdf["centroid"].x
    gdf["cent_lat"] = gdf["centroid"].y
    return gdf


def load_counties() -> gpd.GeoDataFrame:
    shp = RAW / "census_counties" / "cb_2023_us_county_20m.shp"
    gdf = gpd.read_file(shp)
    gdf = gdf[~gdf["STATEFP"].isin(["72", "60", "66", "69", "78"])].copy()
    gdf["centroid"] = gdf.geometry.centroid
    gdf["cent_lon"] = gdf["centroid"].x
    gdf["cent_lat"] = gdf["centroid"].y
    return gdf


def build_county_access(policy: pd.DataFrame) -> pd.DataFrame:
    states = load_states()
    counties = load_counties()
    policy = policy.copy()
    policy["allows_in_state"] = policy["policy_category"] != "total_ban"

    states = states.merge(
        policy[["state_abbr", "policy_category", "allows_in_state", "state_name"]],
        left_on="STUSPS",
        right_on="state_abbr",
        how="left",
    )

    access_states = states[states["allows_in_state"] == True]  # noqa: E712
    access_lats = access_states["cent_lat"].to_numpy()
    access_lons = access_states["cent_lon"].to_numpy()
    access_abbrs = access_states["STUSPS"].to_numpy()

    rows = []
    for _, c in counties.iterrows():
        state_row = states[states["STATEFP"] == c["STATEFP"]]
        if state_row.empty:
            continue
        s = state_row.iloc[0]
        in_state_ok = bool(s.get("allows_in_state") is True)
        if in_state_ok:
            dist = 0.0
            nearest = s["STUSPS"]
        else:
            dists = haversine_miles(c["cent_lat"], c["cent_lon"], access_lats, access_lons)
            idx = int(np.argmin(dists))
            dist = float(dists[idx])
            nearest = str(access_abbrs[idx])
        rows.append(
            {
                "geoid": c["GEOID"],
                "county_name": c["NAME"],
                "state_fips": c["STATEFP"],
                "state_abbr": s["STUSPS"],
                "policy_category": s.get("policy_category"),
                "allows_in_state": in_state_ok,
                "miles_to_nearest_nonban_state": round(dist, 1),
                "nearest_nonban_state": nearest,
                "county_cent_lat": c["cent_lat"],
                "county_cent_lon": c["cent_lon"],
                "metric_note": (
                    "Distance from county centroid to nearest non-ban state centroid. "
                    "Not clinic travel time. Hypothetical access proxy only."
                ),
                "is_synthetic": False,
            }
        )
    return pd.DataFrame(rows)


def build_state_metrics(
    policy: pd.DataFrame,
    provision: pd.DataFrame,
    population: pd.DataFrame,
    county_access: pd.DataFrame,
) -> pd.DataFrame:
    latest_month = provision["month"].max()
    latest = provision[provision["month"] == latest_month].copy()
    latest = latest.rename(columns={"abortions_median": "abortions_latest_month"})

    state_dist = (
        county_access.groupby("state_abbr", as_index=False)
        .agg(
            mean_miles_to_nonban=("miles_to_nearest_nonban_state", "mean"),
            median_miles_to_nonban=("miles_to_nearest_nonban_state", "median"),
            counties=("geoid", "count"),
            counties_zero_miles=("miles_to_nearest_nonban_state", lambda s: int((s == 0).sum())),
        )
    )

    out = (
        policy.merge(population[["state_abbr", "women_15_44", "year"]], on="state_abbr", how="left")
        .merge(
            latest[["state_abbr", "abortions_latest_month", "abortions_lower", "abortions_upper", "month"]],
            on="state_abbr",
            how="left",
        )
        .merge(state_dist, on="state_abbr", how="left")
    )
    out["provision_rate_per_1000"] = np.where(
        out["women_15_44"].fillna(0) > 0,
        out["abortions_latest_month"] / out["women_15_44"] * 1000.0,
        np.nan,
    )
    out["latest_provision_month"] = latest_month
    out["is_synthetic"] = False
    return out


def optional_facility_metrics() -> dict:
    path = RAW / "ansirh_facilities.csv"
    if not path.exists():
        return {
            "status": "unavailable",
            "message": (
                "ANSIRH facility CSV not found. Mode B facility simulations disabled. "
                "Expected columns: facility_id,name,state_abbr,latitude,longitude"
            ),
        }
    fac = pd.read_csv(path)
    required = {"facility_id", "name", "state_abbr", "latitude", "longitude"}
    if not required.issubset(fac.columns):
        return {
            "status": "unavailable",
            "message": f"Facility CSV missing columns: {sorted(required - set(fac.columns))}",
        }
    if fac[["latitude", "longitude"]].isna().any().any():
        return {
            "status": "unavailable",
            "message": "Facility CSV has missing coordinates; refusing to impute.",
        }
    out = PROCESSED / "facilities.parquet"
    fac.to_parquet(out, index=False)
    fac.to_csv(PROCESSED / "facilities.csv", index=False)
    return {"status": "ok", "n_facilities": len(fac), "file": str(out.relative_to(ROOT))}


def main() -> int:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    policy = pd.read_parquet(PROCESSED / "state_policy.parquet")
    provision = pd.read_parquet(PROCESSED / "monthly_provision.parquet")
    population = pd.read_parquet(PROCESSED / "state_population.parquet")

    # Suppress geographic CRS warning noise for centroid calc on geographic CRS —
    # acceptable for coarse national centroid distances.
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        county_access = build_county_access(policy)

    state_metrics = build_state_metrics(policy, provision, population, county_access)

    county_path = PROCESSED / "county_access.parquet"
    state_path = PROCESSED / "state_metrics.parquet"
    county_access.to_parquet(county_path, index=False)
    state_metrics.to_parquet(state_path, index=False)
    county_access.to_csv(PROCESSED / "county_access.csv", index=False)
    state_metrics.to_csv(PROCESSED / "state_metrics.csv", index=False)

    fac_meta = optional_facility_metrics()
    meta = {
        "county_access_rows": len(county_access),
        "state_metrics_rows": len(state_metrics),
        "facilities": fac_meta,
        "distance_metric": (
            "Miles from county centroid to nearest non-ban state centroid "
            "(Census cartographic boundaries + KFF policy). Not clinic travel time."
        ),
    }
    (PROCESSED / "geographic_metrics_meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
