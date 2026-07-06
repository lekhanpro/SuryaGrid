"""ML API - dataset ingestion, augmented dataset build, training, status, predict.

Endpoints:
  POST /ml/datasets/ingest-kaggle   - download the Kaggle dataset (if creds set)
  POST /ml/datasets/build-augmented - build the augmented dataset (kaggle/weather/synthetic)
  POST /ml/train                    - train a model on the augmented dataset
  GET  /ml/model/status             - model + dataset status
  POST /ml/predict                  - single-interval formula/ml/hybrid prediction

No silent behavior: if the Kaggle dataset is missing or no model is trained, the
endpoints say so explicitly. See docs/ML_PIPELINE.md.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Query

from app.agents.forecast_agent import ForecastAgent, SiteConfig
from app.data_sources import source_registry as sr
from app.data_sources.kaggle_solar_provider import KaggleSolarProvider
from app.data_sources.live_weather_provider import LiveWeatherProvider
from app.data_sources.synthetic_weather_provider import SyntheticWeatherProvider
from app.ml import dataset_builder, model_registry, train_model
from app.ml.predict_model import predictor
from app.schemas.requests import MLPredictRequest
from app.utils.response import success_response

router = APIRouter()
_forecast = ForecastAgent()


@router.post("/ml/datasets/ingest-kaggle")
async def ingest_kaggle():
    """Download the Kaggle solar dataset via the Kaggle API (if credentials set)."""
    prov = KaggleSolarProvider()
    result = prov.ingest_via_api()
    return success_response(
        data={"ingest": result, "status": prov.status().to_dict()},
        message=result.get("detail", "ingest attempted"),
    )


async def _build_augmented_impl(
    source: str,
    latitude: float = 12.97,
    longitude: float = 77.59,
    timezone: str = "Asia/Kolkata",
    capacity_mw: float = 50.0,
    panel_efficiency: float = 0.18,
    past_days: int = 60,
) -> dict:
    """Build + persist the augmented dataset. Plain helper (callable in-process).

    Returns a data dict (never raises for provider/kaggle-missing cases).
    """
    src_df = None
    provider_label = source

    if source == "kaggle":
        prov = KaggleSolarProvider()
        if not prov.is_loaded():
            return {
                "built": False,
                "reason": "kaggle_not_loaded",
                "status": prov.status().to_dict(),
            }
        src_df = prov.load_dataframe()
        provider_label = "kaggle-solar"
    elif source in ("weather", "synthetic"):
        provider = LiveWeatherProvider() if source == "weather" else SyntheticWeatherProvider()
        try:
            points = await provider.fetch_forecast(
                latitude, longitude, timezone, forecast_days=1, past_days=past_days
            )
        except Exception as exc:  # live source unreachable
            return {"built": False, "reason": "provider_error", "detail": str(exc)}
        src_df = dataset_builder.weather_points_to_frame(points, source_provider=provider.name)
        provider_label = provider.name

    aug, report = dataset_builder.build_augmented(
        src_df,
        latitude=latitude,
        longitude=longitude,
        site_capacity_mw=capacity_mw,
        panel_efficiency=panel_efficiency,
    )
    path = dataset_builder.save_augmented(aug)
    return {
        "built": True,
        "source": provider_label,
        "rows": len(aug),
        "columns": list(aug.columns),
        "quality_report": report,
        "path": str(path),
    }


@router.post("/ml/datasets/build-augmented")
async def build_augmented(
    source: str = Query(default="kaggle", pattern="^(kaggle|weather|synthetic)$"),
    latitude: float = Query(default=12.97, ge=-90, le=90),
    longitude: float = Query(default=77.59, ge=-180, le=180),
    timezone: str = Query(default="Asia/Kolkata"),
    capacity_mw: float = Query(default=50.0, gt=0),
    panel_efficiency: float = Query(default=0.18, gt=0, le=1),
    past_days: int = Query(default=60, ge=1, le=92),
):
    """Build and persist the canonical augmented dataset from a chosen source."""
    data = await _build_augmented_impl(
        source, latitude, longitude, timezone, capacity_mw, panel_efficiency, past_days
    )
    if not data.get("built"):
        return success_response(data=data, message=data.get("reason", "not built"))
    return success_response(data=data, message=f"Augmented dataset built from {data['source']}")


@router.post("/ml/train")
async def train(
    model_name: str = Query(default="auto"),
    target: str | None = Query(default=None),
    rebuild_from: str | None = Query(default=None, pattern="^(kaggle|weather|synthetic)$"),
):
    """Train a model on the augmented dataset (optionally rebuild it first)."""
    if rebuild_from:
        await _build_augmented_impl(rebuild_from)

    df = dataset_builder.load_augmented()
    if df is None or df.empty:
        # Try to build from Kaggle automatically.
        prov = KaggleSolarProvider()
        if prov.is_loaded():
            df, _ = dataset_builder.build_augmented(prov.load_dataframe())
            dataset_builder.save_augmented(df)
        else:
            return success_response(
                data={
                    "trained": False,
                    "reason": "no_dataset",
                    "detail": "No augmented dataset and Kaggle dataset not loaded. "
                    "Ingest Kaggle or build-augmented from weather/synthetic first.",
                },
                message="No dataset available to train",
            )

    try:
        metadata = train_model.train(df, target=target, model_name=model_name)
    except ValueError as exc:
        return success_response(
            data={"trained": False, "reason": "training_error", "detail": str(exc)},
            message="Training could not proceed",
        )

    predictor.reload()
    return success_response(
        data={
            "trained": True,
            "metadata": metadata,
            "sources": sr.cite(*metadata["source_references"]),
        },
        message=f"Model trained ({metadata['model_type']})",
    )


@router.get("/ml/model/status")
async def model_status():
    prov = KaggleSolarProvider()
    return success_response(
        data={
            "model": model_registry.status(),
            "augmented_dataset_present": dataset_builder.augmented_exists(),
            "kaggle": prov.status().to_dict(),
        }
    )


@router.post("/ml/predict")
async def ml_predict(req: MLPredictRequest):
    """Single-interval prediction in formula/ml/hybrid/auto mode."""
    site = SiteConfig(
        latitude=req.latitude,
        longitude=req.longitude,
        timezone=req.timezone,
        capacity_mw=req.capacity_mw,
        tilt=req.tilt,
        azimuth=req.azimuth,
        panel_efficiency=req.panel_efficiency,
        nearest_substation_distance_km=req.nearest_substation_distance_km,
    )
    from app.providers.base import WeatherPoint

    wp = WeatherPoint(
        timestamp=datetime.now(UTC),
        ghi_w_m2=req.ghi_w_m2,
        dni_w_m2=req.dni_w_m2,
        dhi_w_m2=req.dhi_w_m2,
        temperature_c=req.temperature_c,
        cloud_cover_percent=req.cloud_cover_percent,
        wind_speed_mps=req.wind_speed_mps,
        humidity_percent=req.humidity_percent,
        pressure_hpa=req.pressure_hpa,
        precipitation_probability_percent=req.precipitation_probability_percent,
    )
    point = _forecast.forecast_timeline(site, [wp], mode=req.mode, predictor=predictor)[0]
    sources = ["SRC-PVLIB-001"]
    if point.forecast_mode in ("ml", "hybrid"):
        sources = ["SRC-KAGGLE-SOLAR-001", "SRC-OPENMETEO-001", "SRC-PVLIB-001"]
    return success_response(
        data={
            "timestamp": point.timestamp.isoformat(),
            "forecast_mode": point.forecast_mode,
            "model_version": point.model_version,
            "source_used": point.source_used,
            "ghi_w_m2": point.ghi_w_m2,
            "poa_w_m2": point.poa_w_m2,
            "predicted_generation_mw": point.predicted_generation_mw,
            "clearsky_generation_mw": point.clearsky_generation_mw,
            "confidence_score": point.confidence_score,
            "capacity_mw": req.capacity_mw,
            "sources": sr.cite(*sources),
        }
    )
