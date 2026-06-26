"""Timeline & summary API - real 24h+ DSM nowcast from live weather data."""

from fastapi import APIRouter, Query

from app.agents.forecast_agent import SiteConfig
from app.services.forecast_service import ForecastService
from app.services.site_store import site_store
from app.utils.response import success_response

router = APIRouter()
_service = ForecastService()


def _resolve_site(
    site_id: str,
    latitude: float,
    longitude: float,
    timezone: str,
    capacity_mw: float,
    tilt: float,
    azimuth: float,
) -> tuple[SiteConfig, float, float]:
    """Use a registered site if it exists, else build an ad-hoc config from query."""
    try:
        site = site_store.get(site_id)
        config = site_store.to_config(site)
        return (
            config,
            site["allowed_dsm_threshold_percent"],
            site["penalty_rate_per_mwh"],
        )
    except Exception:
        config = SiteConfig(
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            capacity_mw=capacity_mw,
            tilt=tilt,
            azimuth=azimuth,
        )
        return config, 10.0, 12000.0


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
):
    config, site_threshold, site_penalty = _resolve_site(
        site_id, latitude, longitude, timezone, capacity_mw, tilt, azimuth
    )
    result = await _service.build_timeline(
        site=config,
        scheduled_generation_mw=scheduled_mw,
        allowed_dsm_threshold_percent=threshold_percent
        if threshold_percent is not None
        else site_threshold,
        penalty_rate_per_mwh=penalty_rate if penalty_rate is not None else site_penalty,
        forecast_days=forecast_days,
        past_days=past_days,
    )
    return success_response(
        data={
            "site_id": site_id,
            "capacity_mw": config.capacity_mw,
            "provider": result["provider"],
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
):
    config, site_threshold, site_penalty = _resolve_site(
        site_id, latitude, longitude, timezone, capacity_mw, tilt, azimuth
    )
    result = await _service.build_timeline(
        site=config,
        scheduled_generation_mw=scheduled_mw,
        allowed_dsm_threshold_percent=threshold_percent
        if threshold_percent is not None
        else site_threshold,
        penalty_rate_per_mwh=penalty_rate if penalty_rate is not None else site_penalty,
        forecast_days=forecast_days,
    )
    summary = result["summary"]
    summary["site_id"] = site_id
    summary["capacity_mw"] = config.capacity_mw
    summary["provider"] = result["provider"]
    return success_response(data=summary)
