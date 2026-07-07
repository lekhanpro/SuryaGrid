"""Ingest the anikannal/solar-power-generation-data Kaggle dataset (REAL_INDIA PV).

Joins per-inverter generation (AC/DC power) to plant-level weather (irradiation, ambient
and module temperature) on a format-robust timestamp, for both plants. Output is a single
processed parquet with real AC power as the modelling target. No synthetic data.

    python -m app.data_pipeline.ingest_kaggle_pv_generation --data-mode real
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from app.data_pipeline import _common as C
from app.ml import provenance as prov

SLUG = "anikannal/solar-power-generation-data"
URL = "https://www.kaggle.com/datasets/anikannal/solar-power-generation-data"
OUT = "kaggle_pv_generation_processed.parquet"
SUBDIR = "pv_generation/anikannal_solar_power_generation"

PLANTS = [
    ("Plant_1_Generation_Data.csv", "Plant_1_Weather_Sensor_Data.csv", 1),
    ("Plant_2_Generation_Data.csv", "Plant_2_Weather_Sensor_Data.csv", 2),
]


def _parse_dt(series: pd.Series) -> pd.Series:
    # Files mix "DD-MM-YYYY HH:MM" and ISO "YYYY-MM-DD HH:MM:SS"; dayfirst handles the
    # ambiguous DD-MM case and is ignored for unambiguous ISO strings.
    return pd.to_datetime(series, dayfirst=True, errors="coerce")


def build() -> pd.DataFrame:
    base = C.raw_kaggle_dir() / SUBDIR
    frames = []
    for gen_file, wx_file, plant_no in PLANTS:
        gpath, wpath = base / gen_file, base / wx_file
        if not gpath.exists() or not wpath.exists():
            C.log("ingest_pv", f"MISSING {gpath.name}/{wpath.name}; skipping plant {plant_no}")
            continue
        gen = pd.read_csv(gpath)
        wx = pd.read_csv(wpath)
        gen["timestamp"] = _parse_dt(gen["DATE_TIME"])
        wx["timestamp"] = _parse_dt(wx["DATE_TIME"])
        gen = gen.dropna(subset=["timestamp"])
        wx = wx.dropna(subset=["timestamp"])
        merged = gen.merge(
            wx[["timestamp", "AMBIENT_TEMPERATURE", "MODULE_TEMPERATURE", "IRRADIATION"]],
            on="timestamp",
            how="inner",
        )
        merged["plant_no"] = plant_no
        frames.append(merged)
        C.log("ingest_pv", f"plant {plant_no}: gen={len(gen)} wx={len(wx)} joined={len(merged)}")

    if not frames:
        raise FileNotFoundError("No anikannal PV files found under raw/kaggle.")

    df = pd.concat(frames, ignore_index=True)
    out = pd.DataFrame(
        {
            "timestamp": df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "plant_no": df["plant_no"],
            "inverter_key": df["SOURCE_KEY"],
            "ac_power": pd.to_numeric(df["AC_POWER"], errors="coerce"),
            "dc_power": pd.to_numeric(df["DC_POWER"], errors="coerce"),
            "irradiation": pd.to_numeric(df["IRRADIATION"], errors="coerce"),
            "ambient_temperature_c": pd.to_numeric(df["AMBIENT_TEMPERATURE"], errors="coerce"),
            "module_temperature_c": pd.to_numeric(df["MODULE_TEMPERATURE"], errors="coerce"),
            "daily_yield": pd.to_numeric(df.get("DAILY_YIELD"), errors="coerce"),
        }
    ).dropna(subset=["ac_power", "irradiation"])

    out["hour_of_day"] = pd.to_datetime(out["timestamp"]).dt.hour
    out = C.stamp_metadata(
        out,
        source_name="Solar Power Generation Data (anikannal)",
        kaggle_slug=SLUG,
        source_url=URL,
        geography="India (unspecified plant site)",
        source_label=prov.REAL_INDIA,
        data_type="pv_generation",
    )
    out["quality_score"] = C.row_quality_score(
        out, ["ac_power", "irradiation", "ambient_temperature_c", "module_temperature_c"]
    )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-mode", default="real", choices=["real", "demo"])
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    C.require_real_mode(args.data_mode)
    df = build()
    path = C.processed_kaggle_dir() / OUT
    df.to_parquet(path, index=False)
    C.log("ingest_pv", f"wrote {OUT}: {len(df)} rows, {out_cols(df)} -> {path}")
    return 0


def out_cols(df: pd.DataFrame) -> str:
    return f"AC max={df['ac_power'].max():.1f}, IRR max={df['irradiation'].max():.3f}"


if __name__ == "__main__":
    raise SystemExit(main())
