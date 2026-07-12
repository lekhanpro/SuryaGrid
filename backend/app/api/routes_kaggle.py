"""Phase 1.7 Kaggle-model API - serves the real Kaggle-trained models WITH provenance.

Read-only and self-contained (does not modify the Open-Meteo agents inference layer).
Every prediction/status response carries the dataset slug, geography, non-local flag,
and production readiness so the UI can never show a Kaggle-derived number without origin.

Endpoints (under /api/v1):
  GET  /kaggle/status        - all Kaggle model cards (metrics, geography, prod flag)
  POST /kaggle/pv/estimate   - PV AC-power estimate from irradiation + temperatures
"""

from __future__ import annotations

import json
from functools import lru_cache

import joblib
import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.ml import provenance as prov
from app.utils.response import success_response

router = APIRouter()

_CARDS = {
    "pv_ac": "kaggle_pv_ac_model_card.json",
    "solar_irradiance": "kaggle_solar_irradiance_bengaluru_model_card.json",
    "cloud_risk": "kaggle_cloud_risk_bengaluru_model_card.json",
    "load_forecast": "kaggle_load_forecast_model_card.json",
}
_PV_PKL = "kaggle_pv_ac_model.pkl"


def _card(filename: str) -> dict | None:
    p = prov.model_metadata_dir() / filename
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


@lru_cache(maxsize=8)
def _bundle(filename: str, mtime: float):
    p = prov.trained_models_dir() / filename
    return joblib.load(p) if p.exists() else None


def _pv_bundle():
    p = prov.trained_models_dir() / _PV_PKL
    return _bundle(_PV_PKL, p.stat().st_mtime) if p.exists() else None


def _slug(card: dict) -> str | None:
    srcs = (card or {}).get("training_data_sources") or []
    for s in srcs:
        n = s.get("name", "")
        if "Kaggle:" in n:
            return n.split("Kaggle:", 1)[1].strip()
    return None


class PVInput(BaseModel):
    irradiation: float
    ambient_temperature_c: float = 30.0
    module_temperature_c: float = 40.0
    hour_of_day: int = 12


@router.get("/kaggle/status")
async def kaggle_status():
    out = {}
    for key, cardfile in _CARDS.items():
        c = _card(cardfile)
        if not c:
            out[key] = {"model_present": False}
            continue
        out[key] = {
            "model_present": True,
            "model_name": c.get("model_name"),
            "kaggle_dataset_slug": _slug(c),
            "training_geography": c.get("training_geography"),
            "target_geography": c.get("target_geography"),
            "local_data_available": c.get("local_data_available"),
            "domain_shift_risk": c.get("domain_shift_risk"),
            "metrics": {k: v for k, v in (c.get("metrics") or {}).items() if k != "candidates"},
            "production_ready": c.get("production_ready"),
            "reason_if_not_production_ready": c.get("reason_if_not_production_ready"),
            "data_mode": c.get("data_mode"),
        }
    return success_response(
        data={"data_mode": get_settings().APP_DATA_MODE, "models": out},
        message="Kaggle-trained model status (real data).",
    )


@router.post("/kaggle/pv/estimate")
async def kaggle_pv_estimate(body: PVInput):
    bundle = _pv_bundle()
    card = _card(_CARDS["pv_ac"])
    if bundle is None or card is None:
        return success_response(
            data={
                "prediction_type": "pv_ac_power",
                "prediction_value": None,
                "status": prov.NOT_AVAILABLE,
                "reason": "kaggle_pv_ac_model not trained",
            },
            message="Kaggle PV model unavailable.",
        )
    feats = {
        "irradiation": body.irradiation,
        "ambient_temperature_c": body.ambient_temperature_c,
        "module_temperature_c": body.module_temperature_c,
        "hour_sin": float(np.sin(2 * np.pi * body.hour_of_day / 24.0)),
        "hour_cos": float(np.cos(2 * np.pi * body.hour_of_day / 24.0)),
    }
    x = [[float(feats[c]) for c in bundle["feature_columns"]]]
    value = round(max(0.0, float(bundle["estimator"].predict(x)[0])), 3)
    return success_response(
        data={
            "prediction_type": "pv_ac_power",
            "prediction_value": value,
            "unit": bundle.get("unit", "kW"),
            "model_file": f"backend/models/trained/{_PV_PKL}",
            "model_version": card.get("model_version"),
            "training_dataset": "kaggle_pv_ac_training.parquet",
            "kaggle_dataset_slug": _slug(card),
            "training_geography": card.get("training_geography"),
            "target_geography": card.get("target_geography"),
            "uses_non_local_data": card.get("uses_non_local_data"),
            "local_data_available": card.get("local_data_available"),
            "production_ready": card.get("production_ready"),
            "limitations": card.get("limitations", []),
            "data_mode": card.get("data_mode"),
            "warnings": [
                "PV AC estimate from a REAL_INDIA plant model (not Bengaluru-local); "
                "production_ready=false. Irradiation is the dataset's normalised sensor value.",
            ],
        },
        message="Kaggle PV AC-power estimate with provenance.",
    )
