"""Data validation helpers for ReproAccess."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd


REQUIRED_STATE_POLICY_COLS = [
    "state_fips",
    "state_abbr",
    "state_name",
    "policy_category",
    "statutory_limit",
    "source_url",
    "extraction_date",
]

REQUIRED_PROVISION_COLS = [
    "state_abbr",
    "month",
    "abortions_median",
    "abortions_lower",
    "abortions_upper",
    "source_url",
]

REQUIRED_POPULATION_COLS = [
    "state_fips",
    "state_name",
    "women_15_44",
    "year",
    "source_url",
]

POLICY_CATEGORIES = {
    "total_ban",
    "early_gestational_limit",
    "later_gestational_limit",
    "viability_or_later",
    "no_gestational_limit",
    "unknown",
}


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def raise_if_invalid(self) -> None:
        if not self.ok:
            raise ValueError("; ".join(self.errors))


def _missing_columns(df: pd.DataFrame, required: Iterable[str]) -> list[str]:
    return [c for c in required if c not in df.columns]


def validate_policy_table(df: pd.DataFrame) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    missing = _missing_columns(df, REQUIRED_STATE_POLICY_COLS)
    if missing:
        errors.append(f"Policy table missing columns: {missing}")
    if "policy_category" in df.columns:
        bad = set(df["policy_category"].dropna().unique()) - POLICY_CATEGORIES
        if bad:
            errors.append(f"Unknown policy_category values: {sorted(bad)}")
    if "state_abbr" in df.columns and df["state_abbr"].duplicated().any():
        errors.append("Duplicate state_abbr in policy table")
    if len(df) < 50:
        warnings.append(f"Policy table has only {len(df)} rows (expected ~51 states+DC)")
    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def validate_provision_table(df: pd.DataFrame) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    missing = _missing_columns(df, REQUIRED_PROVISION_COLS)
    if missing:
        errors.append(f"Provision table missing columns: {missing}")
    if "abortions_median" in df.columns and (df["abortions_median"] < 0).any():
        errors.append("Negative abortion counts found")
    if df.empty:
        errors.append("Provision table is empty")
    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def validate_population_table(df: pd.DataFrame) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    missing = _missing_columns(df, REQUIRED_POPULATION_COLS)
    if missing:
        errors.append(f"Population table missing columns: {missing}")
    if "women_15_44" in df.columns and (df["women_15_44"] <= 0).any():
        warnings.append("Some population counts are <= 0")
    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def assert_no_synthetic_flag(df: pd.DataFrame, label: str) -> None:
    """Refuse to treat rows marked as synthetic as observed data."""
    if "is_synthetic" in df.columns and df["is_synthetic"].fillna(False).any():
        raise ValueError(
            f"{label} contains rows flagged is_synthetic=True. "
            "Synthetic values must not be presented as observed statistics."
        )
