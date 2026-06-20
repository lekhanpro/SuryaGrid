"""Health check endpoint."""

from fastapi import APIRouter
from app.config import get_settings
from app.core.rate_limit import redis_client
from app.db.database import engine
from app.utils.response import success_response
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
async def health_check():
    settings = get_settings()

    # Check DB
    db_status = "disconnected"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        pass

    # Check Redis
    redis_status = "disconnected"
    try:
        if redis_client:
            await redis_client.ping()
            redis_status = "connected"
    except Exception:
        pass

    return success_response(data={
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "redis": redis_status,
    })
