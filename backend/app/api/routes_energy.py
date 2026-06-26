"""Energy balance API - production vs consumption, surplus/deficit."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.consumption_service import generate_consumption_day
from app.services.energy_service import compute_energy_balance
from app.services.forecast_service import ForecastService
from app.services.site_resolver import resolve_site
from app.utils.response import success_response

router = APIRouter()
_service = ForecastService()


@router.get("/energy/{site_id}")
async def get_energy_balance(
    site_id: str,
    latitude: float = Query(default=28.6, ge=-90, le=90),
    longitude: float = Query(default=77.2, ge=-180, le=180),
    timezone: str = Query(default="Asia/Kolkata"),
    capacity_mw: float = Query(default=50.0, gt=0),
    tilt: float = Query(default=20.0, ge=0, le=90),
    azimuth: float = Query(default=180.0, ge=0, le=360),
    consumption_profile: str = Query(default="commercial"),
    consumption_base_kw: float = Query(default=5000.0, gt=0),
    forecast_days: int = Query(default=1, ge=1, le=7),
    db: AsyncSession = Depends(get_db),
):
    resolved = await resolve_site(
        db, site_id, latitude, longitude, timezone, capacity_mw, tilt, azimuth
    )
    result = await _service.build_timeline(
        site=resolved.config,
        scheduled_generation_mw=None,
        allowed_dsm_threshold_percent=resolved.threshold_percent,
        penalty_rate_per_mwh=resolved.penalty_rate_per_mwh,
        forecast_days=forecast_days,
    )
    timeline = result["timeline"]
    production_kw = [e["predicted_generation_mw"] * 1000 for e in timeline]

    consumption_day = generate_consumption_day(
        profile=consumption_profile, base_kw=consumption_base_kw, hours=len(timeline)
    )
    consumption_kw = [c["consumption_kw"] for c in consumption_day]

    balance = compute_energy_balance(production_kw, consumption_kw)
    balance["site_id"] = site_id
    balance["capacity_mw"] = resolved.config.capacity_mw
    balance["consumption_profile"] = consumption_profile
    balance["provider"] = result.get("provider", "unknown")
    return success_response(data=balance)


@router.get("/consumption/profiles")
async def list_consumption_profiles():
    from app.services.consumption_service import PROFILES

    profiles = {}
    for name in PROFILES:
        day = generate_consumption_day(profile=name, base_kw=50.0)
        profiles[name] = {
            "sample_base_kw": 50.0,
            "peak_kw": max(c["consumption_kw"] for c in day),
            "daily_kwh": round(sum(c["consumption_kw"] for c in day), 1),
            "hourly": day,
        }
    return success_response(data=profiles)
