"""Phase 1.7 inference layer - serve the trained agents WITH full provenance.

Every prediction is returned inside a provenance envelope so the API/UI can never
show a number without its origin and honesty flags:

    prediction_type, prediction_value, unit, model_file, model_version,
    training_geography, target_geography, local_data_used, source_status,
    confidence_components, limitations, production_ready (+ warnings).

Honesty:
  * Confidence components are REAL model outputs (predicted probability) and REAL test
    metrics from the model card - never fabricated.
  * PV generation is never predicted here (irradiance only); callers must estimate PV
    from capacity via pvlib and label it ESTIMATED_FROM_REAL.
"""

from __future__ import annotations

import json
from datetime import datetime
from functools import cache, lru_cache

import joblib
import numpy as np

from app.ml import provenance as prov
from app.ml.provenance import BENGALURU

# Filenames (must match the trainers)
SOLAR_PKL, SOLAR_CARD = "solar_forecast_model.pkl", "solar_forecast_model_card.json"
CLOUD_PKL, CLOUD_CARD = "cloud_risk_classifier.pkl", "cloud_risk_classifier_card.json"
DSM_PKL, DSM_CARD = "dsm_classifier.pkl", "dsm_model_card.json"
DSM_RULES = "dsm_rules_engine.json"
LOAD_PKL, LOAD_CARD = "load_forecast_model.pkl", "load_forecast_model_card.json"
RL_CARD = "rl_policy_card.json"


def _load_bundle(filename: str):
    path = prov.trained_models_dir() / filename
    if not path.exists():
        return None
    return joblib.load(path)


@cache
def _bundle_cached(filename: str, mtime: float):  # mtime busts cache on retrain
    return _load_bundle(filename)


def _bundle(filename: str):
    path = prov.trained_models_dir() / filename
    if not path.exists():
        return None
    return _bundle_cached(filename, path.stat().st_mtime)


def _card(filename: str) -> dict | None:
    path = prov.model_metadata_dir() / filename
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _bengaluru_location(altitude: float = 920.0):
    import pvlib

    return pvlib.location.Location(
        BENGALURU.latitude, BENGALURU.longitude, tz=BENGALURU.timezone, altitude=altitude
    )


def clearsky_ghi(timestamp_local: str) -> float | None:
    """pvlib Ineichen clear-sky GHI for Bengaluru at a local timestamp."""
    try:
        import pandas as pd

        idx = pd.DatetimeIndex([pd.to_datetime(timestamp_local)]).tz_localize(
            BENGALURU.timezone, nonexistent="shift_forward", ambiguous="NaT"
        )
        return round(
            float(_bengaluru_location().get_clearsky(idx, model="ineichen")["ghi"].iloc[0]), 2
        )
    except Exception:  # noqa: BLE001
        return None


def _time_features(timestamp_local: str) -> dict:
    import pandas as pd

    ts = pd.to_datetime(timestamp_local)
    hour, doy, dow = int(ts.hour), int(ts.dayofyear), int(ts.dayofweek)
    return {
        "hour_of_day": hour,
        "day_of_year": doy,
        "month": int(ts.month),
        "hour_sin": float(np.sin(2 * np.pi * hour / 24.0)),
        "hour_cos": float(np.cos(2 * np.pi * hour / 24.0)),
        "doy_sin": float(np.sin(2 * np.pi * doy / 365.25)),
        "doy_cos": float(np.cos(2 * np.pi * doy / 365.25)),
        "dow_sin": float(np.sin(2 * np.pi * dow / 7.0)),
        "dow_cos": float(np.cos(2 * np.pi * dow / 7.0)),
        "is_weekend": int(dow >= 5),
    }


def _vector(bundle: dict, feats: dict) -> list[float]:
    out = []
    for col in bundle["feature_columns"]:
        v = feats.get(col, 0.0)
        try:
            out.append(float(v) if v is not None else 0.0)
        except (TypeError, ValueError):
            out.append(0.0)
    return out


def _data_mode() -> str:
    try:
        from app.config import get_settings

        return get_settings().APP_DATA_MODE
    except Exception:  # noqa: BLE001
        return "real"


def _envelope(
    card: dict,
    model_filename: str,
    *,
    prediction_type: str,
    value,
    unit: str,
    confidence_components: dict,
    warnings: list[str],
) -> dict:
    card = card or {}
    return {
        "prediction_type": prediction_type,
        "prediction_value": value,
        "unit": unit,
        "model_file": f"backend/models/trained/{model_filename}",
        "model_version": card.get("model_version"),
        "training_geography": card.get("training_geography"),
        "target_geography": card.get("target_geography"),
        "local_data_used": card.get("local_data_available"),
        "source_status": card.get("source_status")
        or [s.get("label") for s in card.get("training_data_sources", [])],
        "confidence_components": confidence_components,
        "limitations": card.get("limitations", []),
        "production_ready": card.get("production_ready", False),
        "uses_non_local_data": card.get("uses_non_local_data", False),
        "uses_synthetic_data": card.get("uses_synthetic_data", False),
        "data_mode": _data_mode(),
        "warnings": warnings,
    }


def _not_available(prediction_type: str, reason: str) -> dict:
    return {
        "prediction_type": prediction_type,
        "prediction_value": None,
        "status": prov.NOT_AVAILABLE,
        "reason": reason,
        "production_ready": False,
    }


# --------------------------------------------------------------------------- #
# Predictions
# --------------------------------------------------------------------------- #
def predict_solar(inputs: dict) -> dict:
    """Irradiance (GHI) forecast. inputs: timestamp_local + weather fields."""
    bundle = _bundle(SOLAR_PKL)
    card = _card(SOLAR_CARD)
    if bundle is None:
        return _not_available("irradiance_forecast", "solar model not trained")
    ts = inputs.get("timestamp_local") or datetime.now().isoformat()
    feats = {**_time_features(ts), **inputs}
    if feats.get("clearsky_ghi_wm2") is None:
        feats["clearsky_ghi_wm2"] = clearsky_ghi(ts) or 0.0
    value = round(float(bundle["estimator"].predict([_vector(bundle, feats)])[0]), 2)
    value = max(0.0, value)
    metrics = (card or {}).get("metrics", {})
    env = _envelope(
        card,
        SOLAR_PKL,
        prediction_type="irradiance_forecast",
        value=value,
        unit="W/m2",
        confidence_components={
            "model_test_r2": metrics.get("r2"),
            "model_test_rmse_wm2": metrics.get("rmse"),
            "note": "Point estimate; uncertainty ~ test RMSE. No per-sample interval.",
        },
        warnings=[
            "This is IRRADIANCE (GHI), not PV generation. PV output must be estimated from "
            "your plant capacity via pvlib and is ESTIMATED_FROM_REAL, never measured.",
        ],
    )
    env["clearsky_ghi_wm2"] = feats["clearsky_ghi_wm2"]

    # Optional PV estimate from user capacity - explicitly ESTIMATED, never "actual".
    cap = inputs.get("capacity_mw")
    if cap not in (None, "", 0):
        try:
            capacity_mw = float(cap)
            performance_ratio = 0.80  # documented derate; not measured
            est_pv = round(max(0.0, capacity_mw * (value / 1000.0) * performance_ratio), 3)
            env["pv_estimate"] = {
                "estimated_output": True,
                "estimated_pv_mw": est_pv,
                "unit": "MW",
                "formula": "capacity_mw * (GHI_W_m2 / 1000) * performance_ratio(0.80)",
                "source_label": prov.ESTIMATED_FROM_REAL,
                "is_actual_generation": False,
                "note": "PV output is ESTIMATED from forecast irradiance + user capacity via a "
                "fixed performance ratio. It is NOT measured generation and NOT model-predicted.",
            }
        except (TypeError, ValueError):
            pass
    return env


def predict_cloud(inputs: dict) -> dict:
    """Irradiance-drop risk (probability + label). inputs: timestamp_local + weather fields."""
    bundle = _bundle(CLOUD_PKL)
    card = _card(CLOUD_CARD)
    if bundle is None:
        return _not_available("irradiance_drop_risk", "cloud model not trained")
    ts = inputs.get("timestamp_local") or datetime.now().isoformat()
    feats = {**_time_features(ts), **inputs}
    proba = float(bundle["estimator"].predict_proba([_vector(bundle, feats)])[0][1])
    label = int(proba >= 0.5)
    metrics = (card or {}).get("metrics", {})
    return _envelope(
        card,
        CLOUD_PKL,
        prediction_type="irradiance_drop_risk",
        value={"drop_risk": label, "probability": round(proba, 4)},
        unit="probability",
        confidence_components={
            "predicted_probability": round(proba, 4),
            "model_test_f1": metrics.get("f1"),
            "model_test_roc_auc": metrics.get("roc_auc"),
        },
        warnings=["Predicts IRRADIANCE drop (clearness kt<0.5), not PV-output drop."],
    )


def predict_dsm(inputs: dict) -> dict:
    """DSM deviation-breach risk + framework recommendation (NO rupees).

    inputs must include scheduled_ghi_wm2 (day-ahead scheduled irradiance) to assess.
    """
    bundle = _bundle(DSM_PKL)
    card = _card(DSM_CARD)
    if bundle is None:
        return _not_available("dsm_deviation_breach_risk", "dsm model not trained")
    if inputs.get("scheduled_ghi_wm2") is None:
        return _not_available(
            "dsm_deviation_breach_risk",
            "scheduled_ghi_wm2 (day-ahead schedule) required to assess deviation; not provided.",
        )
    ts = inputs.get("timestamp_local") or datetime.now().isoformat()
    feats = {**_time_features(ts), **inputs}
    proba = float(bundle["estimator"].predict_proba([_vector(bundle, feats)])[0][1])
    label = int(proba >= 0.5)
    rules = _card_rules()
    metrics = (card or {}).get("metrics", {})
    env = _envelope(
        card,
        DSM_PKL,
        prediction_type="dsm_deviation_breach_risk",
        value={"breach_risk": label, "probability": round(proba, 4)},
        unit="probability",
        confidence_components={
            "predicted_probability": round(proba, 4),
            "model_test_f1": metrics.get("f1"),
            "model_test_roc_auc": metrics.get("roc_auc"),
        },
        warnings=[
            "Framework-only: NO rupee DSM charge is computed (NEEDS_OFFICIAL_TARIFF_SOURCE).",
            "Band +/-15% is a modelling parameter, not an official KERC/CERC value.",
            "No substation-level DSM (real feeder capacity/load unavailable).",
        ],
    )
    env["framework_recommendation"] = rules
    env["emits_rupee_values"] = False
    return env


def _card_rules() -> dict:
    path = prov.trained_models_dir() / DSM_RULES
    if not path.exists():
        return {"status": prov.NEEDS_OFFICIAL_SOURCE}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# Status / data mode
# --------------------------------------------------------------------------- #
def _card_summary(filename: str) -> dict | None:
    c = _card(filename)
    if not c:
        return None
    return {
        "model_name": c.get("model_name"),
        "model_version": c.get("model_version"),
        "prediction_type": c.get("prediction_type"),
        "training_geography": c.get("training_geography"),
        "target_geography": c.get("target_geography"),
        "local_data_available": c.get("local_data_available"),
        "domain_shift_risk": c.get("domain_shift_risk"),
        "production_ready": c.get("production_ready"),
        "reason_if_not_production_ready": c.get("reason_if_not_production_ready"),
        "uses_synthetic_data": c.get("uses_synthetic_data"),
        "uses_non_local_data": c.get("uses_non_local_data"),
        "metrics": c.get("metrics"),
    }


def agents_status() -> dict:
    from app.config import get_settings

    settings = get_settings()
    agents = {
        "solar": {
            "model_present": _bundle(SOLAR_PKL) is not None,
            **(_card_summary(SOLAR_CARD) or {}),
        },
        "cloud": {
            "model_present": _bundle(CLOUD_PKL) is not None,
            **(_card_summary(CLOUD_CARD) or {}),
        },
        "dsm": {"model_present": _bundle(DSM_PKL) is not None, **(_card_summary(DSM_CARD) or {})},
        "load": {
            "model_present": _bundle(LOAD_PKL) is not None,
            **(_card_summary(LOAD_CARD) or {}),
        },
        "rl": {"model_present": False, **(_card_summary(RL_CARD) or {})},
    }
    manifest_path = prov.ml_data_dir() / "dataset_build_manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    )
    return {
        "data_mode": settings.APP_DATA_MODE,
        "region": BENGALURU.display_name,
        "coordinates": [BENGALURU.latitude, BENGALURU.longitude],
        "source_geography_priority": [
            "REAL_LOCAL(Bengaluru)",
            "REAL_KARNATAKA",
            "REAL_INDIA",
            "REAL_COORDINATE_BASED",
            "REAL_NON_LOCAL(pretraining only)",
        ],
        "agents": agents,
        "warnings": data_warnings(agents),
        "dataset_manifest_present": bool(manifest),
    }


def data_warnings(agents: dict) -> list[str]:
    w = [
        "PV generation is ESTIMATED_FROM_REAL irradiance + user capacity; it is never measured "
        "or directly predicted (no real local PV dataset).",
        "Substation capacity (MVA) is unavailable from OSM; substation-level DSM is disabled "
        "(NEEDS_OFFICIAL_SOURCE: KPTCL/BESCOM).",
        "DSM rupee charges are not computed (NEEDS_OFFICIAL_TARIFF_SOURCE).",
    ]
    load = agents.get("load", {})
    if load.get("model_present") and not load.get("local_data_available"):
        w.append(
            "Load forecasts use REAL_INDIA national demand (NOT Bengaluru-local); "
            "domain shift HIGH, not production-ready for local decisions."
        )
    return w
