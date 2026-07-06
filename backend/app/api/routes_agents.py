"""Phase 1.7 agent API - serve trained Bengaluru agents WITH provenance.

Every prediction response carries the full provenance envelope (prediction_type,
model_file, model_version, training/target geography, local_data_used, source_status,
confidence_components, limitations, production_ready, warnings). Honest by design:
no rupee DSM charge, no predicted PV generation, explicit NOT_AVAILABLE where real
data/models are missing.

Endpoints (mounted under /api/v1):
  GET  /agents/status              - all agents + model cards + data mode + warnings
  GET  /agents/data-status         - data mode + source geography + honesty warnings
  POST /agents/solar/forecast      - irradiance (GHI) forecast
  POST /agents/cloud/risk          - irradiance-drop-risk classification
  POST /agents/dsm/assess          - DSM deviation-breach risk + framework recommendation
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ml import agent_models
from app.utils.response import success_response

router = APIRouter()


class AgentWeatherInput(BaseModel):
    timestamp_local: str | None = Field(
        default=None, description="Local IST timestamp, e.g. 2024-06-01T12:00:00"
    )
    cloud_cover_percent: float = 0.0
    temperature_c: float = 25.0
    relative_humidity_percent: float = 50.0
    wind_speed_mps: float = 2.0
    surface_pressure_hpa: float = 910.0
    precipitation_mm: float = 0.0
    # Optional overrides / extra inputs
    clearsky_ghi_wm2: float | None = None  # solar: computed via pvlib if omitted
    scheduled_ghi_wm2: float | None = None  # dsm: day-ahead schedule (required for DSM)
    capacity_mw: float | None = None  # solar: if set, returns an ESTIMATED PV output (not actual)


@router.get("/agents/status")
async def agents_status():
    return success_response(
        data=agent_models.agents_status(),
        message="Phase 1.7 agent status (Bengaluru real-data models).",
    )


@router.get("/agents/data-status")
async def agents_data_status():
    status = agent_models.agents_status()
    return success_response(
        data={
            "data_mode": status["data_mode"],
            "region": status["region"],
            "coordinates": status["coordinates"],
            "source_geography_priority": status["source_geography_priority"],
            "warnings": status["warnings"],
        },
        message="Data mode + source geography + honesty warnings.",
    )


@router.post("/agents/solar/forecast")
async def solar_forecast(body: AgentWeatherInput):
    result = agent_models.predict_solar(body.model_dump())
    return success_response(data=result, message="Irradiance (GHI) forecast with provenance.")


@router.post("/agents/cloud/risk")
async def cloud_risk(body: AgentWeatherInput):
    result = agent_models.predict_cloud(body.model_dump())
    return success_response(data=result, message="Irradiance-drop risk with provenance.")


@router.post("/agents/dsm/assess")
async def dsm_assess(body: AgentWeatherInput):
    result = agent_models.predict_dsm(body.model_dump())
    return success_response(
        data=result, message="DSM deviation-breach risk (framework-only, no rupees)."
    )
