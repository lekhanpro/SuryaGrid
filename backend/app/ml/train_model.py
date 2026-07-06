"""Model training - scikit-learn regressors for solar forecasting.

Trains on the augmented dataset. Target is `actual_generation_mw` when the dataset
provides real plant generation, otherwise `irradiance_w_m2` (the Kaggle case) - in
which case downstream converts irradiance to generation via pvlib.

Candidate models: RandomForest, GradientBoosting, HistGradientBoosting, and a
LinearRegression baseline. Metrics: MAE, RMSE, MAPE, R2. See docs/ML_PIPELINE.md.
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from app.ml import model_registry
from app.ml.feature_engineering import select_feature_columns

RANDOM_STATE = 42
MIN_SAMPLES = 20

# Candidate model factories (no heavy frameworks; scikit-learn only).
MODEL_FACTORIES = {
    "random_forest": lambda: RandomForestRegressor(
        n_estimators=120, random_state=RANDOM_STATE, n_jobs=-1
    ),
    "gradient_boosting": lambda: GradientBoostingRegressor(random_state=RANDOM_STATE),
    "hist_gradient_boosting": lambda: HistGradientBoostingRegressor(random_state=RANDOM_STATE),
    "linear": lambda: LinearRegression(),
}

_SOURCE_REFERENCES = ["SRC-KAGGLE-SOLAR-001", "SRC-OPENMETEO-001", "SRC-PVLIB-001"]


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float | None:
    mask = np.abs(y_true) > 1e-6
    if mask.sum() == 0:
        return None
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "mape": (round(m, 4) if (m := _mape(y_true, y_pred)) is not None else None),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
    }


def _resolve_target(df: pd.DataFrame, target: str | None) -> str:
    if target:
        return target
    if "actual_generation_mw" in df.columns and df["actual_generation_mw"].notna().sum() > 0:
        return "actual_generation_mw"
    return "irradiance_w_m2"


def _prepare(df: pd.DataFrame, target: str, feature_columns: list[str] | None):
    if feature_columns is None:
        feature_columns = select_feature_columns(df, target)
    if not feature_columns:
        raise ValueError("No usable numeric feature columns in the dataset.")
    work = df.copy()
    # Exclude quality-flagged rows if present.
    if "quality_flag" in work.columns:
        work = work[work["quality_flag"] == 1]
    work = work.dropna(subset=[target])
    if len(work) < MIN_SAMPLES:
        raise ValueError(
            f"Not enough samples to train ({len(work)} < {MIN_SAMPLES}). "
            "Load more data (Kaggle dataset or a longer weather archive)."
        )
    x = work[feature_columns].fillna(0.0).to_numpy()
    y = pd.to_numeric(work[target], errors="coerce").fillna(0.0).to_numpy()
    return x, y, feature_columns


def _fit_eval(model_name: str, x_train, x_test, y_train, y_test):
    factory = MODEL_FACTORIES.get(model_name)
    if factory is None:
        raise ValueError(f"Unknown model '{model_name}'. Options: {list(MODEL_FACTORIES)}")
    est = factory()
    est.fit(x_train, y_train)
    metrics = _metrics(y_test, est.predict(x_test))
    return est, metrics


def train(
    df: pd.DataFrame,
    target: str | None = None,
    model_name: str = "random_forest",
    feature_columns: list[str] | None = None,
    test_size: float = 0.2,
    dataset_name: str = "augmented_dataset",
) -> dict:
    """Train one model (or 'auto' to select the best by test RMSE) and persist it."""
    target = _resolve_target(df, target)
    x, y, feature_columns = _prepare(df, target, feature_columns)
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=test_size, random_state=RANDOM_STATE
    )

    candidates_tried: dict[str, dict] = {}
    if model_name == "auto":
        best_name, best_est, best_metrics = None, None, None
        for name in MODEL_FACTORIES:
            est, metrics = _fit_eval(name, x_train, x_test, y_train, y_test)
            candidates_tried[name] = metrics
            if best_metrics is None or metrics["rmse"] < best_metrics["rmse"]:
                best_name, best_est, best_metrics = name, est, metrics
        chosen_name, estimator, metrics = best_name, best_est, best_metrics
    else:
        estimator, metrics = _fit_eval(model_name, x_train, x_test, y_train, y_test)
        chosen_name = model_name
        candidates_tried[model_name] = metrics

    training_date = datetime.now(UTC).isoformat()
    target_type = "generation" if target == "actual_generation_mw" else "irradiance"
    metadata = {
        "model_version": datetime.now(UTC).strftime("%Y%m%d%H%M%S"),
        "model_type": chosen_name,
        "estimator_class": type(estimator).__name__,
        "target": target,
        "target_type": target_type,
        "columns_used": feature_columns,
        "training_dataset": dataset_name,
        "n_samples": int(len(x)),
        "n_train": int(len(x_train)),
        "n_test": int(len(x_test)),
        "metrics": metrics,
        "candidates_tried": candidates_tried,
        "training_date": training_date,
        "source_references": _SOURCE_REFERENCES,
        "limitations": (
            "Decision-support estimate, not a settlement of record. "
            + (
                "Model predicts irradiance (dataset has no plant generation); "
                "generation is derived via the pvlib pipeline. "
                if target_type == "irradiance"
                else ""
            )
            + "Accuracy depends on how representative the training data is of the "
            "target site/season. Retrain when new data is ingested."
        ),
    }
    model_registry.save_model(estimator, feature_columns, metadata)
    return metadata
