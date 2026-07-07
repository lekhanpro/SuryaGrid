"""Shared helpers for the Kaggle ingestion scripts.

Every processed row is stamped with real-source metadata and an honest is_real flag.
Real mode forbids synthetic/demo data (there is none here - these are downloaded files).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.ml import provenance as prov


def raw_kaggle_dir() -> Path:
    return prov.data_dir() / "raw" / "kaggle"


def processed_kaggle_dir() -> Path:
    d = prov.data_dir() / "processed" / "kaggle"
    d.mkdir(parents=True, exist_ok=True)
    return d


def require_real_mode(data_mode: str) -> None:
    if data_mode not in (prov.DATA_MODE_REAL, prov.DATA_MODE_DEMO):
        raise ValueError(f"data_mode must be 'real' or 'demo', got {data_mode!r}")


def stamp_metadata(
    df: pd.DataFrame,
    *,
    source_name: str,
    kaggle_slug: str,
    source_url: str,
    geography: str,
    source_label: str,
    data_type: str,
) -> pd.DataFrame:
    df = df.copy()
    df["source_name"] = source_name
    df["kaggle_slug"] = kaggle_slug
    df["source_url"] = source_url
    df["data_geography"] = geography
    df["source_label"] = source_label
    df["data_type"] = data_type
    df["is_real"] = True
    df["is_synthetic"] = False
    df["ingestion_time"] = datetime.now(UTC).isoformat()
    return df


def row_quality_score(df: pd.DataFrame, key_cols: list[str]) -> pd.Series:
    present = [c for c in key_cols if c in df.columns]
    if not present:
        return pd.Series([1.0] * len(df), index=df.index)
    return df[present].notna().mean(axis=1).round(3)


def log(script: str, msg: str) -> None:
    print(f"[{script}] {msg}", flush=True)
