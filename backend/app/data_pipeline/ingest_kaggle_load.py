"""Ingest shubhamvashisht/hourly-load-india-electrical-load-forecasting (REAL_INDIA).

Real hourly national + regional demand (MW) from 2019. The Southern Region column is the
closest regional proxy to Karnataka but is a multi-state aggregate, so the label stays
REAL_INDIA (not REAL_KARNATAKA). Requires openpyxl to read the .xlsx.

    python -m app.data_pipeline.ingest_kaggle_load --data-mode real
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from app.data_pipeline import _common as C
from app.ml import provenance as prov

SLUG = "shubhamvashisht/hourly-load-india-electrical-load-forecasting"
URL = (
    "https://www.kaggle.com/datasets/shubhamvashisht/hourly-load-india-electrical-load-forecasting"
)
OUT = "kaggle_load_processed.parquet"
XLSX = "load/hourly_load_india/hourlyLoadDataIndia.xlsx"


def build() -> pd.DataFrame:
    path = C.raw_kaggle_dir() / XLSX
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    raw = pd.read_excel(path)
    cols = {c.lower(): c for c in raw.columns}

    def find(*keys):
        for k in keys:
            for lc, orig in cols.items():
                if all(t in lc for t in k):
                    return orig
        return None

    dt = find(("datetime",), ("date",), ("time",))
    nat = find(("national", "demand"))
    south = find(("southern", "demand"))
    if dt is None or nat is None:
        raise ValueError(f"Could not detect datetime/national columns in {list(raw.columns)}")

    ts = pd.to_datetime(raw[dt], errors="coerce")
    out = pd.DataFrame(
        {
            "timestamp": ts,
            "national_demand_mw": pd.to_numeric(raw[nat], errors="coerce"),
            "southern_region_demand_mw": (
                pd.to_numeric(raw[south], errors="coerce") if south else pd.NA
            ),
        }
    ).dropna(subset=["timestamp", "national_demand_mw"])
    out = out[out["timestamp"].dt.year >= 2000].sort_values("timestamp")
    out["timestamp"] = out["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    out = C.stamp_metadata(
        out,
        source_name="Hourly Load India (National + regional demand)",
        kaggle_slug=SLUG,
        source_url=URL,
        geography="India (National; Southern Region proxy for Karnataka)",
        source_label=prov.REAL_INDIA,
        data_type="electricity_load",
    )
    out["data_granularity"] = "hourly"
    out["quality_score"] = C.row_quality_score(out, ["national_demand_mw"])
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-mode", default="real", choices=["real", "demo"])
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    C.require_real_mode(args.data_mode)
    df = build()
    path = C.processed_kaggle_dir() / OUT
    df.to_parquet(path, index=False)
    C.log("ingest_load", f"wrote {OUT}: {len(df)} rows -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
