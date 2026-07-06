"""APIManagementAgent - health, provider status, rate limiting, and retries.

Coordinator for cross-cutting API concerns: aggregate system health (DB / Redis /
weather providers / model), expose provider quota status, wrap the Redis rate
limiter, and provide an async retry helper for flaky upstream calls.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.agents.api_agent import APIAgent
from app.agents.live_weather_agent import LiveWeatherAgent
from app.core import rate_limit
from app.core.logging import logger
from app.data_sources.kaggle_solar_provider import KaggleSolarProvider
from app.db.database import AsyncSessionLocal, engine
from app.ml import model_registry


class APIManagementAgent:
    def __init__(self):
        self.api_agent = APIAgent()
        self.live = LiveWeatherAgent()

    async def check_rate_limit(self, key: str) -> bool:
        return await rate_limit.check_rate_limit(key)

    async def retry(self, coro_factory, attempts: int = 3, base_delay: float = 0.5):
        """Retry an async operation with exponential backoff. coro_factory() -> awaitable."""
        last_exc: Exception | None = None
        for i in range(attempts):
            try:
                return await coro_factory()
            except Exception as exc:  # noqa: BLE001 - deliberate retry boundary
                last_exc = exc
                logger.warning(f"retry {i + 1}/{attempts} after error: {exc}")
                if i < attempts - 1:
                    await asyncio.sleep(base_delay * (2**i))
        raise last_exc if last_exc else RuntimeError("retry failed")

    def provider_status(self) -> dict:
        return {"quota": self.api_agent.get_status(), "providers": self.live.providers_status()}

    async def system_status(self) -> dict:
        db_status = "disconnected"
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                db_status = "connected"
        except Exception:
            db_status = "disconnected"

        redis_status = "disconnected"
        try:
            if rate_limit.redis_client:
                await rate_limit.redis_client.ping()
                redis_status = "connected"
        except Exception:
            redis_status = "disconnected"

        return {
            "database": db_status,
            "database_engine": engine.url.get_backend_name(),
            "redis": redis_status,
            "weather_providers": self.live.providers_status(),
            "kaggle": KaggleSolarProvider().status().to_dict(),
            "model": model_registry.status(),
        }

    async def counts(self) -> dict:
        try:
            from app.db import repository

            async with AsyncSessionLocal() as session:
                return await repository.counts(session)
        except Exception:
            return {}
