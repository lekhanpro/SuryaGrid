"""Weather API - raw real irradiance/weather data from the provider (Open-Meteo)."""

from fastapi import APIRouter, Query

from app.providers.open_meteo import OpenMeteoProvider
from app.services.site_store import site_store
from app.utils.response import success_response

router = APIRouter()
_provider = OpenMeteoProvider()


@router.get("/weather/{site_id}")
async def get_weather(
    site_id: str,
    latitude: float = Query(default=28.6, ge=-90, le=90),
    longitude: float = Query(default=77.2, ge=-180, le=180),
    timezone: str = Query(default="Asia/Kolkata"),
    forecast_days: int = Query(default=1, ge=1, le=7),
    past_days: int = Query(default=0, ge=0, le=7),
):
    try:
        site = site_store.get(site_id)
        latitude, longitude, timezone = site["latitude"], site["longitude"], site["timezone"]
    except Exception:
        pass

    points = await _provider.fetch_forecast(
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
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
    return success_response(
        data={
            "site_id": site_id,
            "provider": _provider.name,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "readings_count": len(readings),
            "readings": readings,
        }
    )
