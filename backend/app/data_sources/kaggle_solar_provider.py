"""Kaggle solar radiation dataset provider.

Ingests and normalizes the Kaggle "Solar Radiation Prediction" dataset
(dronio/SolarEnergy, NASA HI-SEAS). Two load paths:

  1. Kaggle API - when KAGGLE_USERNAME / KAGGLE_KEY are set (never commit kaggle.json).
  2. Manual placement - drop the CSV in backend/data/raw/kaggle/ (no credentials).

Detection is explicit: if no data is present the provider reports
`loaded=False` with detail "Kaggle dataset not loaded". It never silently
substitutes other data.

SOURCE: docs/SOURCE_REGISTRY.md#src-kaggle-solar-001 (SRC-KAGGLE-SOLAR-001)
Unit conversions: docs/FORMULA_SOURCES.md#unit-conversions
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from app.core.logging import logger
from app.data_sources.base_provider import (
    TYPE_HISTORICAL_DATASET,
    DataProvider,
    ProviderStatus,
)

KAGGLE_DATASET_SLUG = "dronio/SolarEnergy"
SOURCE_ID = "SRC-KAGGLE-SOLAR-001"

# Canonical augmented columns produced by normalization (subset relevant to Kaggle).
CANONICAL_COLUMNS = [
    "timestamp",
    "irradiance_w_m2",
    "temperature_c",
    "humidity_percent",
    "wind_speed_mps",
    "pressure_hpa",
    "wind_direction_deg",
]

# Unit conversion constants (standard). See docs/FORMULA_SOURCES.md#unit-conversions.
_INHG_TO_HPA = 33.8639
_MPH_TO_MPS = 0.44704


def _default_data_dir() -> Path:
    override = os.environ.get("SURYAGRID_DATA_DIR")
    if override:
        return Path(override) / "raw" / "kaggle"
    # backend/app/data_sources/kaggle_solar_provider.py -> backend/data/raw/kaggle
    return Path(__file__).resolve().parents[2] / "data" / "raw" / "kaggle"


def _f_to_c(f: pd.Series) -> pd.Series:
    return (f - 32.0) * 5.0 / 9.0


class KaggleSolarProvider(DataProvider):
    name = "kaggle-solar"
    source_id = SOURCE_ID
    provider_type = TYPE_HISTORICAL_DATASET

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or _default_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ---- detection ------------------------------------------------------
    def csv_files(self) -> list[Path]:
        return sorted(p for p in self.data_dir.glob("*.csv"))

    def is_loaded(self) -> bool:
        return len(self.csv_files()) > 0

    @staticmethod
    def credentials_configured() -> bool:
        return bool(os.environ.get("KAGGLE_USERNAME")) and bool(os.environ.get("KAGGLE_KEY"))

    # ---- ingestion ------------------------------------------------------
    def ingest_via_api(self, slug: str = KAGGLE_DATASET_SLUG) -> dict:
        """Download the dataset via the Kaggle API if credentials are set.

        Returns a status dict; never raises for the "no credentials" case.
        """
        if not self.credentials_configured():
            return {
                "ingested": False,
                "reason": "missing_credentials",
                "detail": "KAGGLE_USERNAME / KAGGLE_KEY not set. Place the CSV in "
                f"{self.data_dir} manually, or configure credentials.",
            }
        try:
            # Lazy import: the kaggle package authenticates on import.
            from kaggle.api.kaggle_api_extended import KaggleApi

            api = KaggleApi()
            api.authenticate()
            api.dataset_download_files(slug, path=str(self.data_dir), unzip=True)
            files = [p.name for p in self.csv_files()]
            return {
                "ingested": True,
                "slug": slug,
                "files": files,
                "detail": f"Downloaded {slug} to {self.data_dir}",
            }
        except ImportError:
            return {
                "ingested": False,
                "reason": "kaggle_package_missing",
                "detail": "The 'kaggle' package is not installed. Add it or place the CSV manually.",
            }
        except Exception as exc:  # network / auth / dataset errors
            logger.warning(f"Kaggle ingest failed: {exc}")
            return {"ingested": False, "reason": "error", "detail": str(exc)}

    # ---- normalization --------------------------------------------------
    def load_dataframe(self) -> pd.DataFrame:
        """Load and normalize the Kaggle CSV(s) into the canonical schema.

        Raises FileNotFoundError if nothing is loaded (caller must check is_loaded).
        """
        files = self.csv_files()
        if not files:
            raise FileNotFoundError(
                f"Kaggle dataset not loaded. No CSV in {self.data_dir}. "
                "Configure KAGGLE_USERNAME/KAGGLE_KEY or drop the CSV manually."
            )
        frames = [pd.read_csv(f) for f in files]
        raw = pd.concat(frames, ignore_index=True)
        return self._normalize(raw)

    def _normalize(self, raw: pd.DataFrame) -> pd.DataFrame:
        cols = {c.lower().strip(): c for c in raw.columns}
        out = pd.DataFrame()

        # timestamp from UNIXTime (epoch seconds) if present, else from Date/Time.
        if "unixtime" in cols:
            out["timestamp"] = pd.to_datetime(raw[cols["unixtime"]], unit="s", utc=True)
        elif "timestamp" in cols:
            out["timestamp"] = pd.to_datetime(raw[cols["timestamp"]], utc=True, errors="coerce")
        else:
            # Best-effort: combine Data + Time columns if available.
            date_col = cols.get("data") or cols.get("date")
            time_col = cols.get("time")
            if date_col and time_col:
                combined = raw[date_col].astype(str) + " " + raw[time_col].astype(str)
                out["timestamp"] = pd.to_datetime(combined, utc=True, errors="coerce")
            else:
                out["timestamp"] = pd.NaT

        # irradiance target
        if "radiation" in cols:
            out["irradiance_w_m2"] = pd.to_numeric(raw[cols["radiation"]], errors="coerce")
        elif "irradiance_w_m2" in cols:
            out["irradiance_w_m2"] = pd.to_numeric(raw[cols["irradiance_w_m2"]], errors="coerce")

        # temperature: Fahrenheit -> Celsius (HI-SEAS dataset is degF)
        if "temperature" in cols:
            out["temperature_c"] = _f_to_c(pd.to_numeric(raw[cols["temperature"]], errors="coerce"))
        elif "temperature_c" in cols:
            out["temperature_c"] = pd.to_numeric(raw[cols["temperature_c"]], errors="coerce")

        if "humidity" in cols:
            out["humidity_percent"] = pd.to_numeric(raw[cols["humidity"]], errors="coerce")

        # wind speed: mph -> m/s
        if "speed" in cols:
            out["wind_speed_mps"] = pd.to_numeric(raw[cols["speed"]], errors="coerce") * _MPH_TO_MPS
        elif "wind_speed_mps" in cols:
            out["wind_speed_mps"] = pd.to_numeric(raw[cols["wind_speed_mps"]], errors="coerce")

        # pressure: inHg -> hPa
        if "pressure" in cols:
            out["pressure_hpa"] = (
                pd.to_numeric(raw[cols["pressure"]], errors="coerce") * _INHG_TO_HPA
            )

        wd_col = cols.get("winddirection(degrees)") or cols.get("wind_direction_deg")
        if wd_col:
            out["wind_direction_deg"] = pd.to_numeric(raw[wd_col], errors="coerce")

        # Derived time features
        ts = out["timestamp"]
        out["hour_of_day"] = ts.dt.hour
        out["day_of_year"] = ts.dt.dayofyear
        out["month"] = ts.dt.month

        out["source_provider"] = self.name
        out = out.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
        return out

    # ---- status ---------------------------------------------------------
    def status(self) -> ProviderStatus:
        loaded = self.is_loaded()
        files = [p.name for p in self.csv_files()]
        record_count: int | None = None
        detail: str
        if loaded:
            try:
                record_count = sum(
                    sum(1 for _ in open(f, encoding="utf-8")) - 1 for f in self.csv_files()
                )
            except Exception:
                record_count = None
            detail = f"Kaggle dataset loaded: {files} (~{record_count} rows)"
        else:
            detail = "Kaggle dataset not loaded"
        return ProviderStatus(
            name=self.name,
            source_id=self.source_id,
            provider_type=self.provider_type,
            available=loaded,
            detail=detail,
            loaded=loaded,
            record_count=record_count,
            mode="manual" if loaded and not self.credentials_configured() else "real",
            extra={
                "data_dir": str(self.data_dir),
                "credentials_configured": self.credentials_configured(),
                "dataset_slug": KAGGLE_DATASET_SLUG,
                "files": files,
            },
        )
