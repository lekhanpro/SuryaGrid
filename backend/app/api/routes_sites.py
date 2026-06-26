"""Sites API - register and list solar sites."""

from fastapi import APIRouter

from app.schemas.requests import SiteCreateRequest
from app.services.site_store import site_store
from app.utils.response import success_response

router = APIRouter()


@router.post("/sites")
async def create_site(req: SiteCreateRequest):
    site = site_store.create(req.model_dump())
    return success_response(data=site, message="Site created")


@router.get("/sites")
async def list_sites():
    return success_response(data=site_store.list())


@router.get("/sites/{site_id}")
async def get_site(site_id: str):
    return success_response(data=site_store.get(site_id))
