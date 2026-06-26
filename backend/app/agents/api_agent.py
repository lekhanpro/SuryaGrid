"""APIAgent - provider rotation, failover, and quota tracking.

Manages the weather data providers: tracks which provider to use, rotates
through them on failure, and keeps a per-provider call budget so cost stays
controlled.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.logging import logger
from app.providers.base import WeatherPoint, WeatherProvider
from app.providers.open_meteo import OpenMeteoProvider


class ProviderQuota:
    """Tracks calls-per-day for a provider."""

    def __init__(self, name: str, daily_limit: int = 10_000):
        self.name = name
        self.daily_limit = daily_limit
        self.calls_today = 0
        self.last_reset: datetime = datetime.now(UTC)

    def can_call(self) -> bool:
        self._maybe_reset()
        return self.calls_today < self.daily_limit

    def record_call(self):
        self._maybe_reset()
        self.calls_today += 1

    def _maybe_reset(self):
        now = datetime.now(UTC)
        if now.date() > self.last_reset.date():
            self.calls_today = 0
            self.last_reset = now


class APIAgent:
    """Routes data requests through providers with failover."""

    def __init__(self):
        # Provider registry (in priority order).
        # Open-Meteo is free and key-less so it's the primary for now.
        # When Solcast or NASA POWER are added, they go here.
        self._providers: list[tuple[WeatherProvider, ProviderQuota]] = [
            (OpenMeteoProvider(), ProviderQuota("open-meteo", daily_limit=10_000)),
        ]

    async def fetch_weather(
        self,
        latitude: float,
        longitude: float,
        timezone_str: str = "UTC",
        forecast_days: int = 1,
        past_days: int = 0,
    ) -> tuple[list[WeatherPoint], str]:
        """Try providers in order; return data + provider name."""
        errors: list[str] = []
        for provider, quota in self._providers:
            if not quota.can_call():
                errors.append(f"{provider.name}: daily quota exhausted")
                continue
            try:
                data = await provider.fetch_forecast(
                    latitude=latitude,
                    longitude=longitude,
                    timezone=timezone_str,
                    forecast_days=forecast_days,
                    past_days=past_days,
                )
                quota.record_call()
                return data, provider.name
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
                logger.warning(f"Provider {provider.name} failed: {exc}")
                continue

        raise RuntimeError(f"All weather providers failed: {'; '.join(errors)}")

    def get_status(self) -> list[dict[str, Any]]:
        """Return quota status for all providers."""
        return [
            {
                "name": provider.name,
                "calls_today": quota.calls_today,
                "daily_limit": quota.daily_limit,
                "available": quota.can_call(),
            }
            for provider, quota in self._providers
        ]
