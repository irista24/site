"""Unit tests for geospatial color/policy helpers."""

from __future__ import annotations

import pandas as pd

from src.geospatial import POLICY_COLORS, attach_policy


class _FakeGDF(pd.DataFrame):
    """Minimal stand-in so attach_policy can merge without requiring a shapefile."""

    @property
    def _constructor(self):
        return _FakeGDF


def test_policy_colors_cover_categories():
    required = {
        "total_ban",
        "early_gestational_limit",
        "later_gestational_limit",
        "viability_or_later",
        "no_gestational_limit",
    }
    assert required.issubset(POLICY_COLORS.keys())


def test_attach_policy_sets_fill_color():
    gdf = _FakeGDF({"STUSPS": ["CA", "TX"], "geometry": [None, None]})
    policy = pd.DataFrame(
        {
            "state_abbr": ["CA", "TX"],
            "policy_category": ["no_gestational_limit", "total_ban"],
            "state_name": ["California", "Texas"],
        }
    )
    out = attach_policy(gdf, policy)
    assert out.loc[out["STUSPS"] == "CA", "fill_color"].iloc[0] == POLICY_COLORS["no_gestational_limit"]
    assert out.loc[out["STUSPS"] == "TX", "fill_color"].iloc[0] == POLICY_COLORS["total_ban"]
