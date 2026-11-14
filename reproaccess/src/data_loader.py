"""Load processed ReproAccess datasets with availability metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"


@dataclass
class DatasetStatus:
    name: str
    available: bool
    path: Optional[Path]
    message: str
    source_url: str = ""
    expected_format: str = ""


def _read_table(stem: str) -> tuple[Optional[pd.DataFrame], Optional[Path]]:
    parquet = PROCESSED / f"{stem}.parquet"
    csv = PROCESSED / f"{stem}.csv"
    if parquet.exists():
        return pd.read_parquet(parquet), parquet
    if csv.exists():
        return pd.read_csv(csv), csv
    return None, None


def status_for(
    name: str,
    stem: str,
    source_url: str,
    expected_format: str,
) -> DatasetStatus:
    df, path = _read_table(stem)
    if df is not None and not df.empty:
        return DatasetStatus(
            name=name,
            available=True,
            path=path,
            message=f"Loaded {len(df):,} rows from {path.name}",
            source_url=source_url,
            expected_format=expected_format,
        )
    return DatasetStatus(
        name=name,
        available=False,
        path=None,
        message="Data unavailable. Run scripts/ingest_data.py then scripts/clean_data.py.",
        source_url=source_url,
        expected_format=expected_format,
    )


@lru_cache(maxsize=1)
def load_all() -> dict:
    """Return a dict of dataframes and dataset statuses."""
    tables = {}
    statuses = {}

    specs = [
        (
            "state_policy",
            "State abortion policy (KFF)",
            "https://www.kff.org/womens-health-policy/abortion-in-the-u-s-dashboard/",
            "CSV columns: state_fips,state_abbr,state_name,statutory_limit,policy_category,"
            "mandatory_waiting_period,waiting_period_length,source_url,extraction_date,is_synthetic",
        ),
        (
            "monthly_provision",
            "Monthly abortion provision (Guttmacher)",
            "https://osf.io/k4x7t/",
            "CSV columns: state_abbr,month,abortions_median,abortions_lower,abortions_upper,source_url",
        ),
        (
            "state_population",
            "Women 15–44 population (Census)",
            "https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/state/asrh/",
            "CSV columns: state_fips,state_name,state_abbr,women_15_44,year,source_url",
        ),
        (
            "state_metrics",
            "State metrics (derived)",
            "",
            "Built by scripts/build_geographic_metrics.py",
        ),
        (
            "county_access",
            "County access distances (derived)",
            "https://www2.census.gov/geo/tiger/GENZ2023/shp/",
            "Built by scripts/build_geographic_metrics.py",
        ),
        (
            "facilities",
            "Abortion facilities (ANSIRH optional)",
            "https://www.ansirh.org/",
            "CSV columns: facility_id,name,state_abbr,latitude,longitude",
        ),
    ]

    for stem, name, url, fmt in specs:
        df, path = _read_table(stem)
        tables[stem] = df
        if df is not None and not df.empty:
            statuses[stem] = DatasetStatus(
                name=name,
                available=True,
                path=path,
                message=f"Loaded {len(df):,} rows",
                source_url=url,
                expected_format=fmt,
            )
        else:
            statuses[stem] = DatasetStatus(
                name=name,
                available=False,
                path=None,
                message="Unavailable — not silently substituted with synthetic data.",
                source_url=url,
                expected_format=fmt,
            )

    # Parse dates
    if tables.get("monthly_provision") is not None:
        tables["monthly_provision"]["month"] = pd.to_datetime(tables["monthly_provision"]["month"])

    manifest_path = RAW / "source_manifest.json"
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    dict_path = PROCESSED / "data_dictionary.json"
    data_dictionary = {}
    if dict_path.exists():
        data_dictionary = json.loads(dict_path.read_text())

    return {
        "tables": tables,
        "statuses": statuses,
        "manifest": manifest,
        "data_dictionary": data_dictionary,
    }


def clear_cache() -> None:
    load_all.cache_clear()
