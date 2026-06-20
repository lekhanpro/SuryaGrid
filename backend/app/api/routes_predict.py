"""Prediction API - runs the full orchestrator agent pipeline."""

from fastapi import APIRouter
from app.schemas.requests import PredictRequest, DSMCheckRequest
from app.agents.orchestrator_agent import OrchestratorAgent
from app.agents.dsm_classifier_agent import DSMClassifierAgent
from app.utils.response import success_response

router = APIRouter()
orchestrator = OrchestratorAgent()
dsm_agent = DSMClassifierAgent()


@router.post("/predict")
async def predict(req: PredictRequest):
    result = orchestrator.run_prediction_cycle(
        solar_capacity_mw=req.solar_capacity_mw,
        irradiance_w_m2=req.irradiance_w_m2,
        cloud_cover_percent=req.cloud_cover_percent,
        temperature_c=req.temperature_c,
        scheduled_generation_mw=req.scheduled_generation_mw,
        allowed_dsm_threshold_percent=req.allowed_dsm_threshold_percent,
        penalty_rate_per_mw=req.penalty_rate_per_mw,
    )
    result["site_id"] = req.site_id
    return success_response(data=result)


@router.post("/dsm/check")
async def dsm_check(req: DSMCheckRequest):
    result = dsm_agent.classify(
        predicted_generation_mw=req.predicted_generation_mw,
        scheduled_generation_mw=req.scheduled_generation_mw,
        allowed_dsm_threshold_percent=req.allowed_dsm_threshold_percent,
        penalty_rate_per_mw=req.penalty_rate_per_mw,
    )
    return success_response(data=result)
