"""Sites API - create and list solar sites."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter
from app.schemas.requests import SiteCreateRequest
from app.utils.response import success_response
from app.core.exceptions import NotFoundError

router = APIRouter()

# In-memory store (replaced by DB when PostgreSQL is connected)
_sites: dict[str, dict] = {}


@router.post("/sites")
async def create_site(req: SiteCreateRequest):
    site_id = str(uuid.uuid4())
    site = {
        "id": site_id,
        "name": req.name,
        "latitude": req.latitude,
        "longitude": req.longitude,
        "timezone": req.timezone,
        "capacity_mw": req.capacity_mw,
        "panel_efficiency": req.panel_efficiency,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _sites[site_id] = site
    return success_response(data=site, message="Site created")


@router.get("/sites")
async def list_sites():
    return success_response(data=list(_sites.values()))


@router.get("/sites/{site_id}")
async def get_site(site_id: str):
    if site_id not in _sites:
        raise NotFoundError(f"Site {site_id} not found")
    return success_response(data=_sites[site_id])


def get_site_store() -> dict:
    """Access for other routes."""
    return _sites
