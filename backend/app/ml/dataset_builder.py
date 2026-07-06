"""Augmented dataset builder.

Joins a normalized source frame (Kaggle history and/or live-weather features) with
site attributes, schedule, and nearest-substation distance into the canonical
augmented schema (feature_engineering.AUGMENTED_COLUMNS), then runs data-quality
validation and flags bad rows. See docs/ML_PIPELINE.md.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from app.ml import data_quality
from app.ml.feature_engineering import AUGMENTED_COLUMNS, add_time_features, ensure_columns

AUGMENTED_FILENAME = "augmented_dataset.csv"

# Typical crystalline-silicon module efficiency. FALLBACK_DEFAULT.
# SOURCE: docs/SOURCE_REGISTRY.md (section 3.5 / operator parameters).
DEFAULT_PANEL_EFFICIENCY = 0.18


def _processed_dir() -> Path:
    override = os.environ.get("SURYAGRID_DATA_DIR")
    base = Path(override) if override else Path(__file__).resolve().parents[2] / "data"
    return base / "processed"


def augmented_path() -> Path:
    return _processed_dir() / AUGMENTED_FILENAME


def weather_points_to_frame(weather_points, source_provider: str = "open-meteo") -> pd.DataFrame:
    """Convert a list of providers.base.WeatherPoint into a source frame."""
    rows = []
    for p in weather_points:
        rows.append(
            {
                "timestamp": p.timestamp,
                "irradiance_w_m2": p.ghi_w_m2,
                "cloud_cover_percent": p.cloud_cover_percent,
                "temperature_c": p.temperature_c,
                "wind_speed_mps": p.wind_speed_mps,
                "humidity_percent": getattr(p, "humidity_percent", 0.0),
                "pressure_hpa": getattr(p, "pressure_hpa", 0.0),
                "precipitation_probability_percent": getattr(
                    p, "precipitation_probability_percent", 0.0
                ),
                "source_provider": source_provider,
            }
        )
    return pd.DataFrame(rows)


def build_augmented(
    source_df: pd.DataFrame,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    site_capacity_mw: float | None = None,
    panel_efficiency: float | None = None,
    nearest_substation_distance_km: float | None = None,
    scheduled_generation_mw: float | None = None,
    actual_generation_col: str | None = None,
    validate: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """Build the canonical augmented dataset from a normalized source frame.

    Returns (augmented_df, quality_report). Scalar context (site/schedule/substation)
    is broadcast across rows. Missing canonical columns are added as NaN so the
    schema is always complete and self-describing.
    """
    if source_df is None or source_df.empty:
        empty = ensure_columns(pd.DataFrame(), AUGMENTED_COLUMNS)
        return empty, {"rows": 0, "issues": {}, "passed": True, "clean_rows": 0, "total_flagged": 0}

    df = source_df.copy()
    if "timestamp" not in df.columns:
        raise ValueError("source_df must contain a 'timestamp' column")

    # Time features
    if not {"hour_of_day", "day_of_year", "month"}.issubset(df.columns):
        df = add_time_features(df)

    # Broadcast scalar context
    if latitude is not None:
        df["latitude"] = latitude
    if longitude is not None:
        df["longitude"] = longitude
    if site_capacity_mw is not None:
        df["site_capacity_mw"] = site_capacity_mw
    df["panel_efficiency"] = (
        panel_efficiency if panel_efficiency is not None else DEFAULT_PANEL_EFFICIENCY
    )
    if nearest_substation_distance_km is not None:
        df["nearest_substation_distance_km"] = nearest_substation_distance_km
    if scheduled_generation_mw is not None:
        df["scheduled_generation_mw"] = scheduled_generation_mw

    # Target generation column mapping (if the source has real plant generation)
    if actual_generation_col and actual_generation_col in df.columns:
        df["actual_generation_mw"] = pd.to_numeric(df[actual_generation_col], errors="coerce")

    if "source_provider" not in df.columns:
        df["source_provider"] = "unknown"

    # Enforce canonical schema (adds missing columns as NaN, fixes order)
    df = ensure_columns(df, AUGMENTED_COLUMNS)

    report: dict = {"rows": len(df), "issues": {}, "passed": True}
    if validate:
        df, report = data_quality.validate_and_flag(df, capacity_mw=site_capacity_mw)
    return df, report


def save_augmented(df: pd.DataFrame) -> Path:
    path = augmented_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def load_augmented() -> pd.DataFrame | None:
    path = augmented_path()
    if not path.exists():
        return None
    return pd.read_csv(path)


def augmented_exists() -> bool:
    return augmented_path().exists()
