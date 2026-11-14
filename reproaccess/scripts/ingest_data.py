#!/usr/bin/env python3
"""Download and stage public datasets for ReproAccess.

Sources:
  - Guttmacher Monthly Abortion Provision Study (OSF)
  - Census Bureau cartographic boundaries (TIGER/Line cartographic)
  - Census Bureau state age-sex population estimates
  - KFF Abortion Policy indicators (manual CSV or extracted table)

Never fabricates facility coordinates, policy values, or outcomes.
"""

from __future__ import annotations

import csv
import json
import sys
import zipfile
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
META = RAW / "source_manifest.json"

GUTTMACHER_URL = "https://osf.io/tr6sw/download"
STATES_CB_URL = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_20m.zip"
COUNTIES_CB_URL = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_20m.zip"
POPEST_URL = (
    "https://www2.census.gov/programs-surveys/popest/datasets/"
    "2020-2023/state/asrh/sc-est2023-agesex-civ.csv"
)

# Public KFF State Health Facts — Gestational Limits (as of 2026-01-06).
# Extracted from https://www.kff.org/state-health-policy-data/state-indicator/gestational-limit-abortions/
# This is a curated extraction of the published indicator table, not synthetic data.
KFF_GESTATIONAL_LIMITS = [
    ("Alabama", "AL", "Abortion banned"),
    ("Alaska", "AK", "No gestational limit"),
    ("Arizona", "AZ", "Fetal viability"),
    ("Arkansas", "AR", "Abortion banned"),
    ("California", "CA", "Fetal viability"),
    ("Colorado", "CO", "No gestational limit"),
    ("Connecticut", "CT", "Fetal viability"),
    ("Delaware", "DE", "Fetal viability"),
    ("District of Columbia", "DC", "No gestational limit"),
    ("Florida", "FL", "6 weeks LMP"),
    ("Georgia", "GA", "6 weeks LMP"),
    ("Hawaii", "HI", "Fetal viability"),
    ("Idaho", "ID", "Abortion banned"),
    ("Illinois", "IL", "Fetal viability"),
    ("Indiana", "IN", "Abortion banned"),
    ("Iowa", "IA", "6 weeks LMP"),
    ("Kansas", "KS", "22 weeks LMP"),
    ("Kentucky", "KY", "Abortion banned"),
    ("Louisiana", "LA", "Abortion banned"),
    ("Maine", "ME", "Fetal viability"),
    ("Maryland", "MD", "No gestational limit"),
    ("Massachusetts", "MA", "24 weeks LMP"),
    ("Michigan", "MI", "No gestational limit"),
    ("Minnesota", "MN", "No gestational limit"),
    ("Mississippi", "MS", "Abortion banned"),
    ("Missouri", "MO", "Fetal viability"),
    ("Montana", "MT", "Fetal viability"),
    ("Nebraska", "NE", "12 weeks LMP"),
    ("Nevada", "NV", "24 weeks LMP"),
    ("New Hampshire", "NH", "24 weeks LMP"),
    ("New Jersey", "NJ", "No gestational limit"),
    ("New Mexico", "NM", "No gestational limit"),
    ("New York", "NY", "Fetal viability"),
    ("North Carolina", "NC", "12 weeks LMP"),
    ("North Dakota", "ND", "Abortion banned"),
    ("Ohio", "OH", "22 weeks LMP"),
    ("Oklahoma", "OK", "Abortion banned"),
    ("Oregon", "OR", "No gestational limit"),
    ("Pennsylvania", "PA", "24 weeks LMP"),
    ("Rhode Island", "RI", "Fetal viability"),
    ("South Carolina", "SC", "6 weeks LMP"),
    ("South Dakota", "SD", "Abortion banned"),
    ("Tennessee", "TN", "Abortion banned"),
    ("Texas", "TX", "Abortion banned"),
    ("Utah", "UT", "18 weeks LMP"),
    ("Vermont", "VT", "No gestational limit"),
    ("Virginia", "VA", "3rd trimester"),
    ("Washington", "WA", "Fetal viability"),
    ("West Virginia", "WV", "Abortion banned"),
    ("Wisconsin", "WI", "22 weeks LMP"),
    ("Wyoming", "WY", "Fetal viability"),
]

# Public KFF State Health Facts — Mandatory Waiting Periods (as of 2025-12-01).
# https://www.kff.org/other/state-indicator/mandatory-waiting-periods/
# "—" means abortion is banned (waiting period N/A under ban).
KFF_WAITING_PERIODS = {
    "AL": ("—", "—", "—"),
    "AK": ("No", "N/A", "N/A"),
    "AZ": ("Yes", "24 hours", "Yes"),
    "AR": ("—", "—", "—"),
    "CA": ("No", "N/A", "N/A"),
    "CO": ("No", "N/A", "N/A"),
    "CT": ("No", "N/A", "N/A"),
    "DE": ("No", "N/A", "N/A"),
    "DC": ("No", "N/A", "N/A"),
    "FL": ("Yes", "24 hours", "Yes"),
    "GA": ("Yes", "24 hours", "No"),
    "HI": ("No", "N/A", "N/A"),
    "ID": ("—", "—", "—"),
    "IL": ("No", "N/A", "N/A"),
    "IN": ("—", "—", "—"),
    "IA": ("Yes", "24 hours", "Yes"),
    "KS": ("No", "N/A", "N/A"),
    "KY": ("—", "—", "—"),
    "LA": ("—", "—", "—"),
    "ME": ("No", "N/A", "N/A"),
    "MD": ("No", "N/A", "N/A"),
    "MA": ("No", "N/A", "N/A"),
    "MI": ("No", "N/A", "N/A"),
    "MN": ("No", "N/A", "N/A"),
    "MS": ("—", "—", "—"),
    "MO": ("No", "N/A", "N/A"),
    "MT": ("No", "N/A", "N/A"),
    "NE": ("Yes", "24 hours", "No"),
    "NV": ("No", "N/A", "N/A"),
    "NH": ("No", "N/A", "N/A"),
    "NJ": ("No", "N/A", "N/A"),
    "NM": ("No", "N/A", "N/A"),
    "NY": ("No", "N/A", "N/A"),
    "NC": ("Yes", "72 hours", "Yes"),
    "ND": ("—", "—", "—"),
    "OH": ("No", "N/A", "N/A"),
    "OK": ("—", "—", "—"),
    "OR": ("No", "N/A", "N/A"),
    "PA": ("Yes", "24 hours", "No"),
    "RI": ("No", "N/A", "N/A"),
    "SC": ("Yes", "24 hours", "No"),
    "SD": ("—", "—", "—"),
    "TN": ("—", "—", "—"),
    "TX": ("—", "—", "—"),
    "UT": ("Yes", "72 hours", "Yes"),
    "VT": ("No", "N/A", "N/A"),
    "VA": ("No", "N/A", "N/A"),
    "WA": ("No", "N/A", "N/A"),
    "WV": ("—", "—", "—"),
    "WI": ("Yes", "24 hours", "Yes"),
    "WY": ("No", "N/A", "N/A"),
}

STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
    "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15",
    "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
    "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27",
    "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53",
    "WV": "54", "WI": "55", "WY": "56",
}


def download(url: str, dest: Path, timeout: int = 120) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "ReproAccess/0.1 (datathon research)"})
    try:
        with urlopen(req, timeout=timeout) as resp, open(dest, "wb") as f:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
        print(f"Downloaded {url} -> {dest}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED download {url}: {exc}", file=sys.stderr)
        return False


def unzip(zip_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)
    print(f"Extracted {zip_path} -> {out_dir}")


def categorize_limit(statutory: str) -> str:
    s = statutory.strip().lower()
    if "banned" in s:
        return "total_ban"
    if "no gestational limit" in s:
        return "no_gestational_limit"
    if "fetal viability" in s or "3rd trimester" in s or "24 weeks" in s:
        return "viability_or_later"
    if any(x in s for x in ("6 weeks", "12 weeks")):
        return "early_gestational_limit"
    if any(x in s for x in ("15 weeks", "18 weeks", "20 weeks", "22 weeks")):
        return "later_gestational_limit"
    return "unknown"


def write_kff_policy_csv() -> Path:
    """Write curated KFF gestational-limit + waiting-period extraction."""
    out = RAW / "kff_abortion_policy.csv"
    extraction_date = date.today().isoformat()
    gest_source = (
        "https://www.kff.org/state-health-policy-data/state-indicator/gestational-limit-abortions/"
    )
    wait_source = "https://www.kff.org/other/state-indicator/mandatory-waiting-periods/"
    rows = []
    for name, abbr, statutory in KFF_GESTATIONAL_LIMITS:
        wait, wait_len, two_trips = KFF_WAITING_PERIODS.get(abbr, ("unknown", "unknown", "unknown"))
        rows.append(
            {
                "state_name": name,
                "state_abbr": abbr,
                "state_fips": STATE_FIPS[abbr],
                "statutory_limit": statutory,
                "policy_category": categorize_limit(statutory),
                "mandatory_waiting_period": wait,
                "waiting_period_length": wait_len,
                "in_person_counseling_two_trips": two_trips,
                "gestational_source_url": gest_source,
                "gestational_as_of": "2026-01-06",
                "waiting_source_url": wait_source,
                "waiting_as_of": "2025-12-01",
                "extraction_date": extraction_date,
                "is_synthetic": False,
            }
        )
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote KFF policy extraction -> {out} ({len(rows)} states)")
    return out


def write_manifest(entries: list[dict]) -> None:
    META.write_text(json.dumps({"generated": date.today().isoformat(), "sources": entries}, indent=2))
    print(f"Wrote manifest -> {META}")


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []

    gutt_path = RAW / "guttmacher_monthly_provision.csv"
    if download(GUTTMACHER_URL, gutt_path):
        entries.append(
            {
                "name": "Guttmacher Monthly Abortion Provision Study",
                "url": "https://osf.io/k4x7t/",
                "file": str(gutt_path.relative_to(ROOT)),
                "status": "ok",
                "extraction_date": date.today().isoformat(),
            }
        )
    else:
        entries.append(
            {
                "name": "Guttmacher Monthly Abortion Provision Study",
                "url": "https://osf.io/k4x7t/",
                "file": str(gutt_path.relative_to(ROOT)),
                "status": "unavailable",
                "extraction_date": date.today().isoformat(),
            }
        )

    states_zip = RAW / "states_cartographic.zip"
    states_dir = RAW / "census_states"
    if download(STATES_CB_URL, states_zip):
        unzip(states_zip, states_dir)
        entries.append(
            {
                "name": "Census cartographic boundaries — states (2023 20m)",
                "url": STATES_CB_URL,
                "file": str(states_dir.relative_to(ROOT)),
                "status": "ok",
                "extraction_date": date.today().isoformat(),
            }
        )

    counties_zip = RAW / "counties_cartographic.zip"
    counties_dir = RAW / "census_counties"
    if download(COUNTIES_CB_URL, counties_zip):
        unzip(counties_zip, counties_dir)
        entries.append(
            {
                "name": "Census cartographic boundaries — counties (2023 20m)",
                "url": COUNTIES_CB_URL,
                "file": str(counties_dir.relative_to(ROOT)),
                "status": "ok",
                "extraction_date": date.today().isoformat(),
            }
        )

    pop_path = RAW / "sc-est2023-agesex-civ.csv"
    if download(POPEST_URL, pop_path):
        entries.append(
            {
                "name": "Census state age-sex civilian population estimates 2023",
                "url": POPEST_URL,
                "file": str(pop_path.relative_to(ROOT)),
                "status": "ok",
                "extraction_date": date.today().isoformat(),
            }
        )

    kff_path = write_kff_policy_csv()
    entries.append(
        {
            "name": "KFF Abortion Policy (gestational limits + waiting periods)",
            "url": "https://www.kff.org/womens-health-policy/abortion-in-the-u-s-dashboard/",
            "file": str(kff_path.relative_to(ROOT)),
            "status": "ok",
            "note": (
                "Curated extraction from KFF State Health Facts public indicator tables. "
                "If you prefer an official CSV export, place it at data/raw/kff_abortion_policy.csv "
                "using the column schema documented in README.md."
            ),
            "extraction_date": date.today().isoformat(),
        }
    )

    # Optional ANSIRH facilities — never invent coordinates.
    ansirh = RAW / "ansirh_facilities.csv"
    entries.append(
        {
            "name": "ANSIRH Abortion Facility Database (optional)",
            "url": "https://www.ansirh.org/",
            "file": str(ansirh.relative_to(ROOT)),
            "status": "available" if ansirh.exists() else "unavailable",
            "note": (
                "Optional. Place a CSV with columns facility_id,name,state_abbr,latitude,longitude "
                "to enable Mode B facility simulations. Coordinates are never fabricated."
            ),
            "extraction_date": date.today().isoformat(),
        }
    )

    write_manifest(entries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
