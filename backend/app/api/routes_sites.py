"""Sites API - register and list solar sites (persisted in the database)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db import repository
from app.db.session import get_db
from app.schemas.requests import SiteCreateRequest
from app.utils.response import success_response

router = APIRouter()


def _serialize(site) -> dict:
    return {
        "id": str(site.id),
        "name": site.name,
        "latitude": site.latitude,
        "longitude": site.longitude,
        "timezone": site.timezone,
        "capacity_mw": site.capacity_mw,
        "tilt": site.tilt,
        "azimuth": site.azimuth,
        "altitude": site.altitude,
        "allowed_dsm_threshold_percent": site.allowed_dsm_threshold_percent,
        "penalty_rate_per_mwh": site.penalty_rate_per_mwh,
        "created_at": site.created_at.isoformat() if site.created_at else None,
    }


@router.post("/sites")
async def create_site(req: SiteCreateRequest, db: AsyncSession = Depends(get_db)):
    site = await repository.create_site(db, req.model_dump())
    return success_response(data=_serialize(site), message="Site created")


@router.get("/sites")
async def list_sites(db: AsyncSession = Depends(get_db)):
    sites = await repository.list_sites(db)
    return success_response(data=[_serialize(s) for s in sites])


@router.get("/sites/{site_id}")
async def get_site(site_id: str, db: AsyncSession = Depends(get_db)):
    site = await repository.get_site(db, site_id)
    if site is None:
        raise NotFoundError(f"Site {site_id} not found")
    return success_response(data=_serialize(site))
