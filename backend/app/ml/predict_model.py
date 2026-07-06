"""Model prediction - load the trained model and score feature vectors.

Aligns incoming features to the exact column order recorded in the model metadata,
so training and inference always agree. Returns the raw prediction (irradiance or
generation depending on the trained target); conversion to generation for the
irradiance case is handled by the ForecastAgent hybrid path. See docs/ML_PIPELINE.md.
"""

from __future__ import annotations

from app.ml import model_registry
from app.ml.feature_engineering import feature_vector


class ModelPredictor:
    def __init__(self):
        self._bundle: dict | None = None
        self._meta: dict | None = None
        self._loaded = False

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return self._bundle is not None
        self._bundle = model_registry.load_model()
        self._meta = model_registry.load_metadata()
        self._loaded = True
        return self._bundle is not None

    def reload(self) -> None:
        """Force a reload (call after (re)training)."""
        self._loaded = False
        self._bundle = None
        self._meta = None

    def is_available(self) -> bool:
        return self._ensure_loaded()

    def metadata(self) -> dict | None:
        self._ensure_loaded()
        return self._meta

    @property
    def target_type(self) -> str | None:
        meta = self.metadata()
        return meta.get("target_type") if meta else None

    def predict_one(self, features: dict) -> dict | None:
        """Predict for a single feature dict. Returns None if no model is available."""
        if not self._ensure_loaded():
            return None
        columns = self._bundle["feature_columns"]
        estimator = self._bundle["estimator"]
        vec = feature_vector(features, columns)
        value = float(estimator.predict([vec])[0])
        meta = self._meta or {}
        return {
            "value": round(value, 4),
            "target": meta.get("target"),
            "target_type": meta.get("target_type"),
            "model_version": meta.get("model_version"),
            "model_type": meta.get("model_type"),
        }


# Module-level singleton reused across requests.
predictor = ModelPredictor()
