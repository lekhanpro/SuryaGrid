"""Real-time API - current conditions and on-demand ingestion."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.api_agent import APIAgent
from app.db import repository
from app.db.session import get_db
from app.utils.response import success_response

router = APIRouter()
_api_agent = APIAgent()


@router.get("/weather/current/{site_id}")
async def current_weather(
    site_id: str,
    latitude: float = Query(default=12.97, ge=-90, le=90),
    longitude: float = Query(default=77.59, ge=-180, le=180),
    timezone: str = Query(default="Asia/Kolkata"),
    db: AsyncSession = Depends(get_db),
):
    site = await repository.get_site(db, site_id)
    if site is not None:
        latitude, longitude, timezone = site.latitude, site.longitude, site.timezone
    provider = _api_agent._providers[0][0]
    cur = await provider.fetch_current(latitude, longitude, timezone)
    return success_response(data={"site_id": site_id, "provider": provider.name, **cur})


@router.post("/ingest/current/{site_id}")
async def ingest_current(site_id: str, db: AsyncSession = Depends(get_db)):
    """Persist a single real-time reading for a registered site."""
    site = await repository.get_site(db, site_id)
    if site is None:
        return success_response(
            data={"site_id": site_id, "ingested": False, "reason": "site not registered"}
        )
    provider = _api_agent._providers[0][0]
    cur = await provider.fetch_current(site.latitude, site.longitude, site.timezone)
    if not cur.get("timestamp"):
        return success_response(data={"site_id": site_id, "ingested": False})
    ts = datetime.fromisoformat(cur["timestamp"])
    await repository.save_readings(
        db,
        site.id,
        [
            {
                "ts": ts,
                "ghi": cur["ghi_w_m2"],
                "dni": cur["dni_w_m2"],
                "dhi": cur["dhi_w_m2"],
                "temp": cur["temperature_c"],
                "cloud_cover": cur["cloud_cover_percent"],
                "wind": cur["wind_speed_mps"],
            }
        ],
        source="open-meteo-current",
    )
    return success_response(
        data={"site_id": site_id, "ingested": True, "timestamp": cur["timestamp"], **cur}
    )
