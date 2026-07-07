"""Ingest meenakshihihihihi/time-series-solar-irradiance-for-indian-cities (REAL_BENGALURU).

Per-city hourly NASA-POWER-derived irradiance/weather. Builds a timestamp from
YEAR/MO/DY/HR, drops the -999 fill value, and labels the Bengaluru extract REAL_BENGALURU
(other cities REAL_INDIA). GHI = ALLSKY_SFC_SW_DWN; clearness index = ALLSKY_KT (real).

    python -m app.data_pipeline.ingest_kaggle_solar --data-mode real
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from app.data_pipeline import _common as C
from app.ml import provenance as prov

SLUG = "meenakshihihihihi/time-series-solar-irradiance-for-indian-cities"
URL = "https://www.kaggle.com/datasets/meenakshihihihihi/time-series-solar-irradiance-for-indian-cities"
OUT = "kaggle_solar_processed.parquet"
SUBDIR = "solar/india_cities_irradiance"
FILL = -999.0


def _city_from_filename(name: str) -> str:
    base = name.lower().replace("solar", "").replace("irradiance", "").replace(".csv", "")
    base = base.strip()
    if "beng" in base:
        return "Bengaluru"
    return base.title().strip() or "Unknown"


def build() -> pd.DataFrame:
    base = C.raw_kaggle_dir() / SUBDIR
    files = sorted(base.glob("*.csv"))
    if not files:
        raise FileNotFoundError("No India-cities irradiance CSVs found under raw/kaggle.")
    frames = []
    for f in files:
        d = pd.read_csv(f)
        city = _city_from_filename(f.name)
        ts = pd.to_datetime(
            dict(year=d["YEAR"], month=d["MO"], day=d["DY"], hour=d["HR"]), errors="coerce"
        )
        out = pd.DataFrame(
            {
                "timestamp": ts,
                "city": city,
                "ghi_wm2": pd.to_numeric(d.get("ALLSKY_SFC_SW_DWN"), errors="coerce"),
                "clearness_index": pd.to_numeric(d.get("ALLSKY_KT"), errors="coerce"),
                "temperature_c": pd.to_numeric(d.get("T2M"), errors="coerce"),
                "pressure_kpa": pd.to_numeric(d.get("PS"), errors="coerce"),
                "precip_mm": pd.to_numeric(d.get("PRECTOTCORR"), errors="coerce"),
                "solar_zenith_deg": pd.to_numeric(d.get("SZA"), errors="coerce"),
            }
        )
        frames.append(out)
        C.log("ingest_solar", f"{f.name}: {len(out)} rows, city={city}")

    df = pd.concat(frames, ignore_index=True).dropna(subset=["timestamp"])
    # -999 is a fill value across all measured columns -> mark missing.
    for c in ["ghi_wm2", "clearness_index", "temperature_c", "pressure_kpa", "precip_mm"]:
        df[c] = df[c].replace(FILL, np.nan)
    df["hour_of_day"] = df["timestamp"].dt.hour
    df["day_of_year"] = df["timestamp"].dt.dayofyear
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    # Bengaluru rows are city-local; other cities are REAL_INDIA baselines.
    df["source_label"] = np.where(df["city"] == "Bengaluru", prov.REAL_BENGALURU, prov.REAL_INDIA)
    df = C.stamp_metadata(
        df,
        source_name="Time Series Solar Irradiance for Indian Cities",
        kaggle_slug=SLUG,
        source_url=URL,
        geography="Indian cities incl. Bengaluru",
        source_label=prov.REAL_BENGALURU,  # dataset-level; per-row overridden above
        data_type="solar_irradiance",
    )
    # per-row label (Bengaluru vs other) must win over the dataset-level stamp
    df["source_label"] = np.where(df["city"] == "Bengaluru", prov.REAL_BENGALURU, prov.REAL_INDIA)
    df["quality_score"] = C.row_quality_score(df, ["ghi_wm2", "temperature_c", "pressure_kpa"])
    return df


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-mode", default="real", choices=["real", "demo"])
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    C.require_real_mode(args.data_mode)
    df = build()
    path = C.processed_kaggle_dir() / OUT
    df.to_parquet(path, index=False)
    nb = int((df["city"] == "Bengaluru").sum())
    C.log("ingest_solar", f"wrote {OUT}: {len(df)} rows ({nb} Bengaluru) -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
