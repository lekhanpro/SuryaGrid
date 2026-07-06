"""Prediction API.

POST /predict               - single-interval DSM evaluation from explicit inputs
GET  /predict/{site_id}     - full end-to-end site prediction (weather->ml/hybrid->
                              advanced DSM->fuzzy risk->sources), the complete schema
POST /dsm/check             - standalone (simple) DSM classification
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dsm_classifier_agent import DSMClassifierAgent
from app.agents.forecast_agent import ForecastAgent, SiteConfig
from app.agents.fuzzy_risk_agent import FuzzyRiskAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.data_sources import source_registry as sr
from app.db.session import get_db
from app.schemas.requests import DSMCheckRequest, PredictRequest
from app.utils.response import success_response

router = APIRouter()
_forecast = ForecastAgent()
_orchestrator = OrchestratorAgent()
_dsm = DSMClassifierAgent()
_fuzzy = FuzzyRiskAgent()


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
        timestamp=datetime.now(UTC),
    )
    result = _orchestrator.evaluate(
        forecast_point=point,
        scheduled_generation_mw=req.scheduled_generation_mw,
        allowed_dsm_threshold_percent=req.allowed_dsm_threshold_percent,
        penalty_rate_per_mwh=req.penalty_rate_per_mwh,
    )
    # Enrich to the full response schema (direction, band, fuzzy risk, sources).
    predicted = result["predicted_generation_mw"]
    within = result["penalty_status"] != "PENALTY_RISK"
    if within:
        direction = "WITHIN_LIMIT"
    else:
        direction = (
            "OVER_INJECTION" if predicted > req.scheduled_generation_mw else "UNDER_INJECTION"
        )
    fuzzy = _fuzzy.score(
        deviation_percent=result["deviation_percent"],
        allowed_dsm_threshold_percent=req.allowed_dsm_threshold_percent,
        confidence_score=point.confidence_score,
        cloud_cover_percent=req.cloud_cover_percent,
    )
    result.update(
        {
            "capacity_mw": req.capacity_mw,
            "forecast_mode": "formula",
            "source_used": "formula:pvlib (explicit inputs)",
            "data_sources": ["user_input"],
            "deviation_direction": direction,
            "dsm_band": "within_band" if within else f">{req.allowed_dsm_threshold_percent:.0f}%",
            "estimated_dsm_charge": result["estimated_penalty_cost"],
            "fuzzy_risk_score": fuzzy["fuzzy_risk_score"],
            "fuzzy_risk_level": fuzzy["fuzzy_risk_level"],
            "sources": sr.cite("SRC-PVLIB-001"),
        }
    )
    return success_response(data=result)


@router.get("/predict/{site_id}")
async def predict_site(
    site_id: str,
    latitude: float = Query(default=12.97, ge=-90, le=90),
    longitude: float = Query(default=77.59, ge=-180, le=180),
    timezone: str = Query(default="Asia/Kolkata"),
    capacity_mw: float = Query(default=50.0, gt=0),
    tilt: float = Query(default=20.0, ge=0, le=90),
    azimuth: float = Query(default=180.0, ge=0, le=360),
    panel_efficiency: float = Query(default=0.18, gt=0, le=1),
    scheduled_mw: float | None = Query(default=None, ge=0),
    mode: str = Query(default="auto", pattern="^(auto|formula|ml|hybrid)$"),
    region: str | None = Query(default=None),
    regulator: str | None = Query(default=None),
    rule_profile_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Full end-to-end prediction for a site (the complete response schema)."""
    result = await _orchestrator.run_full(
        db,
        site_id=site_id,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        capacity_mw=capacity_mw,
        tilt=tilt,
        azimuth=azimuth,
        panel_efficiency=panel_efficiency,
        scheduled_generation_mw=scheduled_mw,
        mode=mode,
        region=region,
        regulator=regulator,
        rule_profile_id=rule_profile_id,
    )
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
