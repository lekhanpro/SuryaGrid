"""Feature engineering for the augmented solar dataset.

Defines the canonical augmented schema (single source of truth) and helpers to
derive time features, align feature vectors for inference, and select model
feature columns. See docs/ML_PIPELINE.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Canonical augmented dataset columns (docs/DATA_SOURCE_CATALOG.md section 6).
AUGMENTED_COLUMNS: list[str] = [
    "timestamp",
    "hour_of_day",
    "day_of_year",
    "month",
    "latitude",
    "longitude",
    "irradiance_w_m2",
    "cloud_cover_percent",
    "temperature_c",
    "humidity_percent",
    "wind_speed_mps",
    "precipitation_probability_percent",
    "pressure_hpa",
    "site_capacity_mw",
    "panel_efficiency",
    "nearest_substation_distance_km",
    "scheduled_generation_mw",
    "actual_generation_mw",
    "source_provider",
    "quality_flag",
]

# Numeric feature columns a model may learn from (targets/metadata excluded).
FEATURE_COLUMNS: list[str] = [
    "hour_of_day",
    "day_of_year",
    "month",
    "latitude",
    "longitude",
    "cloud_cover_percent",
    "temperature_c",
    "humidity_percent",
    "wind_speed_mps",
    "precipitation_probability_percent",
    "pressure_hpa",
    "site_capacity_mw",
    "panel_efficiency",
    "nearest_substation_distance_km",
]

# Columns that are never model features.
NON_FEATURE_COLUMNS = {
    "timestamp",
    "source_provider",
    "quality_flag",
    "irradiance_w_m2",
    "actual_generation_mw",
    "scheduled_generation_mw",
}


def add_time_features(df: pd.DataFrame, ts_col: str = "timestamp") -> pd.DataFrame:
    """Add hour_of_day, day_of_year, month derived from a timestamp column."""
    out = df.copy()
    ts = pd.to_datetime(out[ts_col], utc=True, errors="coerce")
    out["hour_of_day"] = ts.dt.hour
    out["day_of_year"] = ts.dt.dayofyear
    out["month"] = ts.dt.month
    return out


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Return df with any missing canonical columns added as NaN (order preserved)."""
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = np.nan
    return out[columns]


def select_feature_columns(df: pd.DataFrame, target: str) -> list[str]:
    """Numeric columns usable as features: present, not target/metadata, not all-NaN."""
    cols: list[str] = []
    for col in df.columns:
        if col == target or col in NON_FEATURE_COLUMNS:
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        if df[col].notna().sum() == 0:
            continue
        cols.append(col)
    return cols


def feature_vector(features: dict, columns: list[str]) -> list[float]:
    """Build an ordered feature vector for inference; missing keys -> 0.0."""
    vec: list[float] = []
    for col in columns:
        val = features.get(col, 0.0)
        try:
            vec.append(float(val) if val is not None else 0.0)
        except (TypeError, ValueError):
            vec.append(0.0)
    return vec
