"""Forecast API - mode-aware (formula/ml/hybrid) generation forecast for a site.

Distinct from /timeline (which runs the full DSM pipeline in formula mode): this
returns the generation forecast timeline with the chosen model mode and per-point
forecast_mode / model_version / confidence.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.forecast_agent import ForecastAgent
from app.agents.live_weather_agent import LiveWeatherAgent
from app.data_sources import source_registry as sr
from app.db.session import get_db
from app.ml.predict_model import predictor
from app.providers.base import WeatherPoint
from app.services.site_resolver import resolve_site
from app.utils.response import success_response

router = APIRouter()
_forecast = ForecastAgent()
_live = LiveWeatherAgent()


def _reading_to_point(r: dict) -> WeatherPoint:
    return WeatherPoint(
        timestamp=datetime.fromisoformat(r["timestamp"]),
        ghi_w_m2=r.get("ghi_w_m2", 0.0),
        dni_w_m2=r.get("dni_w_m2", 0.0),
        dhi_w_m2=r.get("dhi_w_m2", 0.0),
        temperature_c=r.get("temperature_c", 25.0),
        cloud_cover_percent=r.get("cloud_cover_percent", 0.0),
        wind_speed_mps=r.get("wind_speed_mps", 2.0),
        humidity_percent=r.get("humidity_percent", 0.0),
        pressure_hpa=r.get("pressure_hpa", 0.0),
        precipitation_probability_percent=r.get("precipitation_probability_percent", 0.0),
    )


@router.get("/forecast/{site_id}")
async def get_forecast(
    site_id: str,
    latitude: float = Query(default=12.97, ge=-90, le=90),
    longitude: float = Query(default=77.59, ge=-180, le=180),
    timezone: str = Query(default="Asia/Kolkata"),
    capacity_mw: float = Query(default=50.0, gt=0),
    tilt: float = Query(default=20.0, ge=0, le=90),
    azimuth: float = Query(default=180.0, ge=0, le=360),
    panel_efficiency: float = Query(default=0.18, gt=0, le=1),
    mode: str = Query(default="auto", pattern="^(auto|formula|ml|hybrid)$"),
    horizon: str = Query(default="24h", pattern="^(15min|30min|1h|24h|7d)$"),
    db: AsyncSession = Depends(get_db),
):
    resolved = await resolve_site(
        db, site_id, latitude, longitude, timezone, capacity_mw, tilt, azimuth
    )
    cfg = resolved.config
    cfg.panel_efficiency = panel_efficiency

    wx = await _live.fetch(cfg.latitude, cfg.longitude, cfg.timezone, horizon=horizon)
    points = [_reading_to_point(r) for r in wx["readings"]]
    fpts = _forecast.forecast_timeline(cfg, points, mode=mode, predictor=predictor)

    timeline = [
        {
            "timestamp": p.timestamp.isoformat(),
            "ghi_w_m2": p.ghi_w_m2,
            "poa_w_m2": p.poa_w_m2,
            "cloud_cover_percent": p.cloud_cover_percent,
            "temperature_c": p.temperature_c,
            "predicted_generation_mw": p.predicted_generation_mw,
            "clearsky_generation_mw": p.clearsky_generation_mw,
            "confidence_score": p.confidence_score,
            "forecast_mode": p.forecast_mode,
            "model_version": p.model_version,
            "source_used": p.source_used,
        }
        for p in fpts
    ]
    effective_mode = fpts[0].forecast_mode if fpts else mode
    src_ids = ["SRC-PVLIB-001"]
    if wx.get("mode") != "synthetic":
        src_ids.append("SRC-OPENMETEO-001")
    if effective_mode in ("ml", "hybrid"):
        src_ids.append("SRC-KAGGLE-SOLAR-001")

    return success_response(
        data={
            "site_id": site_id,
            "capacity_mw": cfg.capacity_mw,
            "requested_mode": mode,
            "effective_mode": effective_mode,
            "weather_provider": wx.get("provider"),
            "weather_mode": wx.get("mode"),
            "horizon": horizon,
            "intervals": len(timeline),
            "peak_generation_mw": round(
                max((t["predicted_generation_mw"] for t in timeline), default=0.0), 4
            ),
            "predicted_energy_mwh": round(sum(t["predicted_generation_mw"] for t in timeline), 4),
            "sources": sr.cite(*src_ids),
            "timeline": timeline,
        }
    )
