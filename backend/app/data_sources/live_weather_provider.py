"""Live weather provider - real forecast data (Open-Meteo primary).

Wraps the real, key-less Open-Meteo client (app/providers/open_meteo.py) and adds
the DataProvider status contract plus forecast-horizon helpers. Kept modular so
Solcast / NASA POWER can be added as alternative backends later without touching
the pvlib / ML pipeline.

SOURCE: docs/SOURCE_REGISTRY.md#src-openmeteo-001 (SRC-OPENMETEO-001)
"""

from __future__ import annotations

from app.data_sources.base_provider import TYPE_LIVE_WEATHER, DataProvider, ProviderStatus
from app.providers.base import WeatherPoint, WeatherProvider
from app.providers.open_meteo import OpenMeteoProvider

# Supported forecast horizons -> (label, hours). Open-Meteo is hourly, so sub-hourly
# horizons resolve to the nearest hourly forecast (documented limitation).
HORIZONS: dict[str, int] = {
    "15min": 1,  # nearest hourly (no minute-level nowcast on the free tier)
    "30min": 1,  # nearest hourly
    "1h": 1,
    "24h": 24,
    "7d": 24 * 7,
}


class LiveWeatherProvider(WeatherProvider, DataProvider):
    """Real live weather forecasts via Open-Meteo."""

    name = "open-meteo"
    source_id = "SRC-OPENMETEO-001"
    provider_type = TYPE_LIVE_WEATHER

    def __init__(self, backend: OpenMeteoProvider | None = None):
        self._backend = backend or OpenMeteoProvider()

    async def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        forecast_days: int = 1,
        past_days: int = 0,
    ) -> list[WeatherPoint]:
        return await self._backend.fetch_forecast(
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            forecast_days=forecast_days,
            past_days=past_days,
        )

    async def fetch_current(self, latitude: float, longitude: float, timezone: str) -> dict:
        return await self._backend.fetch_current(latitude, longitude, timezone)

    async def fetch_archive(
        self, latitude: float, longitude: float, timezone: str, start_date: str, end_date: str
    ) -> list[WeatherPoint]:
        return await self._backend.fetch_archive(
            latitude, longitude, timezone, start_date, end_date
        )

    @staticmethod
    def resolve_horizon(horizon: str) -> tuple[int, str]:
        """Map a horizon label to (hours, note about any limitation)."""
        hours = HORIZONS.get(horizon)
        if hours is None:
            return 24, f"Unknown horizon '{horizon}'; defaulting to 24h."
        note = ""
        if horizon in ("15min", "30min"):
            note = (
                "Open-Meteo free tier is hourly; sub-hourly horizon resolved to the "
                "nearest hourly forecast (documented limitation)."
            )
        return hours, note

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            source_id=self.source_id,
            provider_type=self.provider_type,
            available=True,  # key-less, generally reachable; actual reachability checked on call
            detail="Open-Meteo live forecast (key-less). Hourly resolution, up to 16 days.",
            mode="real",
            extra={"horizons": list(HORIZONS.keys())},
        )
