#!/usr/bin/env python3
"""Clean raw public datasets into analysis-ready Parquet/CSV tables."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
sys.path.insert(0, str(ROOT))

from src.validation import (  # noqa: E402
    assert_no_synthetic_flag,
    validate_policy_table,
    validate_population_table,
    validate_provision_table,
)

STATE_NAME_TO_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}


def clean_provision() -> pd.DataFrame:
    path = RAW / "guttmacher_monthly_provision.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    df = pd.read_csv(path)
    # Keep state-level monthly rows only (exclude US aggregate and ban-group rollups).
    valid_abbrs = set(STATE_NAME_TO_ABBR.values())
    df = df[df["state"].isin(valid_abbrs)].copy()
    df = df.rename(
        columns={
            "state": "state_abbr",
            "median": "abortions_median",
            "lowerbound": "abortions_lower",
            "upperbound": "abortions_upper",
            "source": "source_url",
            "publishdate": "publish_date",
        }
    )
    df["month"] = pd.to_datetime(df["month"])
    df["is_synthetic"] = False
    out_cols = [
        "state_abbr",
        "month",
        "abortions_median",
        "abortions_lower",
        "abortions_upper",
        "source_url",
        "notes",
        "publish_date",
        "is_synthetic",
    ]
    df = df[out_cols].sort_values(["state_abbr", "month"]).reset_index(drop=True)
    result = validate_provision_table(df)
    for w in result.warnings:
        print("WARN:", w)
    result.raise_if_invalid()
    assert_no_synthetic_flag(df, "provision")
    return df


def clean_policy() -> pd.DataFrame:
    path = RAW / "kff_abortion_policy.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run scripts/ingest_data.py or place a KFF CSV export "
            "with the documented schema."
        )
    df = pd.read_csv(path)
    df["source_url"] = df.get(
        "gestational_source_url",
        "https://www.kff.org/womens-health-policy/abortion-in-the-u-s-dashboard/",
    )
    if "is_synthetic" not in df.columns:
        df["is_synthetic"] = False
    result = validate_policy_table(df)
    for w in result.warnings:
        print("WARN:", w)
    result.raise_if_invalid()
    assert_no_synthetic_flag(df, "policy")
    return df


def clean_population() -> pd.DataFrame:
    """Women ages 15–44 from Census civilian age-sex estimates (SEX=2 female)."""
    path = RAW / "sc-est2023-agesex-civ.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    raw = pd.read_csv(path)
    # SUMLEV 040 = state; SEX 2 = female; AGE 15-44 inclusive
    state = raw[(raw["SUMLEV"] == 40) & (raw["SEX"] == 2)].copy()
    state = state[(state["AGE"] >= 15) & (state["AGE"] <= 44)]
    grouped = (
        state.groupby(["STATE", "NAME"], as_index=False)["POPEST2023_CIV"]
        .sum()
        .rename(
            columns={
                "STATE": "state_fips",
                "NAME": "state_name",
                "POPEST2023_CIV": "women_15_44",
            }
        )
    )
    grouped["state_fips"] = grouped["state_fips"].astype(int).astype(str).str.zfill(2)
    grouped["state_abbr"] = grouped["state_name"].map(STATE_NAME_TO_ABBR)
    grouped["year"] = 2023
    grouped["source_url"] = (
        "https://www2.census.gov/programs-surveys/popest/datasets/"
        "2020-2023/state/asrh/sc-est2023-agesex-civ.csv"
    )
    grouped["extraction_date"] = pd.Timestamp.today().date().isoformat()
    grouped["is_synthetic"] = False
    grouped = grouped.dropna(subset=["state_abbr"]).reset_index(drop=True)
    result = validate_population_table(grouped)
    for w in result.warnings:
        print("WARN:", w)
    result.raise_if_invalid()
    return grouped


def write_data_dictionary(paths: dict[str, Path]) -> None:
    dictionary = {
        "state_policy": {
            "description": "State abortion policy status from KFF State Health Facts",
            "columns": {
                "state_fips": "Two-digit state FIPS code",
                "state_abbr": "Postal abbreviation",
                "state_name": "State or DC name",
                "statutory_limit": "Statutory gestational limit text from KFF",
                "policy_category": "Normalized category used for mapping/analytics",
                "mandatory_waiting_period": "Yes/No/— (ban) from KFF waiting-period indicator",
                "waiting_period_length": "Length of waiting period when applicable",
                "source_url": "Primary KFF source URL",
                "extraction_date": "Date this file was extracted/curated",
                "is_synthetic": "Must be False for observed data",
            },
        },
        "monthly_provision": {
            "description": "Monthly abortion provision estimates (Guttmacher OSF)",
            "columns": {
                "state_abbr": "Postal abbreviation (states without total bans)",
                "month": "Month midpoint date",
                "abortions_median": "Posterior median estimate (rounded)",
                "abortions_lower": "Lower bound of uncertainty interval",
                "abortions_upper": "Upper bound of uncertainty interval",
                "source_url": "Guttmacher/OSF citation URL",
                "publish_date": "Guttmacher publish date string",
            },
        },
        "state_population": {
            "description": "Women ages 15–44 from Census civilian pop estimates 2023",
            "columns": {
                "state_fips": "Two-digit FIPS",
                "state_name": "State name",
                "state_abbr": "Postal abbreviation",
                "women_15_44": "Sum of female civilian population ages 15–44",
                "year": "Estimate year",
            },
        },
        "files": {k: str(v.relative_to(ROOT)) for k, v in paths.items()},
    }
    out = PROCESSED / "data_dictionary.json"
    out.write_text(json.dumps(dictionary, indent=2))
    print(f"Wrote {out}")


def main() -> int:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    provision = clean_provision()
    policy = clean_policy()
    population = clean_population()

    paths = {
        "monthly_provision": PROCESSED / "monthly_provision.parquet",
        "state_policy": PROCESSED / "state_policy.parquet",
        "state_population": PROCESSED / "state_population.parquet",
    }
    provision.to_parquet(paths["monthly_provision"], index=False)
    policy.to_parquet(paths["state_policy"], index=False)
    population.to_parquet(paths["state_population"], index=False)
    # Also write CSV copies for transparency / Streamlit Cloud without parquet tooling issues
    provision.to_csv(PROCESSED / "monthly_provision.csv", index=False)
    policy.to_csv(PROCESSED / "state_policy.csv", index=False)
    population.to_csv(PROCESSED / "state_population.csv", index=False)

    write_data_dictionary(paths)
    print(
        f"Cleaned rows — provision: {len(provision)}, policy: {len(policy)}, "
        f"population: {len(population)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
