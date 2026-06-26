"""Weather API - raw real irradiance/weather data, persisted when site exists."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.api_agent import APIAgent
from app.db import repository
from app.db.session import get_db
from app.utils.response import success_response

router = APIRouter()
_api_agent = APIAgent()


@router.get("/weather/{site_id}")
async def get_weather(
    site_id: str,
    latitude: float = Query(default=28.6, ge=-90, le=90),
    longitude: float = Query(default=77.2, ge=-180, le=180),
    timezone: str = Query(default="Asia/Kolkata"),
    forecast_days: int = Query(default=1, ge=1, le=7),
    past_days: int = Query(default=0, ge=0, le=7),
    db: AsyncSession = Depends(get_db),
):
    site = await repository.get_site(db, site_id)
    if site is not None:
        latitude, longitude, timezone = site.latitude, site.longitude, site.timezone

    points, provider = await _api_agent.fetch_weather(
        latitude=latitude,
        longitude=longitude,
        timezone_str=timezone,
        forecast_days=forecast_days,
        past_days=past_days,
    )
    readings = [
        {
            "timestamp": p.timestamp.isoformat(),
            "ghi_w_m2": p.ghi_w_m2,
            "dni_w_m2": p.dni_w_m2,
            "dhi_w_m2": p.dhi_w_m2,
            "temperature_c": p.temperature_c,
            "cloud_cover_percent": p.cloud_cover_percent,
            "wind_speed_mps": p.wind_speed_mps,
        }
        for p in points
    ]

    persisted = False
    if site is not None:
        rows = [
            {
                "ts": p.timestamp,
                "ghi": p.ghi_w_m2,
                "dni": p.dni_w_m2,
                "dhi": p.dhi_w_m2,
                "temp": p.temperature_c,
                "cloud_cover": p.cloud_cover_percent,
                "wind": p.wind_speed_mps,
            }
            for p in points
        ]
        await repository.save_readings(db, site.id, rows, source=provider)
        persisted = True

    return success_response(
        data={
            "site_id": site_id,
            "provider": provider,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "readings_count": len(readings),
            "persisted": persisted,
            "readings": readings,
        }
    )


@router.get("/providers/status")
async def provider_status():
    return success_response(data={"providers": _api_agent.get_status()})
