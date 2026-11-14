"""Unit tests for analysis helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from src.analysis import (
    monthly_national_trend,
    optional_panel_regression,
    summarize_by_policy,
)
from src.validation import validate_policy_table, validate_provision_table


def test_summarize_by_policy_groups():
    df = pd.DataFrame(
        {
            "state_abbr": ["CA", "TX", "NY"],
            "policy_category": ["no_gestational_limit", "total_ban", "viability_or_later"],
            "provision_rate_per_1000": [1.2, None, 0.9],
            "mean_miles_to_nonban": [0.0, 120.0, 0.0],
            "women_15_44": [1e6, 2e6, 1.5e6],
            "abortions_latest_month": [1000, None, 800],
        }
    )
    result = summarize_by_policy(df)
    assert len(result.table) == 3
    assert result.method


def test_monthly_national_trend():
    provision = pd.DataFrame(
        {
            "state_abbr": ["CA", "CA", "NY"],
            "month": pd.to_datetime(["2024-01-15", "2024-02-15", "2024-01-15"]),
            "abortions_median": [100, 110, 50],
        }
    )
    trend = monthly_national_trend(provision)
    jan = trend.loc[trend["month"] == pd.Timestamp("2024-01-15")].iloc[0]
    assert jan["abortions_sum_of_state_medians"] == 150
    assert jan["n_states"] == 2


def test_validate_provision_rejects_negatives():
    bad = pd.DataFrame(
        {
            "state_abbr": ["CA"],
            "month": [pd.Timestamp("2024-01-15")],
            "abortions_median": [-1],
            "abortions_lower": [-2],
            "abortions_upper": [0],
            "source_url": ["x"],
        }
    )
    result = validate_provision_table(bad)
    assert not result.ok


def test_validate_policy_categories():
    df = pd.DataFrame(
        {
            "state_fips": ["06"],
            "state_abbr": ["CA"],
            "state_name": ["California"],
            "policy_category": ["not_a_real_category"],
            "statutory_limit": ["x"],
            "source_url": ["u"],
            "extraction_date": ["2026-01-01"],
        }
    )
    result = validate_policy_table(df)
    assert not result.ok


def test_optional_regression_runs_or_explains():
    provision = pd.DataFrame(
        {
            "state_abbr": ["CA", "CA", "NY", "NY", "FL", "FL"],
            "month": pd.to_datetime(
                ["2024-01-15", "2024-02-15", "2024-01-15", "2024-02-15", "2024-01-15", "2024-02-15"]
            ),
            "abortions_median": [1000, 1100, 800, 850, 900, 950],
        }
    )
    policy = pd.DataFrame(
        {
            "state_abbr": ["CA", "NY", "FL"],
            "policy_category": [
                "no_gestational_limit",
                "viability_or_later",
                "early_gestational_limit",
            ],
        }
    )
    result = optional_panel_regression(provision, policy)
    assert result is not None
    if result.get("ok"):
        assert "limitations" in result
        assert result["n_states"] == 3
