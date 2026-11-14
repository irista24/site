"""Unit tests for hypothetical scenario simulations."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.simulations import mode_a_policy_shift, mode_b_facility_access


def _metrics():
    return pd.DataFrame(
        {
            "state_abbr": ["CA", "TX", "NY"],
            "state_name": ["California", "Texas", "New York"],
            "policy_category": ["no_gestational_limit", "total_ban", "viability_or_later"],
            "women_15_44": [1_000_000, 2_000_000, 1_500_000],
            "abortions_latest_month": [1000.0, np.nan, 800.0],
            "provision_rate_per_1000": [1.0, np.nan, 0.533],
        }
    )


def test_mode_a_marks_hypothetical_and_does_not_invent_ban_counts():
    result = mode_a_policy_shift(
        _metrics(),
        from_categories=["total_ban"],
        to_category="no_gestational_limit",
        elasticity=0.2,
    )
    assert result.hypothetical is True
    assert result.mode == "A"
    tx = result.details[result.details["state_abbr"] == "TX"].iloc[0]
    assert tx["changed"] is True or tx["changed"] == True  # noqa: E712
    # Ban state had no observed provision — scenario must not invent abortions
    assert pd.isna(tx["scenario_abortions"])


def test_mode_a_adjusts_observed_rates_when_loosening():
    metrics = _metrics()
    # Reclassify NY from viability to no limit (one step less restrictive)
    result = mode_a_policy_shift(
        metrics,
        from_categories=["viability_or_later"],
        to_category="no_gestational_limit",
        elasticity=0.1,
    )
    ny = result.details[result.details["state_abbr"] == "NY"].iloc[0]
    assert ny["scenario_rate"] > ny["baseline_rate"]


def test_mode_b_unavailable_without_facilities():
    county = pd.DataFrame(
        {
            "geoid": ["06001"],
            "county_name": ["Alameda"],
            "state_abbr": ["CA"],
            "county_cent_lat": [37.6],
            "county_cent_lon": [-121.9],
        }
    )
    result = mode_b_facility_access(county, None, close_states=["TX"])
    assert result.mode == "B"
    assert any("unavailable" in w.lower() or "Facility" in w for w in result.warnings)


def test_mode_b_with_facilities_computes_distances():
    county = pd.DataFrame(
        {
            "geoid": ["06001", "48001"],
            "county_name": ["Alameda", "Anderson"],
            "state_abbr": ["CA", "TX"],
            "county_cent_lat": [37.6, 31.8],
            "county_cent_lon": [-121.9, -95.6],
        }
    )
    facilities = pd.DataFrame(
        {
            "facility_id": ["1", "2"],
            "name": ["A", "B"],
            "state_abbr": ["CA", "TX"],
            "latitude": [37.7, 32.0],
            "longitude": [-122.0, -96.0],
        }
    )
    result = mode_b_facility_access(county, facilities, close_states=["TX"])
    assert result.hypothetical is True
    assert not result.details.empty
    assert "baseline_miles_to_facility" in result.details.columns
