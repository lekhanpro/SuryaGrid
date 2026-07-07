"""Build ML training files from the PROCESSED Kaggle parquet (real data only).

Outputs (kaggle_-prefixed, written next to the Phase 1.7 Open-Meteo datasets so the
existing verified artifacts are NOT overwritten):
  * kaggle_pv_ac_training.parquet          (REAL_INDIA  - PV AC power target)
  * kaggle_solar_irradiance_training.parquet (REAL_BENGALURU - GHI target)
  * kaggle_cloud_training.parquet          (REAL_BENGALURU - irradiance-drop label)
  * kaggle_load_training.parquet           (REAL_INDIA  - demand target)

    python -m app.ml.build_kaggle_ml_datasets --data-mode real
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from app.data_pipeline import _common as C
from app.ml import provenance as prov

CLEARNESS_DROP_THRESHOLD = 0.5


def _cyc(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    ts = pd.to_datetime(df["timestamp"])
    h, doy, dow = ts.dt.hour, ts.dt.dayofyear, ts.dt.dayofweek
    df["hour_sin"] = np.sin(2 * np.pi * h / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * h / 24.0)
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    df["dow_sin"] = np.sin(2 * np.pi * dow / 7.0)
    df["dow_cos"] = np.cos(2 * np.pi * dow / 7.0)
    df["is_weekend"] = (dow >= 5).astype(int)
    return df


def _read(name: str) -> pd.DataFrame:
    path = C.processed_kaggle_dir() / name
    if not path.exists():
        raise FileNotFoundError(f"Processed file missing: {path}. Run the ingest scripts first.")
    return pd.read_parquet(path)


def build_pv() -> dict:
    df = _cyc(_read("kaggle_pv_generation_processed.parquet"))
    feats = ["irradiation", "ambient_temperature_c", "module_temperature_c", "hour_sin", "hour_cos"]
    out = df[[*feats, "ac_power", "timestamp", "plant_no"]].dropna(subset=[*feats, "ac_power"])
    out["source_label"] = prov.REAL_INDIA
    prov.write_parquet(out, "kaggle_pv_ac_training.parquet")
    return {"file": "kaggle_pv_ac_training.parquet", "rows": int(len(out)), "features": feats,
            "target": "ac_power", "label": prov.REAL_INDIA}


def build_solar() -> dict:
    df = _cyc(_read("kaggle_solar_processed.parquet"))
    df = df[df["city"] == "Bengaluru"].copy()
    feats = ["hour_sin", "hour_cos", "doy_sin", "doy_cos", "temperature_c", "pressure_kpa",
             "precip_mm", "solar_zenith_deg"]
    out = df[[*feats, "ghi_wm2", "timestamp"]].dropna(subset=[*feats, "ghi_wm2"])
    out = out[out["ghi_wm2"] >= 0]
    out["source_label"] = prov.REAL_BENGALURU
    prov.write_parquet(out, "kaggle_solar_irradiance_training.parquet")
    return {"file": "kaggle_solar_irradiance_training.parquet", "rows": int(len(out)),
            "features": feats, "target": "ghi_wm2", "label": prov.REAL_BENGALURU}


def build_cloud() -> dict:
    df = _cyc(_read("kaggle_solar_processed.parquet"))
    df = df[df["city"] == "Bengaluru"].copy()
    # Daylight = sun above horizon; label from the REAL clearness index (ALLSKY_KT).
    df = df[(df["solar_zenith_deg"] < 90) & df["clearness_index"].notna()]
    df = df[df["clearness_index"] >= 0]  # drop residual fill
    df["irradiance_drop_risk"] = (df["clearness_index"] < CLEARNESS_DROP_THRESHOLD).astype(int)
    feats = ["hour_sin", "hour_cos", "doy_sin", "doy_cos", "temperature_c", "pressure_kpa",
             "precip_mm"]
    out = df[[*feats, "irradiance_drop_risk", "clearness_index", "timestamp"]].dropna(
        subset=[*feats, "irradiance_drop_risk"]
    )
    out["source_label"] = prov.REAL_BENGALURU
    prov.write_parquet(out, "kaggle_cloud_training.parquet")
    return {"file": "kaggle_cloud_training.parquet", "rows": int(len(out)), "features": feats,
            "target": "irradiance_drop_risk",
            "positive_rate": round(float(out["irradiance_drop_risk"].mean()), 4),
            "label": prov.REAL_BENGALURU}


def build_load() -> dict:
    df = _cyc(_read("kaggle_load_processed.parquet")).sort_values("timestamp").reset_index(drop=True)
    tgt = "national_demand_mw"
    df["lag_24h"] = df[tgt].shift(24)
    df["lag_168h"] = df[tgt].shift(168)
    df["roll_24h_mean"] = df[tgt].rolling(24, min_periods=12).mean().shift(1)
    feats = ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "doy_sin", "doy_cos", "is_weekend",
             "lag_24h", "lag_168h", "roll_24h_mean"]
    out = df[[*feats, tgt, "timestamp"]].dropna(subset=[*feats, tgt])
    out["source_label"] = prov.REAL_INDIA
    prov.write_parquet(out, "kaggle_load_training.parquet")
    return {"file": "kaggle_load_training.parquet", "rows": int(len(out)), "features": feats,
            "target": tgt, "label": prov.REAL_INDIA}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-mode", default="real", choices=["real", "demo"])
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    C.require_real_mode(args.data_mode)
    prov.ensure_dirs()
    for fn in (build_pv, build_solar, build_cloud, build_load):
        r = fn()
        C.log("build_kaggle_ml", f"{r['file']}: {r['rows']} rows | target={r['target']} | {r['label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
