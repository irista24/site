"""Hypothetical policy scenario simulations.

All outputs are labeled hypothetical and must never be presented as forecasts
of real-world health outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from src.analysis import POLICY_LABELS


@dataclass
class ScenarioResult:
    mode: str
    hypothetical: bool
    summary: pd.DataFrame
    details: pd.DataFrame
    assumptions: list[str]
    warnings: list[str]


def mode_a_policy_shift(
    state_metrics: pd.DataFrame,
    from_categories: list[str],
    to_category: str,
    elasticity: float = 0.15,
) -> ScenarioResult:
    """Mode A: reclassify selected policy categories and apply a simple elasticity
    to provision rates where observed provision exists.

    For states currently banned (no observed provision), we do NOT invent abortion
    counts. We only report population newly classified under the destination policy
    and flag provision as unknown.
    """
    df = state_metrics.copy()
    df["baseline_category"] = df["policy_category"]
    df["scenario_category"] = df["policy_category"]
    mask = df["policy_category"].isin(from_categories)
    df.loc[mask, "scenario_category"] = to_category

    df["baseline_rate"] = df["provision_rate_per_1000"]
    # Direction: moving toward less restrictive categories → positive elasticity on rate
    restrictiveness = {
        "total_ban": 4,
        "early_gestational_limit": 3,
        "later_gestational_limit": 2,
        "viability_or_later": 1,
        "no_gestational_limit": 0,
    }
    df["delta_restrict"] = df["baseline_category"].map(restrictiveness) - df["scenario_category"].map(
        restrictiveness
    )
    df["scenario_rate"] = np.where(
        df["baseline_rate"].notna(),
        df["baseline_rate"] * (1 + elasticity * df["delta_restrict"].fillna(0)),
        np.nan,
    )
    df["scenario_abortions"] = np.where(
        df["scenario_rate"].notna() & df["women_15_44"].notna(),
        df["scenario_rate"] / 1000.0 * df["women_15_44"],
        np.nan,
    )
    df["baseline_abortions"] = df["abortions_latest_month"]
    df["changed"] = mask
    df["population_reclassified"] = np.where(mask, df["women_15_44"], 0)

    summary = pd.DataFrame(
        [
            {
                "metric": "States reclassified",
                "value": int(mask.sum()),
            },
            {
                "metric": "Women 15–44 in reclassified states",
                "value": float(df.loc[mask, "women_15_44"].sum()),
            },
            {
                "metric": "Baseline abortions (states with observed provision, monthly)",
                "value": float(df["baseline_abortions"].sum(skipna=True)),
            },
            {
                "metric": "Hypothetical scenario abortions (same states only)",
                "value": float(df["scenario_abortions"].sum(skipna=True)),
            },
            {
                "metric": "Elasticity applied per restrictiveness step",
                "value": elasticity,
            },
        ]
    )

    assumptions = [
        "HYPOTHETICAL simulation — not a prediction of real-world outcomes.",
        f"States in {from_categories} reclassified to {to_category} ({POLICY_LABELS.get(to_category, to_category)}).",
        f"For states with observed provision, rate adjusts by {elasticity:.0%} per step change in restrictiveness index.",
        "States without observed provision (typically total bans) are not assigned invented abortion counts.",
        "Ignores interstate travel, telehealth, capacity constraints, and enforcement.",
    ]
    warnings = [
        "Do not interpret results as causal policy impacts or clinical forecasts.",
        "Elasticity is a user-chosen illustrative parameter, not estimated from these data.",
    ]
    details = df[
        [
            "state_abbr",
            "state_name",
            "women_15_44",
            "baseline_category",
            "scenario_category",
            "baseline_abortions",
            "scenario_abortions",
            "baseline_rate",
            "scenario_rate",
            "changed",
        ]
    ].sort_values("state_abbr")
    return ScenarioResult(
        mode="A",
        hypothetical=True,
        summary=summary,
        details=details,
        assumptions=assumptions,
        warnings=warnings,
    )


def mode_b_facility_access(
    county_access: pd.DataFrame,
    facilities: Optional[pd.DataFrame],
    close_states: list[str],
) -> ScenarioResult:
    """Mode B: if facility coordinates exist, estimate share of counties whose
    nearest in-network facility would change if facilities in `close_states` close.

    Without facilities, returns an unavailable result (never invents coordinates).
    """
    if facilities is None or facilities.empty:
        empty = pd.DataFrame({"metric": ["Facilities unavailable"], "value": [np.nan]})
        return ScenarioResult(
            mode="B",
            hypothetical=True,
            summary=empty,
            details=pd.DataFrame(),
            assumptions=[],
            warnings=[
                "Facility data unavailable. Place ANSIRH CSV at data/raw/ansirh_facilities.csv "
                "with facility_id,name,state_abbr,latitude,longitude. Coordinates are never fabricated."
            ],
        )

    required = {"latitude", "longitude", "state_abbr"}
    if not required.issubset(facilities.columns):
        return ScenarioResult(
            mode="B",
            hypothetical=True,
            summary=pd.DataFrame({"metric": ["Invalid facility schema"], "value": [np.nan]}),
            details=pd.DataFrame(),
            assumptions=[],
            warnings=[f"Facility CSV missing columns: {sorted(required - set(facilities.columns))}"],
        )

    def hav(lat1, lon1, lat2, lon2):
        r = 3958.7613
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        return 2 * r * np.arcsin(np.sqrt(a))

    counties = county_access.dropna(subset=["county_cent_lat", "county_cent_lon"]).copy()
    fac_all = facilities.dropna(subset=["latitude", "longitude"]).copy()
    fac_open = fac_all[~fac_all["state_abbr"].isin(close_states)].copy()

    def nearest_miles(fac_df: pd.DataFrame) -> np.ndarray:
        if fac_df.empty:
            return np.full(len(counties), np.nan)
        dists = []
        lats = fac_df["latitude"].to_numpy()
        lons = fac_df["longitude"].to_numpy()
        for _, row in counties.iterrows():
            d = hav(row["county_cent_lat"], row["county_cent_lon"], lats, lons)
            dists.append(float(np.min(d)))
        return np.array(dists)

    baseline = nearest_miles(fac_all)
    scenario = nearest_miles(fac_open)
    counties["baseline_miles_to_facility"] = baseline
    counties["scenario_miles_to_facility"] = scenario
    counties["miles_increase"] = scenario - baseline

    summary = pd.DataFrame(
        [
            {"metric": "Facilities baseline", "value": len(fac_all)},
            {"metric": "Facilities after hypothetical closures", "value": len(fac_open)},
            {"metric": "Median baseline miles to nearest facility", "value": float(np.nanmedian(baseline))},
            {"metric": "Median scenario miles to nearest facility", "value": float(np.nanmedian(scenario))},
            {
                "metric": "Counties with >25 mile increase",
                "value": int(np.nansum(counties["miles_increase"] > 25)),
            },
        ]
    )
    return ScenarioResult(
        mode="B",
        hypothetical=True,
        summary=summary,
        details=counties[
            [
                "geoid",
                "county_name",
                "state_abbr",
                "baseline_miles_to_facility",
                "scenario_miles_to_facility",
                "miles_increase",
            ]
        ],
        assumptions=[
            "HYPOTHETICAL — facility closures are assumed, not observed.",
            f"Facilities in states {close_states} treated as closed.",
            "Distance is county-centroid to facility lat/lon great-circle miles.",
            "Does not model appointment capacity, cost, or legal barriers.",
        ],
        warnings=[
            "Illustrative access geometry only; not a health-outcome forecast.",
        ],
    )
