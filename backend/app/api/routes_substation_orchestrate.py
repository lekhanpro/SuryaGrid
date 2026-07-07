"""Substation-driven agent workflow API.

When a substation is picked from the dropdown, these endpoints turn it into the central
context object and run it through the full agent workflow (weather -> solar -> cloud ->
generation timeline -> DSM), returning an agent_trace + calculation_trace and honest
provenance. Nothing is fabricated: missing real fields stay null and their calculations
are explicitly blocked.

Endpoints (mounted under /api/v1):
  GET  /substations/catalog          - dropdown-ready list (id + display_label + coords)
  GET  /substations/{substation_id}  - full SubstationContext for one substation
  POST /orchestrate/substation       - run the whole workflow for a selected substation
  POST /dsm/forecast                 - substation-context DSM forecast (framework-only)
  GET  /generation/timeline          - substation generation timeline (ESTIMATED from GHI)
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.agents.substation_orchestrator import get_substation_orchestrator
from app.core.exceptions import NotFoundError
from app.services.substation_context_service import get_substation_context_service
from app.utils.response import success_response

router = APIRouter()
_service = get_substation_context_service()
_orchestrator = get_substation_orchestrator()


class OrchestrateRequest(BaseModel):
    substation_id: str = Field(..., description="ID from GET /substations/catalog")
    site_capacity_mw: float | None = Field(
        default=None,
        gt=0,
        description="USER plant capacity (MW) for the PV estimate; not the substation MVA",
    )
    forecast_horizon_hours: int = Field(default=6, ge=1, le=48)
    scheduled_generation_mw: float | None = Field(
        default=None, ge=0, description="Operator day-ahead schedule (MW) for DSM deviation"
    )
    use_live_weather: bool = Field(
        default=True, description="Fetch Open-Meteo; false = clear-sky only"
    )
    site_latitude: float | None = Field(default=None, ge=-90, le=90)
    site_longitude: float | None = Field(default=None, ge=-180, le=180)


def _require_context(substation_id: str, lat: float | None = None, lon: float | None = None):
    context = _service.get_context(substation_id, site_latitude=lat, site_longitude=lon)
    if context is None:
        raise NotFoundError(
            f"Substation '{substation_id}' not found. Use GET /api/v1/substations/catalog "
            f"for valid IDs ({_service.count()} available)."
        )
    return context


# --------------------------------------------------------------------------- #
# Catalog + detail (declare the literal /catalog route BEFORE the dynamic one)
# --------------------------------------------------------------------------- #
@router.get("/substations/catalog")
async def substations_catalog(limit: int = Query(default=1000, ge=1, le=2000)):
    catalog = _service.list_catalog(limit=limit)
    return success_response(
        data={
            "count": len(catalog),
            "total_available": _service.count(),
            "source_label": "REAL_BENGALURU",
            "substations": catalog,
        },
        message="Dropdown-ready substation catalog (OpenStreetMap, Bengaluru).",
    )


@router.get("/substations/{substation_id}")
async def substation_detail(
    substation_id: str,
    site_latitude: float | None = Query(default=None, ge=-90, le=90),
    site_longitude: float | None = Query(default=None, ge=-180, le=180),
):
    context = _require_context(substation_id, site_latitude, site_longitude)
    return success_response(
        data=context.model_dump(),
        message="Full substation context (honest missing-field handling).",
    )


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
@router.post("/orchestrate/substation")
async def orchestrate_substation(body: OrchestrateRequest):
    context = _require_context(body.substation_id, body.site_latitude, body.site_longitude)
    result = await _orchestrator.run(
        context,
        site_capacity_mw=body.site_capacity_mw,
        forecast_horizon_hours=body.forecast_horizon_hours,
        scheduled_generation_mw=body.scheduled_generation_mw,
        use_live_weather=body.use_live_weather,
    )
    return success_response(
        data=result,
        message="Substation-driven agent workflow complete (weather -> solar -> cloud -> "
        "generation -> DSM).",
    )


@router.post("/dsm/forecast")
async def dsm_forecast(body: OrchestrateRequest):
    context = _require_context(body.substation_id, body.site_latitude, body.site_longitude)
    result = await _orchestrator.run(
        context,
        site_capacity_mw=body.site_capacity_mw,
        forecast_horizon_hours=body.forecast_horizon_hours,
        scheduled_generation_mw=body.scheduled_generation_mw,
        use_live_weather=body.use_live_weather,
    )
    return success_response(
        data={
            "substation": result["substation"],
            "dsm_forecast": result["dsm_forecast"],
            "generation_summary": result["generation_summary"],
            "workflow": result["workflow"],
            "data_sources": result["data_sources"],
            "limitations": result["limitations"],
            "data_mode": result["data_mode"],
            "emits_rupee_values": False,
        },
        message="Substation-context DSM forecast (framework-only, no rupees).",
    )


@router.get("/generation/timeline")
async def generation_timeline(
    substation_id: str = Query(..., description="ID from /substations/catalog"),
    site_capacity_mw: float | None = Query(default=None, gt=0),
    forecast_horizon_hours: int = Query(default=12, ge=1, le=48),
    allow_estimated: bool = Query(default=True),
    use_live_weather: bool = Query(default=True),
):
    context = _require_context(substation_id)
    result = await _orchestrator.run(
        context,
        site_capacity_mw=site_capacity_mw,
        forecast_horizon_hours=forecast_horizon_hours,
        use_live_weather=use_live_weather,
    )
    timeline = result["generation_timeline"]
    summary = result["generation_summary"]
    if not allow_estimated:
        # Honest: there is no measured generation, so suppress the estimate rather than fake it.
        for row in timeline:
            row["estimated_generation_mw"] = None
            row["estimated_generation_suppressed"] = True
        summary = {
            **summary,
            "peak_estimated_generation_mw": None,
            "total_estimated_energy_mwh": None,
            "note": "allow_estimated=false: estimated PV suppressed; only real irradiance shown. "
            "No measured generation exists for this substation.",
        }
    return success_response(
        data={
            "substation": result["substation"],
            "weather": result["weather"],
            "generation_timeline": timeline,
            "generation_summary": summary,
            "workflow": result["workflow"],
            "limitations": result["limitations"],
            "data_mode": result["data_mode"],
        },
        message="Substation generation timeline (ESTIMATED from forecast irradiance).",
    )
