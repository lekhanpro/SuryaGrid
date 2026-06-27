"""Karnataka / BESCOM API - site seeding, KERC DSM, BESCOM connector status."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.karnataka_sites import KARNATAKA_SITES, to_site_payload
from app.db import repository
from app.db.session import get_db
from app.integrations.bescom import BescomConnector
from app.integrations.karnataka_dsm import KarnatakaDSM
from app.services.forecast_service import ForecastService
from app.services.site_resolver import resolve_site
from app.utils.response import success_response

router = APIRouter()
_dsm = KarnatakaDSM()
_bescom = BescomConnector()
_service = ForecastService()


@router.post("/karnataka/seed")
async def seed_karnataka(db: AsyncSession = Depends(get_db)):
    """Register the Karnataka solar sites (idempotent on name)."""
    existing = {s.name for s in await repository.list_sites(db)}
    created = []
    for entry in KARNATAKA_SITES:
        if entry["name"] in existing:
            continue
        site = await repository.create_site(db, to_site_payload(entry))
        created.append({"id": str(site.id), "name": site.name, "capacity_mw": site.capacity_mw})
    return success_response(
        data={"created": created, "total_registry": len(KARNATAKA_SITES)},
        message=f"Seeded {len(created)} Karnataka site(s)",
    )


@router.get("/karnataka/regions")
async def karnataka_regions():
    regions: dict[str, list] = {}
    for e in KARNATAKA_SITES:
        regions.setdefault(e["region"], []).append(
            {"name": e["name"], "capacity_mw": e["capacity_mw"], "discom": e["discom"]}
        )
    total = sum(e["capacity_mw"] for e in KARNATAKA_SITES)
    return success_response(
        data={"total_capacity_mw": total, "regions": regions, "dsm_band_percent": _dsm.band_percent}
    )


@router.get("/bescom/status")
async def bescom_status():
    return success_response(
        data={
            "connector": _bescom.status(),
            "kerc_solar_band_percent": _dsm.band_percent,
            "slabs": [
                {"range_percent": f"{lo:.0f}-{hi:.0f}", "rate_inr_per_kwh": r}
                for lo, hi, r in _dsm.slabs
            ],
        }
    )


@router.post("/dsm/karnataka/{site_id}")
async def karnataka_dsm_day(
    site_id: str,
    latitude: float = Query(default=12.97, ge=-90, le=90),
    longitude: float = Query(default=77.59, ge=-180, le=180),
    timezone: str = Query(default="Asia/Kolkata"),
    capacity_mw: float = Query(default=50.0, gt=0),
    tilt: float = Query(default=13.0, ge=0, le=90),
    azimuth: float = Query(default=180.0, ge=0, le=360),
    db: AsyncSession = Depends(get_db),
):
    """Settle a day under the KERC/BESCOM DSM framework (±5% band, slab charges)."""
    resolved = await resolve_site(
        db, site_id, latitude, longitude, timezone, capacity_mw, tilt, azimuth
    )
    result = await _service.build_timeline(
        site=resolved.config,
        scheduled_generation_mw=None,
        allowed_dsm_threshold_percent=_dsm.band_percent,
        penalty_rate_per_mwh=resolved.penalty_rate_per_mwh,
    )
    timeline = result["timeline"]
    cap = resolved.config.capacity_mw

    intervals = []
    total_charge = 0.0
    breaches = 0
    for e in timeline:
        actual = e["predicted_generation_mw"]
        scheduled = e["scheduled_generation_mw"]
        # BESCOM connector supplies "actual" (simulated = nowcast until live feed).
        telem = _bescom.actual_injection(actual, e["timestamp"])
        r = _dsm.settle(
            actual_mw=telem.actual_injection_mw,
            scheduled_mw=scheduled,
            available_capacity_mw=cap,
            interval_hours=1.0,
        )
        total_charge += r.dsm_charge_inr
        if not r.within_band:
            breaches += 1
        intervals.append(
            {
                "timestamp": e["timestamp"],
                "actual_mw": r.actual_mw,
                "scheduled_mw": r.scheduled_mw,
                "deviation_percent": r.deviation_percent,
                "within_band": r.within_band,
                "direction": r.direction,
                "dsm_charge_inr": r.dsm_charge_inr,
            }
        )

    return success_response(
        data={
            "site_id": site_id,
            "framework": "KERC / BESCOM intra-state DSM",
            "band_percent": _dsm.band_percent,
            "feed_mode": _bescom.mode.value,
            "capacity_mw": cap,
            "intervals": len(intervals),
            "band_breaches": breaches,
            "total_dsm_charge_inr": round(total_charge, 2),
            "timeline": intervals,
        }
    )
