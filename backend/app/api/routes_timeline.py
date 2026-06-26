"""Timeline & summary API - real 24h+ DSM nowcast from live weather data."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repository
from app.db.session import get_db
from app.services.forecast_service import ForecastService
from app.services.site_resolver import resolve_site
from app.utils.response import success_response

router = APIRouter()
_service = ForecastService()


async def _persist_forecasts(db: AsyncSession, site_uuid, timeline: list[dict]) -> None:
    if site_uuid is None:
        return
    rows = [
        {
            "ts": datetime.fromisoformat(e["timestamp"]),
            "predicted_kw": e["predicted_generation_mw"] * 1000,
            "clearsky_kw": e["scheduled_generation_mw"] * 1000,
            "confidence": e["confidence_score"],
        }
        for e in timeline
    ]
    await repository.save_forecasts(db, site_uuid, rows)


@router.get("/timeline/{site_id}")
async def get_timeline(
    site_id: str,
    latitude: float = Query(default=28.6, ge=-90, le=90),
    longitude: float = Query(default=77.2, ge=-180, le=180),
    timezone: str = Query(default="Asia/Kolkata"),
    capacity_mw: float = Query(default=50.0, gt=0),
    tilt: float = Query(default=20.0, ge=0, le=90),
    azimuth: float = Query(default=180.0, ge=0, le=360),
    scheduled_mw: float | None = Query(default=None, ge=0),
    threshold_percent: float | None = Query(default=None, ge=0, le=100),
    penalty_rate: float | None = Query(default=None, ge=0),
    forecast_days: int = Query(default=1, ge=1, le=7),
    past_days: int = Query(default=0, ge=0, le=7),
    db: AsyncSession = Depends(get_db),
):
    resolved = await resolve_site(
        db, site_id, latitude, longitude, timezone, capacity_mw, tilt, azimuth
    )
    result = await _service.build_timeline(
        site=resolved.config,
        scheduled_generation_mw=scheduled_mw,
        allowed_dsm_threshold_percent=(
            threshold_percent if threshold_percent is not None else resolved.threshold_percent
        ),
        penalty_rate_per_mwh=(
            penalty_rate if penalty_rate is not None else resolved.penalty_rate_per_mwh
        ),
        forecast_days=forecast_days,
        past_days=past_days,
    )
    await _persist_forecasts(db, resolved.site_uuid, result["timeline"])
    return success_response(
        data={
            "site_id": site_id,
            "capacity_mw": resolved.config.capacity_mw,
            "provider": result["provider"],
            "persisted": resolved.site_uuid is not None,
            "summary": result["summary"],
            "timeline": result["timeline"],
        }
    )


@router.get("/summary/{site_id}")
async def get_summary(
    site_id: str,
    latitude: float = Query(default=28.6, ge=-90, le=90),
    longitude: float = Query(default=77.2, ge=-180, le=180),
    timezone: str = Query(default="Asia/Kolkata"),
    capacity_mw: float = Query(default=50.0, gt=0),
    tilt: float = Query(default=20.0, ge=0, le=90),
    azimuth: float = Query(default=180.0, ge=0, le=360),
    scheduled_mw: float | None = Query(default=None, ge=0),
    threshold_percent: float | None = Query(default=None, ge=0, le=100),
    penalty_rate: float | None = Query(default=None, ge=0),
    forecast_days: int = Query(default=1, ge=1, le=7),
    db: AsyncSession = Depends(get_db),
):
    resolved = await resolve_site(
        db, site_id, latitude, longitude, timezone, capacity_mw, tilt, azimuth
    )
    result = await _service.build_timeline(
        site=resolved.config,
        scheduled_generation_mw=scheduled_mw,
        allowed_dsm_threshold_percent=(
            threshold_percent if threshold_percent is not None else resolved.threshold_percent
        ),
        penalty_rate_per_mwh=(
            penalty_rate if penalty_rate is not None else resolved.penalty_rate_per_mwh
        ),
        forecast_days=forecast_days,
    )
    summary = result["summary"]
    summary["site_id"] = site_id
    summary["capacity_mw"] = resolved.config.capacity_mw
    summary["provider"] = result["provider"]
    return success_response(data=summary)
