"""Suryagrid AI Phase 1 - Solar Nowcasting & DSM Penalty Prediction System."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_agents import router as agents_router
from app.api.routes_dsm import router as dsm_router
from app.api.routes_energy import router as energy_router
from app.api.routes_forecast import router as forecast_router
from app.api.routes_health import router as health_router
from app.api.routes_kaggle import router as kaggle_router
from app.api.routes_karnataka import router as karnataka_router
from app.api.routes_locations import router as locations_router
from app.api.routes_ml import router as ml_router
from app.api.routes_predict import router as predict_router
from app.api.routes_realtime import router as realtime_router
from app.api.routes_settlement import router as settlement_router
from app.api.routes_sites import router as sites_router
from app.api.routes_sources import router as sources_router
from app.api.routes_substation_orchestrate import router as substation_workflow_router
from app.api.routes_system import router as system_router
from app.api.routes_timeline import router as timeline_router
from app.api.routes_weather import router as weather_router
from app.config import get_settings
from app.core.exceptions import AppException, app_exception_handler, validation_exception_handler
from app.core.logging import logger
from app.core.rate_limit import close_redis, init_redis
from app.core.scheduler import start_scheduler, stop_scheduler
from app.db.database import AsyncSessionLocal, dispose_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    await init_db()
    logger.info("Database initialized")
    # Seed default DSM rule profiles (idempotent). See docs/DSM_RULE_SOURCES.md.
    try:
        from app.dsm import dsm_repository

        async with AsyncSessionLocal() as session:
            seeded = await dsm_repository.seed_default_profiles(session)
        if seeded:
            logger.info(f"Seeded {seeded} DSM rule profile(s)")
    except Exception as exc:
        logger.warning(f"DSM profile seeding skipped: {exc}")
    await init_redis()
    logger.info("Redis initialized")
    start_scheduler()
    yield
    stop_scheduler()
    await close_redis()
    await dispose_db()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Solar Irradiance Nowcasting + DSM Penalty Prediction (Open-Meteo + pvlib)",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Routes
    app.include_router(health_router, prefix="/api/v1", tags=["health"])
    app.include_router(system_router, prefix="/api/v1", tags=["system"])
    app.include_router(dsm_router, prefix="/api/v1", tags=["dsm"])
    app.include_router(sites_router, prefix="/api/v1", tags=["sites"])
    app.include_router(sources_router, prefix="/api/v1", tags=["sources"])
    app.include_router(locations_router, prefix="/api/v1", tags=["locations"])
    app.include_router(weather_router, prefix="/api/v1", tags=["weather"])
    app.include_router(predict_router, prefix="/api/v1", tags=["prediction"])
    app.include_router(forecast_router, prefix="/api/v1", tags=["forecast"])
    app.include_router(ml_router, prefix="/api/v1", tags=["ml"])
    app.include_router(agents_router, prefix="/api/v1", tags=["agents"])
    app.include_router(kaggle_router, prefix="/api/v1", tags=["kaggle"])
    app.include_router(timeline_router, prefix="/api/v1", tags=["timeline"])
    app.include_router(energy_router, prefix="/api/v1", tags=["energy"])
    app.include_router(settlement_router, prefix="/api/v1", tags=["settlement"])
    app.include_router(realtime_router, prefix="/api/v1", tags=["realtime"])
    app.include_router(karnataka_router, prefix="/api/v1", tags=["karnataka"])
    # Substation-driven agent workflow (registered AFTER locations so /substations/catalog
    # and /substations/{substation_id} resolve without clashing with existing routes).
    app.include_router(substation_workflow_router, prefix="/api/v1", tags=["substation-workflow"])

    return app


app = create_app()
