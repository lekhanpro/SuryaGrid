"""Train the solar agent - a Bengaluru IRRADIANCE forecast model (GHI, W/m2).

It predicts shortwave radiation (GHI) from calendar + meteorological features on
REAL Open-Meteo coordinate data for Bengaluru. It does NOT predict PV generation:
there is no real local PV generation dataset, so plant output must be derived from
user-provided capacity via pvlib downstream (production_ready_for_pv_generation=false).
"""

from __future__ import annotations

import argparse
import json
import sys

from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor

from app.ml import provenance as prov
from app.ml import train_utils as tu
from app.ml.build_ml_datasets import F_SOLAR
from app.ml.provenance import REAL_COORDINATE_BASED

MODEL_PKL = "solar_forecast_model.pkl"
CARD_JSON = "solar_forecast_model_card.json"

FEATURES = [
    "hour_sin",
    "hour_cos",
    "doy_sin",
    "doy_cos",
    "month",
    "cloud_cover_percent",
    "temperature_c",
    "relative_humidity_percent",
    "wind_speed_mps",
    "surface_pressure_hpa",
    "precipitation_mm",
    "clearsky_ghi_wm2",
]
TARGET = "target_ghi_wm2"
ORDER_COL = "timestamp_local"
MIN_ROWS = 2000
R2_PRODUCTION_THRESHOLD = 0.75


def train(data_mode: str = "real") -> dict:
    df = tu.load_training_frame(F_SOLAR)
    if df is None or len(df) < MIN_ROWS:
        return _skip(f"solar training data missing or < {MIN_ROWS} rows")

    x_tr, x_te, y_tr, y_te, split = tu.chronological_split(
        df, FEATURES, TARGET, order_col=ORDER_COL
    )
    candidates = {
        "random_forest": RandomForestRegressor(
            n_estimators=200, max_depth=18, random_state=tu.RANDOM_STATE, n_jobs=-1
        ),
        "hist_gradient_boosting": HistGradientBoostingRegressor(
            max_iter=300, random_state=tu.RANDOM_STATE
        ),
    }
    best_name, best_est, best_metrics = None, None, None
    tried = {}
    for name, est in candidates.items():
        est.fit(x_tr, y_tr)
        m = tu.regression_metrics(y_te, est.predict(x_te))
        tried[name] = m
        if best_metrics is None or m["rmse"] < best_metrics["rmse"]:
            best_name, best_est, best_metrics = name, est, m

    prov.trained_models_dir().mkdir(parents=True, exist_ok=True)
    bundle = {
        "estimator": best_est,
        "feature_columns": FEATURES,
        "target": TARGET,
        "prediction_type": "irradiance_forecast",
        "unit": "W/m2",
        "model_type": best_name,
    }
    pkl_path = tu.save_pkl(bundle, MODEL_PKL)

    production_ready = best_metrics["r2"] >= R2_PRODUCTION_THRESHOLD
    card = prov.ModelCard(
        model_name="solar_forecast_model",
        training_data_files=[F_SOLAR, "bengaluru_weather_solar_history.parquet"],
        training_data_sources=[
            {
                "name": "Open-Meteo Historical Weather Archive",
                "url": "https://open-meteo.com/en/docs/historical-weather-api",
                "label": REAL_COORDINATE_BASED,
                "geography": "Bengaluru coordinates (12.9716, 77.5946)",
                "license": "Open-Meteo (CC-BY 4.0)",
            },
            {
                "name": "NASA POWER (daily GHI cross-check)",
                "url": "https://power.larc.nasa.gov/",
                "label": REAL_COORDINATE_BASED,
                "geography": "Bengaluru coordinates",
            },
            {
                "name": "pvlib Ineichen clear-sky (derived feature)",
                "url": "https://pvlib-python.readthedocs.io/",
                "label": prov.ESTIMATED_FROM_REAL,
            },
        ],
        training_geography="Bengaluru, Karnataka, India (coordinate-based)",
        target_geography="Bengaluru, Karnataka, India",
        local_data_available=True,
        domain_shift_risk="LOW",
        features=FEATURES,
        target=TARGET,
        train_rows=split["n_train"],
        test_rows=split["n_test"],
        train_test_split_method="chronological_80_20",
        metrics={"chosen_model": best_name, **best_metrics, "candidates": tried},
        limitations=[
            "Predicts global horizontal irradiance (GHI, W/m2), NOT PV plant generation.",
            "PV output must be derived from user-provided capacity via pvlib; it is never "
            "predicted directly (no real local PV generation dataset exists).",
            "Trained on Open-Meteo reanalysis at the city coordinate; a specific rooftop "
            "microclimate may differ. Retrain with on-site pyranometer data when available.",
            "Sub-hourly horizons resolve to the nearest hour (hourly source data).",
        ],
        production_ready=production_ready,
        reason_if_not_production_ready=(
            None
            if production_ready
            else f"R2 {best_metrics['r2']} < {R2_PRODUCTION_THRESHOLD} on chronological test set."
        ),
        uses_synthetic_data=False,
        synthetic_percentage=0.0,
        uses_non_local_data=False,
        non_local_data_percentage=0.0,
        prediction_type="irradiance_forecast",
        model_type=best_name,
        notes=[
            "production_ready_for_pv_generation=false (irradiance model only).",
            "NASA POWER vs Open-Meteo daily GHI agreement documented in the build manifest.",
        ],
    )
    card_path = card.save(CARD_JSON)

    result = {
        "agent": "solar",
        "status": "TRAINED",
        "model_file": str(pkl_path),
        "model_card": str(card_path),
        "prediction_type": "irradiance_forecast",
        "metrics": best_metrics,
        "chosen_model": best_name,
        "production_ready": production_ready,
        "rows": split["n"],
    }
    print(f"[train_solar_agent] TRAINED {best_name} | R2={best_metrics['r2']} "
          f"RMSE={best_metrics['rmse']} W/m2 | production_ready={production_ready}")
    return result


def _skip(reason: str) -> dict:
    print(f"[train_solar_agent] SKIP: {reason}")
    card = prov.ModelCard(
        model_name="solar_forecast_model",
        target="target_ghi_wm2",
        production_ready=False,
        reason_if_not_production_ready=reason,
        domain_shift_risk="UNKNOWN",
        prediction_type="irradiance_forecast",
    )
    card.save(CARD_JSON)
    return {"agent": "solar", "status": "SKIPPED", "reason": reason}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--region", default="bengaluru")
    p.add_argument("--data-mode", default="real", choices=["real", "demo"])
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    print(json.dumps(train(args.data_mode), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
