"""Train the load agent - an hourly electricity-demand forecast model.

Data reality: the only validated real load series available is INDIA NATIONAL hourly
demand (Grid-India/POSOCO-style "Hourly Demand Met in MW"), NOT Bengaluru-local. We
train on it honestly and label the domain shift: it is a REAL_INDIA baseline, usable
for pretraining, but production_ready=false for a Bengaluru target until local BESCOM/
KPTCL feeder load is connected.

If no valid load series exists, the model is skipped with
reason=INSUFFICIENT_LOCAL_LOAD_DATA.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor

from app.ml import provenance as prov
from app.ml import train_utils as tu
from app.ml.build_ml_datasets import F_LOAD_HISTORY, F_LOAD_TRAIN, MIN_LOAD_ROWS
from app.ml.provenance import REAL_INDIA

MODEL_PKL = "load_forecast_model.pkl"
CARD_JSON = "load_forecast_model_card.json"

FEATURES = [
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "doy_sin",
    "doy_cos",
    "is_weekend",
    "lag_24h",
    "lag_168h",
    "roll_24h_mean",
]
TARGET = "load_value"
ORDER_COL = "timestamp"
R2_PRODUCTION_THRESHOLD = 0.80


def _engineer(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("timestamp").reset_index(drop=True).copy()
    ts = pd.to_datetime(df["timestamp"])
    df["hour"] = ts.dt.hour
    df["dow"] = ts.dt.dayofweek
    df["doy"] = ts.dt.dayofyear
    df["is_weekend"] = (df["dow"] >= 5).astype(int)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24.0)
    df["dow_sin"] = np.sin(2 * np.pi * df["dow"] / 7.0)
    df["dow_cos"] = np.cos(2 * np.pi * df["dow"] / 7.0)
    df["doy_sin"] = np.sin(2 * np.pi * df["doy"] / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * df["doy"] / 365.25)
    df["lag_24h"] = df[TARGET].shift(24)
    df["lag_168h"] = df[TARGET].shift(168)
    df["roll_24h_mean"] = df[TARGET].rolling(24, min_periods=12).mean().shift(1)
    return df.dropna(subset=[*FEATURES, TARGET]).reset_index(drop=True)


def train(data_mode: str = "real") -> dict:
    hist = tu.load_training_frame(F_LOAD_HISTORY)
    if hist is None or len(hist) < MIN_LOAD_ROWS:
        return _skip("INSUFFICIENT_LOCAL_LOAD_DATA", non_local=False, local=False)

    scope = str(hist.get("region_scope", pd.Series(["unknown"])).iloc[0])
    src_label = str(hist.get("source_label", pd.Series([REAL_INDIA])).iloc[0])
    is_local = "bengaluru" in scope.lower() or "karnataka" in scope.lower()

    train_df = _engineer(hist)
    if len(train_df) < MIN_LOAD_ROWS:
        return _skip(
            "INSUFFICIENT_LOCAL_LOAD_DATA (too few rows after lag engineering)",
            non_local=False,
            local=is_local,
        )
    train_df["source_label"] = src_label
    train_df["region_scope"] = scope
    prov.write_parquet(
        train_df[[*FEATURES, TARGET, "timestamp", "source_label", "region_scope"]], F_LOAD_TRAIN
    )

    x_tr, x_te, y_tr, y_te, split = tu.chronological_split(
        train_df, FEATURES, TARGET, order_col=ORDER_COL
    )
    candidates = {
        "random_forest": RandomForestRegressor(
            n_estimators=200, max_depth=20, random_state=tu.RANDOM_STATE, n_jobs=-1
        ),
        "hist_gradient_boosting": HistGradientBoostingRegressor(
            max_iter=400, random_state=tu.RANDOM_STATE
        ),
    }
    best_name, best_est, best_metrics, tried = None, None, None, {}
    for name, est in candidates.items():
        est.fit(x_tr, y_tr)
        m = tu.regression_metrics(y_te, est.predict(x_te))
        tried[name] = m
        if best_metrics is None or m["rmse"] < best_metrics["rmse"]:
            best_name, best_est, best_metrics = name, est, m

    bundle = {
        "estimator": best_est,
        "feature_columns": FEATURES,
        "target": TARGET,
        "prediction_type": "load_forecast",
        "unit": "MW",
        "model_type": best_name,
        "region_scope": scope,
    }
    pkl_path = tu.save_pkl(bundle, MODEL_PKL)

    # Honest: national India data is REAL but NOT Bengaluru-local -> not production-ready
    # for a Bengaluru target regardless of fit quality.
    production_ready = is_local and best_metrics["r2"] >= R2_PRODUCTION_THRESHOLD
    reason = None
    if not production_ready:
        reason = (
            "INSUFFICIENT_LOCAL_LOAD_DATA: model trained on REAL_INDIA national demand "
            f"({scope}), not Bengaluru/Karnataka feeder load. High domain shift; usable as "
            "an India-level baseline / pretraining only."
        )

    card = prov.ModelCard(
        model_name="load_forecast_model",
        training_data_files=[F_LOAD_HISTORY, F_LOAD_TRAIN],
        training_data_sources=[
            {
                "name": "National-Level Electricity Load Curve Data (India) - Kaggle",
                "dataset": "smarthkaushal/energy-demand-profile",
                "url": "https://www.kaggle.com/datasets/smarthkaushal/energy-demand-profile",
                "label": REAL_INDIA,
                "geography": "India (national aggregate)",
                "measure": "Hourly Demand Met (MW)",
            }
        ],
        training_geography="India (national aggregate demand)",
        target_geography="Bengaluru, Karnataka, India",
        local_data_available=False,
        domain_shift_risk="HIGH",
        features=FEATURES,
        target=TARGET,
        train_rows=split["n_train"],
        test_rows=split["n_test"],
        train_test_split_method="chronological_80_20",
        metrics={"chosen_model": best_name, **best_metrics, "candidates": tried},
        limitations=[
            "Trained on India NATIONAL hourly demand, not Bengaluru/Karnataka load.",
            "National aggregate demand shape differs strongly from a city/feeder profile "
            "(domain shift HIGH). Do not use for Bengaluru DSM/settlement decisions.",
            "No metered BESCOM/KPTCL feeder load was available; connect it to make this local.",
        ],
        production_ready=production_ready,
        reason_if_not_production_ready=reason,
        uses_synthetic_data=False,
        synthetic_percentage=0.0,
        uses_non_local_data=False,  # India national is real Indian data, not foreign
        non_local_data_percentage=0.0,
        prediction_type="load_forecast",
        model_type=best_name,
        notes=[
            f"source_scope={scope}; source_label={src_label}.",
            "REAL_INDIA (national) is not foreign, but is NOT Bengaluru-local -> "
            "local_data_available=false, domain_shift_risk=HIGH.",
        ],
    )
    card_path = card.save(CARD_JSON)

    print(
        f"[train_load_agent] TRAINED {best_name} on REAL_INDIA national load | "
        f"R2={best_metrics['r2']} RMSE={best_metrics['rmse']} MW | "
        f"production_ready={production_ready} (domain shift HIGH)"
    )
    return {
        "agent": "load",
        "status": "TRAINED_NON_LOCAL",
        "model_file": str(pkl_path),
        "model_card": str(card_path),
        "training_parquet": str(prov.ml_data_dir() / F_LOAD_TRAIN),
        "prediction_type": "load_forecast",
        "metrics": best_metrics,
        "production_ready": production_ready,
        "geography": scope,
        "rows": split["n"],
    }


def _skip(reason: str, *, non_local: bool, local: bool) -> dict:
    print(f"[train_load_agent] SKIP: {reason}")
    prov.ModelCard(
        model_name="load_forecast_model",
        target="load_value",
        training_geography="unknown",
        local_data_available=local,
        domain_shift_risk="UNKNOWN",
        production_ready=False,
        reason_if_not_production_ready=reason,
        uses_non_local_data=non_local,
        prediction_type="load_forecast",
    ).save(CARD_JSON)
    return {"agent": "load", "status": "SKIPPED", "reason": reason}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--region", default="bengaluru")
    p.add_argument("--data-mode", default="real", choices=["real", "demo"])
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    print(json.dumps(train(args.data_mode), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
