"""Model registry - persistence of the trained model and its metadata.

Artifacts live in backend/models/:
  - solar_forecast_model.joblib   (the fitted sklearn estimator + feature columns)
  - model_metadata.json           (dataset, columns, target, model type, metrics,
                                    training date, source references, limitations)

See docs/ML_PIPELINE.md.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import joblib

MODEL_FILENAME = "solar_forecast_model.joblib"
METADATA_FILENAME = "model_metadata.json"


def _models_dir() -> Path:
    override = os.environ.get("SURYAGRID_MODELS_DIR")
    if override:
        return Path(override)
    # backend/app/ml/model_registry.py -> backend/models
    return Path(__file__).resolve().parents[2] / "models"


def model_path() -> Path:
    return _models_dir() / MODEL_FILENAME


def metadata_path() -> Path:
    return _models_dir() / METADATA_FILENAME


def is_trained() -> bool:
    return model_path().exists() and metadata_path().exists()


def save_model(estimator: Any, feature_columns: list[str], metadata: dict) -> dict:
    """Persist the estimator (with its feature columns) and metadata JSON."""
    d = _models_dir()
    d.mkdir(parents=True, exist_ok=True)
    joblib.dump({"estimator": estimator, "feature_columns": feature_columns}, model_path())
    with open(metadata_path(), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)
    return {"model_path": str(model_path()), "metadata_path": str(metadata_path())}


def load_model() -> dict | None:
    """Load {'estimator', 'feature_columns'} or None if not trained."""
    if not model_path().exists():
        return None
    return joblib.load(model_path())


def load_metadata() -> dict | None:
    if not metadata_path().exists():
        return None
    with open(metadata_path(), encoding="utf-8") as f:
        return json.load(f)


def status() -> dict:
    """Honest model status for the API."""
    if not is_trained():
        return {
            "trained": False,
            "detail": "No model trained. Ingest a dataset, build the augmented dataset, then train.",
            "model_path": str(model_path()),
        }
    meta = load_metadata() or {}
    return {
        "trained": True,
        "detail": "Model available.",
        "model_path": str(model_path()),
        "model_type": meta.get("model_type"),
        "target": meta.get("target"),
        "metrics": meta.get("metrics"),
        "training_date": meta.get("training_date"),
        "columns_used": meta.get("columns_used"),
        "model_version": meta.get("model_version"),
    }


def clear() -> bool:
    """Delete artifacts (used by tests). Returns True if anything was removed."""
    removed = False
    for p in (model_path(), metadata_path()):
        if p.exists():
            p.unlink()
            removed = True
    return removed
