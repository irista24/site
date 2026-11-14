"""Observational analytics for ReproAccess.

All associations are correlational. Do not interpret as causal effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


POLICY_ORDER = [
    "total_ban",
    "early_gestational_limit",
    "later_gestational_limit",
    "viability_or_later",
    "no_gestational_limit",
]

POLICY_LABELS = {
    "total_ban": "Total ban",
    "early_gestational_limit": "Early gestational limit (≤12 weeks)",
    "later_gestational_limit": "Later gestational limit (13–22 weeks)",
    "viability_or_later": "Viability / ~24 weeks+",
    "no_gestational_limit": "No gestational limit",
    "unknown": "Unknown",
}


@dataclass
class AssociationResult:
    table: pd.DataFrame
    notes: list[str]
    method: str


def summarize_by_policy(state_metrics: pd.DataFrame) -> AssociationResult:
    df = state_metrics.copy()
    df["policy_label"] = df["policy_category"].map(POLICY_LABELS).fillna(df["policy_category"])
    agg = (
        df.groupby(["policy_category", "policy_label"], as_index=False)
        .agg(
            n_states=("state_abbr", "count"),
            mean_provision_rate=("provision_rate_per_1000", "mean"),
            median_provision_rate=("provision_rate_per_1000", "median"),
            mean_miles=("mean_miles_to_nonban", "mean"),
            total_women_15_44=("women_15_44", "sum"),
            states_with_provision=("abortions_latest_month", lambda s: int(s.notna().sum())),
        )
        .sort_values("policy_category", key=lambda s: s.map({c: i for i, c in enumerate(POLICY_ORDER)}))
    )
    notes = [
        "Provision rates are observed only for states included in the Guttmacher Monthly "
        "Abortion Provision Study (typically states without total bans).",
        "Comparisons across policy categories are observational associations, not causal effects.",
        "States with total bans generally have missing in-state provision estimates by design.",
    ]
    return AssociationResult(table=agg, notes=notes, method="groupby descriptive summary")


def monthly_national_trend(provision: pd.DataFrame) -> pd.DataFrame:
    """Sum state medians by month for states present in the file (not a US total replicate)."""
    g = (
        provision.groupby("month", as_index=False)
        .agg(
            abortions_sum_of_state_medians=("abortions_median", "sum"),
            n_states=("state_abbr", "nunique"),
        )
        .sort_values("month")
    )
    return g


def state_series(provision: pd.DataFrame, state_abbr: str) -> pd.DataFrame:
    return (
        provision[provision["state_abbr"] == state_abbr]
        .sort_values("month")
        .reset_index(drop=True)
    )


def optional_panel_regression(
    provision: pd.DataFrame,
    policy: pd.DataFrame,
) -> Optional[dict]:
    """Optional two-way FE style OLS on log provision vs policy category dummies.

    Uses cross-sectional policy (latest KFF snapshot) merged onto monthly provision —
    policy does not vary within state in this extract, so state FE absorb the policy
    coefficient. We therefore report a pooled OLS with time FE only, clearly labeled
    as exploratory / non-causal.
    """
    try:
        import statsmodels.formula.api as smf
    except ImportError:
        return None

    df = provision.merge(
        policy[["state_abbr", "policy_category"]],
        on="state_abbr",
        how="inner",
    )
    if df.empty or df["policy_category"].nunique() < 2:
        return {
            "ok": False,
            "message": "Insufficient policy variation among states with provision data.",
        }

    df = df[df["abortions_median"] > 0].copy()
    df["log_abortions"] = np.log(df["abortions_median"])
    df["month_str"] = df["month"].dt.strftime("%Y-%m")
    df["policy_cat"] = pd.Categorical(df["policy_category"])

    try:
        model = smf.ols(
            "log_abortions ~ C(policy_cat) + C(month_str)",
            data=df,
        ).fit(cov_type="cluster", cov_kwds={"groups": df["state_abbr"]})
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Regression failed: {exc}"}

    coef = model.params.filter(like="policy_cat").to_dict()
    se = model.bse.filter(like="policy_cat").to_dict()
    return {
        "ok": True,
        "n_obs": int(model.nobs),
        "n_states": int(df["state_abbr"].nunique()),
        "r_squared": float(model.rsquared),
        "coefficients": {k: float(v) for k, v in coef.items()},
        "std_errors": {k: float(v) for k, v in se.items()},
        "limitations": [
            "Policy is a single cross-sectional snapshot (KFF as-of date), not a panel of policy changes.",
            "Coefficients are observational associations with month fixed effects and clustered SEs.",
            "Do not interpret as causal effects of policy on abortion provision.",
            "States with total bans are largely absent from provision data, inducing selection.",
            "Guttmacher estimates include uncertainty intervals not modeled in this OLS.",
        ],
        "formula": "log(abortions_median) ~ C(policy_category) + C(month)",
    }


def correlation_rate_vs_distance(state_metrics: pd.DataFrame) -> dict:
    df = state_metrics.dropna(subset=["provision_rate_per_1000", "mean_miles_to_nonban"])
    if len(df) < 5:
        return {"ok": False, "message": "Too few observations for correlation."}
    corr = float(df["provision_rate_per_1000"].corr(df["mean_miles_to_nonban"]))
    return {
        "ok": True,
        "pearson_r": corr,
        "n": len(df),
        "note": "Observational correlation only; distance proxy is to non-ban state centroids.",
    }
