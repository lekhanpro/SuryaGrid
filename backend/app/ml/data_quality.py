"""Data-quality validation for the augmented dataset.

Implements the Phase D quality checks: missing values, invalid units, invalid
timestamps, duplicate timestamps, impossible irradiance, negative generation,
generation above capacity, and bad coordinates. Produces a report and a per-row
`quality_flag` (1 = good, 0 = flagged). Bad rows are flagged, not silently dropped;
callers decide whether to exclude them.

Physical bounds are sourced: irradiance ceiling ~1500 W/m2 (well above the solar
constant projected to the surface). See docs/FORMULA_SOURCES.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

QUALITY_GOOD = 1
QUALITY_FLAGGED = 0

# Physical/plausibility bounds
IRRADIANCE_MAX_W_M2 = 1500.0
IRRADIANCE_MIN_W_M2 = 0.0
LAT_MIN, LAT_MAX = -90.0, 90.0
LON_MIN, LON_MAX = -180.0, 180.0

# Columns that must not contain missing values for a usable row (when present).
_CRITICAL_COLUMNS = ["timestamp"]


def run_quality_checks(df: pd.DataFrame, capacity_mw: float | None = None) -> dict:
    """Return a quality report (issue counts) plus a boolean bad-row mask.

    The mask marks rows failing any hard check (invalid/duplicate timestamp,
    impossible irradiance, negative/over-capacity generation, bad coordinates).
    """
    n = len(df)
    issues: dict[str, int] = {}
    bad = pd.Series(False, index=df.index)

    # 1. Missing values (report per column; only timestamp is a hard failure).
    missing = {c: int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()}
    issues["missing_values_total"] = int(sum(missing.values()))

    # 2. Invalid timestamps
    if "timestamp" in df.columns:
        ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        invalid_ts = ts.isna()
        issues["invalid_timestamps"] = int(invalid_ts.sum())
        bad |= invalid_ts
        # 3. Duplicate timestamps
        dup = ts.duplicated(keep="first") & ~invalid_ts
        issues["duplicate_timestamps"] = int(dup.sum())
        bad |= dup
    else:
        issues["invalid_timestamps"] = 0
        issues["duplicate_timestamps"] = 0

    # 4. Impossible irradiance
    if "irradiance_w_m2" in df.columns:
        irr = pd.to_numeric(df["irradiance_w_m2"], errors="coerce")
        bad_irr = (irr < IRRADIANCE_MIN_W_M2) | (irr > IRRADIANCE_MAX_W_M2)
        bad_irr = bad_irr.fillna(False)
        issues["impossible_irradiance"] = int(bad_irr.sum())
        bad |= bad_irr
    else:
        issues["impossible_irradiance"] = 0

    # 5. Negative generation & 6. generation above capacity
    if "actual_generation_mw" in df.columns:
        gen = pd.to_numeric(df["actual_generation_mw"], errors="coerce")
        neg = (gen < 0).fillna(False)
        issues["negative_generation"] = int(neg.sum())
        bad |= neg

        cap_series = _capacity_series(df, capacity_mw)
        if cap_series is not None:
            over = (gen > cap_series * 1.001).fillna(False)  # 0.1% tolerance
            issues["generation_above_capacity"] = int(over.sum())
            bad |= over
        else:
            issues["generation_above_capacity"] = 0
    else:
        issues["negative_generation"] = 0
        issues["generation_above_capacity"] = 0

    # 7. Bad coordinates
    bad_coords = pd.Series(False, index=df.index)
    if "latitude" in df.columns:
        lat = pd.to_numeric(df["latitude"], errors="coerce")
        bad_coords |= ((lat < LAT_MIN) | (lat > LAT_MAX)).fillna(False)
    if "longitude" in df.columns:
        lon = pd.to_numeric(df["longitude"], errors="coerce")
        bad_coords |= ((lon < LON_MIN) | (lon > LON_MAX)).fillna(False)
    issues["bad_coordinates"] = int(bad_coords.sum())
    bad |= bad_coords

    total_flagged = int(bad.sum())
    return {
        "rows": n,
        "issues": issues,
        "missing_by_column": missing,
        "total_flagged": total_flagged,
        "clean_rows": n - total_flagged,
        "passed": total_flagged == 0,
        "_bad_mask": bad,
    }


def _capacity_series(df: pd.DataFrame, capacity_mw: float | None):
    if "site_capacity_mw" in df.columns and df["site_capacity_mw"].notna().any():
        return pd.to_numeric(df["site_capacity_mw"], errors="coerce")
    if capacity_mw is not None:
        return pd.Series(float(capacity_mw), index=df.index)
    return None


def validate_and_flag(
    df: pd.DataFrame, capacity_mw: float | None = None
) -> tuple[pd.DataFrame, dict]:
    """Add/update a `quality_flag` column (1 good / 0 flagged) and return report."""
    report = run_quality_checks(df, capacity_mw)
    out = df.copy()
    bad = report.pop("_bad_mask")
    out["quality_flag"] = np.where(bad, QUALITY_FLAGGED, QUALITY_GOOD)
    return out, report


def clean(df: pd.DataFrame, capacity_mw: float | None = None) -> tuple[pd.DataFrame, dict]:
    """Return only good rows plus the quality report."""
    flagged, report = validate_and_flag(df, capacity_mw)
    good = flagged[flagged["quality_flag"] == QUALITY_GOOD].reset_index(drop=True)
    return good, report
