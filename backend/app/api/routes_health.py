"""Health check endpoint."""

from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.core import rate_limit
from app.db.database import AsyncSessionLocal, engine
from app.utils.response import success_response

router = APIRouter()


@router.get("/health")
async def health_check():
    settings = get_settings()

    # Check DB and gather row counts
    db_status = "disconnected"
    db_counts: dict = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = "connected"
        from app.db import repository

        async with AsyncSessionLocal() as session:
            db_counts = await repository.counts(session)
    except Exception:
        pass

    # Check Redis
    redis_status = "disconnected"
    try:
        if rate_limit.redis_client:
            await rate_limit.redis_client.ping()
            redis_status = "connected"
    except Exception:
        pass

    dialect = engine.url.get_backend_name()

    return success_response(
        data={
            "status": "healthy",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "database": db_status,
            "database_engine": dialect,
            "redis": redis_status,
            "record_counts": db_counts,
        }
    )
