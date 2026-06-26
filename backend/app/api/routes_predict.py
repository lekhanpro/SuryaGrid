"""Prediction API - single-interval DSM evaluation from explicit inputs."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.agents.dsm_classifier_agent import DSMClassifierAgent
from app.agents.forecast_agent import ForecastAgent, SiteConfig
from app.agents.orchestrator_agent import OrchestratorAgent
from app.schemas.requests import DSMCheckRequest, PredictRequest
from app.utils.response import success_response

router = APIRouter()
_forecast = ForecastAgent()
_orchestrator = OrchestratorAgent()
_dsm = DSMClassifierAgent()


@router.post("/predict")
async def predict(req: PredictRequest):
    site = SiteConfig(
        latitude=req.latitude,
        longitude=req.longitude,
        timezone=req.timezone,
        capacity_mw=req.capacity_mw,
        tilt=req.tilt,
        azimuth=req.azimuth,
    )
    point = _forecast.predict_point(
        site=site,
        ghi_w_m2=req.ghi_w_m2,
        dni_w_m2=req.dni_w_m2,
        dhi_w_m2=req.dhi_w_m2,
        temperature_c=req.temperature_c,
        cloud_cover_percent=req.cloud_cover_percent,
        wind_speed_mps=req.wind_speed_mps,
        timestamp=datetime.now(timezone.utc),
    )
    result = _orchestrator.evaluate(
        forecast_point=point,
        scheduled_generation_mw=req.scheduled_generation_mw,
        allowed_dsm_threshold_percent=req.allowed_dsm_threshold_percent,
        penalty_rate_per_mwh=req.penalty_rate_per_mwh,
    )
    result["capacity_mw"] = req.capacity_mw
    return success_response(data=result)


@router.post("/dsm/check")
async def dsm_check(req: DSMCheckRequest):
    result = _dsm.classify(
        predicted_generation_mw=req.predicted_generation_mw,
        scheduled_generation_mw=req.scheduled_generation_mw,
        allowed_dsm_threshold_percent=req.allowed_dsm_threshold_percent,
        penalty_rate_per_mwh=req.penalty_rate_per_mwh,
    )
    return success_response(data=result)
