"""Weather API - real irradiance/weather data, live fetch, caching, persistence.

Endpoints:
  GET  /weather/{site_id}            - raw hourly weather (legacy; persisted if site)
  POST /weather/fetch                - live fetch for a coordinate (Redis-cached)
  GET  /weather/latest/{site_id}     - latest current conditions for a site
  GET  /weather/forecast/{site_id}   - forecast for a site over a horizon (persisted)
  GET  /weather/providers/status     - live + fallback provider status
  GET  /providers/status             - provider quota status (legacy)
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.api_agent import APIAgent
from app.agents.live_weather_agent import LiveWeatherAgent
from app.db import repository
from app.db.session import get_db
from app.utils.response import success_response

router = APIRouter()
_api_agent = APIAgent()
_live = LiveWeatherAgent()


def _readings_to_rows(readings: list[dict]) -> list[dict]:
    rows = []
    for r in readings:
        try:
            ts = datetime.fromisoformat(r["timestamp"])
        except (KeyError, ValueError):
            continue
        rows.append(
            {
                "ts": ts,
                "ghi": r.get("ghi_w_m2", 0.0),
                "dni": r.get("dni_w_m2", 0.0),
                "dhi": r.get("dhi_w_m2", 0.0),
                "temp": r.get("temperature_c", 0.0),
                "cloud_cover": r.get("cloud_cover_percent", 0.0),
                "wind": r.get("wind_speed_mps", 2.0),
            }
        )
    return rows


async def _resolve_coords(db: AsyncSession, site_id: str, latitude, longitude, timezone):
    site = await repository.get_site(db, site_id)
    if site is not None:
        return site, site.latitude, site.longitude, site.timezone
    return None, latitude, longitude, timezone


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
            "humidity_percent": p.humidity_percent,
            "pressure_hpa": p.pressure_hpa,
            "precipitation_probability_percent": p.precipitation_probability_percent,
        }
        for p in points
    ]

    persisted = False
    if site is not None:
        await repository.save_readings(db, site.id, _readings_to_rows(readings), source=provider)
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


@router.post("/weather/fetch")
async def weather_fetch(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    timezone: str = Query(default="Asia/Kolkata"),
    horizon: str = Query(default="24h", pattern="^(15min|30min|1h|24h|7d)$"),
    past_days: int = Query(default=0, ge=0, le=7),
):
    """Live fetch for an arbitrary coordinate (Redis-cached, synthetic fallback reported)."""
    result = await _live.fetch(latitude, longitude, timezone, horizon=horizon, past_days=past_days)
    return success_response(data=result)


@router.get("/weather/providers/status")
async def weather_providers_status():
    return success_response(
        data={
            "providers": _live.providers_status(),
            "quota": _api_agent.get_status(),
        }
    )


@router.get("/weather/latest/{site_id}")
async def weather_latest(
    site_id: str,
    latitude: float = Query(default=12.97, ge=-90, le=90),
    longitude: float = Query(default=77.59, ge=-180, le=180),
    timezone: str = Query(default="Asia/Kolkata"),
    db: AsyncSession = Depends(get_db),
):
    _, lat, lon, tz = await _resolve_coords(db, site_id, latitude, longitude, timezone)
    result = await _live.latest(lat, lon, tz)
    result["site_id"] = site_id
    return success_response(data=result)


@router.get("/weather/forecast/{site_id}")
async def weather_forecast(
    site_id: str,
    latitude: float = Query(default=12.97, ge=-90, le=90),
    longitude: float = Query(default=77.59, ge=-180, le=180),
    timezone: str = Query(default="Asia/Kolkata"),
    horizon: str = Query(default="24h", pattern="^(15min|30min|1h|24h|7d)$"),
    past_days: int = Query(default=0, ge=0, le=7),
    db: AsyncSession = Depends(get_db),
):
    site, lat, lon, tz = await _resolve_coords(db, site_id, latitude, longitude, timezone)
    result = await _live.fetch(lat, lon, tz, horizon=horizon, past_days=past_days)

    persisted = False
    if site is not None and result.get("mode") == "real":
        await repository.save_readings(
            db, site.id, _readings_to_rows(result["readings"]), source=result["provider"]
        )
        persisted = True

    result["site_id"] = site_id
    result["persisted"] = persisted
    return success_response(data=result)


@router.get("/providers/status")
async def provider_status():
    return success_response(data={"providers": _api_agent.get_status()})
