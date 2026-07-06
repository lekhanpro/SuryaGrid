"""Locations & substations API.

GET  /locations                     - unified list of discoverable locations
GET  /locations/available           - aggregate of sites/substations/weather points
GET  /substations                   - list imported substations
POST /substations/import            - import from OSM (lat/lon) or CSV (csv_text)
GET  /substations/nearest/{site_id} - nearest substation to a site
GET  /sites/{site_id}/data-coverage - data availability flags for a site
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.location_data_agent import LocationDataAgent
from app.core.exceptions import AppException
from app.db import repository
from app.db.session import get_db
from app.schemas.requests import SubstationImportRequest
from app.utils.response import success_response

router = APIRouter()
_agent = LocationDataAgent()


@router.get("/locations")
async def list_locations(db: AsyncSession = Depends(get_db)):
    """Unified, discoverable list of every location the platform knows about."""
    agg = await _agent.available_locations(db)
    unified = []
    for s in agg["sites"]:
        unified.append({**s, "type": "site", "source": "registered"})
    for e in agg["site_registry"]:
        unified.append({**e, "type": "site_registry", "source": "preset"})
    for sub in agg["substations"]:
        unified.append(
            {
                "id": sub["id"],
                "name": sub["name"],
                "latitude": sub["latitude"],
                "longitude": sub["longitude"],
                "type": "substation",
                "source": sub["source_name"],
                "source_confidence": sub["source_confidence"],
            }
        )
    return success_response(data={"count": len(unified), "locations": unified})


@router.get("/locations/available")
async def available_locations(db: AsyncSession = Depends(get_db)):
    return success_response(data=await _agent.available_locations(db))


@router.get("/substations")
async def list_substations(
    limit: int = Query(default=500, ge=1, le=2000), db: AsyncSession = Depends(get_db)
):
    from app.agents.location_data_agent import _serialize_substation

    subs = await repository.list_substations(db, limit=limit)
    return success_response(
        data={"count": len(subs), "substations": [_serialize_substation(s) for s in subs]}
    )


@router.post("/substations/import")
async def import_substations(req: SubstationImportRequest, db: AsyncSession = Depends(get_db)):
    if req.csv_text:
        result = await _agent.import_substations_csv(db, req.csv_text)
    elif req.latitude is not None and req.longitude is not None:
        result = await _agent.import_substations_osm(db, req.latitude, req.longitude, req.radius_km)
    else:
        raise AppException(
            status_code=400,
            detail="Provide csv_text for manual import, or latitude+longitude for OSM import.",
            error_code="VALIDATION_ERROR",
        )
    return success_response(data=result, message="Substation import complete")


@router.get("/substations/nearest/{site_id}")
async def nearest_substation(
    site_id: str,
    latitude: float = Query(default=12.97, ge=-90, le=90),
    longitude: float = Query(default=77.59, ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
):
    return success_response(data=await _agent.nearest_for_site(db, site_id, latitude, longitude))


@router.get("/sites/{site_id}/data-coverage")
async def data_coverage(
    site_id: str,
    latitude: float = Query(default=12.97, ge=-90, le=90),
    longitude: float = Query(default=77.59, ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
):
    return success_response(data=await _agent.data_coverage(db, site_id, latitude, longitude))
