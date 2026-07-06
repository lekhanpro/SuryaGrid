"""System API - aggregate health of DB, Redis, weather providers, and the model."""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.api_management_agent import APIManagementAgent
from app.config import get_settings
from app.utils.response import success_response

router = APIRouter()
_mgmt = APIManagementAgent()


@router.get("/system/status")
async def system_status():
    settings = get_settings()
    status = await _mgmt.system_status()
    status["counts"] = await _mgmt.counts()
    status["app"] = {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }
    healthy = status["database"] == "connected"
    return success_response(
        data={"healthy": healthy, **status},
        message="System status",
    )
