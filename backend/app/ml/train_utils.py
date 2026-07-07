"""Shared training helpers for Phase 1.7 agent trainers.

Chronological (time-ordered) train/test split - never a random shuffle - because
every dataset here is a time series and a random split would leak the future into
the past. Metrics and .pkl persistence to backend/models/trained/ are centralised.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)

from app.ml import provenance as prov

RANDOM_STATE = 42


def chronological_split(
    df: pd.DataFrame,
    feature_cols: list[str],
    target: str,
    *,
    order_col: str,
    test_frac: float = 0.2,
):
    """Sort by time, take the first (1-test_frac) rows as train, the rest as test."""
    work = df.sort_values(order_col).reset_index(drop=True)
    work = work.dropna(subset=[*feature_cols, target])
    n = len(work)
    if n == 0:
        raise ValueError("No rows left after dropping NaNs in features/target.")
    cut = int(n * (1.0 - test_frac))
    train, test = work.iloc[:cut], work.iloc[cut:]
    x_train = train[feature_cols].to_numpy(dtype=float)
    x_test = test[feature_cols].to_numpy(dtype=float)
    y_train = pd.to_numeric(train[target], errors="coerce").to_numpy()
    y_test = pd.to_numeric(test[target], errors="coerce").to_numpy()
    return x_train, x_test, y_train, y_test, {"n": n, "n_train": len(train), "n_test": len(test)}


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    mask = np.abs(y_true) > 1e-6
    mape = (
        round(float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0), 3)
        if mask.sum()
        else None
    )
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "mape_percent": mape,
        "r2": round(float(r2_score(y_true, y_pred)), 4),
    }


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_proba=None) -> dict:
    out = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
    }
    if y_proba is not None and len(np.unique(y_true)) > 1:
        try:
            out["roc_auc"] = round(float(roc_auc_score(y_true, y_proba)), 4)
        except ValueError:
            out["roc_auc"] = None
    return out


def save_pkl(bundle: dict, filename: str) -> Path:
    """Persist a model bundle to backend/models/trained/<filename>."""
    prov.trained_models_dir().mkdir(parents=True, exist_ok=True)
    path = prov.trained_models_dir() / filename
    joblib.dump(bundle, path)
    return path


def load_training_frame(filename: str) -> pd.DataFrame | None:
    return prov.read_parquet(filename)
