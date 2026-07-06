"""LiveWeatherAgent - real forecast ingestion with Redis caching and fallback.

Fetches live hourly forecasts (Open-Meteo via LiveWeatherProvider) for solar-site
and substation coordinates over a configurable horizon. Responses are cached in
Redis (bucketed by hour) so repeated requests within the same hour do not re-hit
the upstream API. If the live source fails, the agent falls back to the synthetic
provider but REPORTS it (provider name + mode='synthetic') - never a silent fake.

Horizons: 15min / 30min / 1h / 24h / 7d. The free Open-Meteo tier is hourly, so
sub-hourly horizons resolve to the nearest hourly forecast (documented limitation).

SOURCE: docs/SOURCE_REGISTRY.md#src-openmeteo-001 (SRC-OPENMETEO-001)
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime

from app.core import rate_limit
from app.core.logging import logger
from app.data_sources.live_weather_provider import LiveWeatherProvider
from app.data_sources.synthetic_weather_provider import SyntheticWeatherProvider
from app.providers.base import WeatherPoint

_FORECAST_TTL_SECONDS = 3600  # one hour: matches Open-Meteo hourly resolution
_CURRENT_TTL_SECONDS = 900  # 15 minutes


def _point_to_reading(p: WeatherPoint) -> dict:
    return {
        "timestamp": p.timestamp.isoformat(),
        "ghi_w_m2": p.ghi_w_m2,
        "dni_w_m2": p.dni_w_m2,
        "dhi_w_m2": p.dhi_w_m2,
        "temperature_c": p.temperature_c,
        "cloud_cover_percent": p.cloud_cover_percent,
        "wind_speed_mps": p.wind_speed_mps,
        "humidity_percent": p.humidity_percent,
        "pressure_hpa": p.pressure_hpa,
        "precipitation_probability_percent": p.precipitation_probability_percent,
        "weather_code": p.weather_code,
    }


class LiveWeatherAgent:
    def __init__(
        self,
        provider: LiveWeatherProvider | None = None,
        fallback: SyntheticWeatherProvider | None = None,
    ):
        self.provider = provider or LiveWeatherProvider()
        self.fallback = fallback or SyntheticWeatherProvider()

    # ---- Redis cache helpers -------------------------------------------
    @staticmethod
    async def _cache_get(key: str):
        client = rate_limit.redis_client
        if client is None:
            return None
        try:
            raw = await client.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:  # cache is best-effort
            logger.warning(f"Redis get failed: {exc}")
            return None

    @staticmethod
    async def _cache_set(key: str, value: dict, ttl: int) -> None:
        client = rate_limit.redis_client
        if client is None:
            return
        try:
            await client.set(key, json.dumps(value), ex=ttl)
        except Exception as exc:
            logger.warning(f"Redis set failed: {exc}")

    # ---- forecast -------------------------------------------------------
    async def fetch(
        self,
        latitude: float,
        longitude: float,
        timezone: str = "Asia/Kolkata",
        horizon: str = "24h",
        past_days: int = 0,
    ) -> dict:
        """Fetch a live forecast for a coordinate over a horizon, with caching."""
        hours, note = LiveWeatherProvider.resolve_horizon(horizon)
        forecast_days = max(1, math.ceil(hours / 24))
        bucket = datetime.now(UTC).strftime("%Y%m%d%H")
        cache_key = f"wx:{round(latitude, 2)}:{round(longitude, 2)}:{horizon}:{past_days}:{bucket}"

        cached = await self._cache_get(cache_key)
        if cached is not None:
            cached["cached"] = True
            return cached

        provider_name = self.provider.name
        mode = "real"
        try:
            points = await self.provider.fetch_forecast(
                latitude, longitude, timezone, forecast_days=forecast_days, past_days=past_days
            )
        except Exception as exc:
            logger.warning(f"Live weather failed, using synthetic fallback: {exc}")
            points = await self.fallback.fetch_forecast(
                latitude, longitude, timezone, forecast_days=forecast_days, past_days=past_days
            )
            provider_name = f"{self.fallback.name} (fallback)"
            mode = "synthetic"
            note = (note + " Live source unavailable; synthetic fallback used.").strip()

        readings = [_point_to_reading(p) for p in points]
        result = {
            "provider": provider_name,
            "mode": mode,
            "horizon": horizon,
            "horizon_hours": hours,
            "note": note,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "readings_count": len(readings),
            "readings": readings,
            "cached": False,
            "fetched_at": datetime.now(UTC).isoformat(),
        }
        if mode == "real":  # only cache real data
            await self._cache_set(cache_key, result, _FORECAST_TTL_SECONDS)
        return result

    async def latest(
        self, latitude: float, longitude: float, timezone: str = "Asia/Kolkata"
    ) -> dict:
        """Latest current conditions (short-cache), real Open-Meteo `current` block."""
        bucket = datetime.now(UTC).strftime("%Y%m%d%H%M")[:-1]  # ~10-min bucket
        cache_key = f"wxcur:{round(latitude, 3)}:{round(longitude, 3)}:{bucket}"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            cached["cached"] = True
            return cached
        try:
            cur = await self.provider.fetch_current(latitude, longitude, timezone)
            cur.update({"provider": self.provider.name, "mode": "real", "cached": False})
            await self._cache_set(cache_key, cur, _CURRENT_TTL_SECONDS)
            return cur
        except Exception as exc:
            logger.warning(f"Live current failed, synthetic fallback: {exc}")
            pts = await self.fallback.fetch_forecast(latitude, longitude, timezone, forecast_days=1)
            now_hour = datetime.now(UTC).hour
            p = min(pts, key=lambda x: abs(x.timestamp.hour - now_hour))
            reading = _point_to_reading(p)
            reading.update(
                {
                    "provider": f"{self.fallback.name} (fallback)",
                    "mode": "synthetic",
                    "cached": False,
                }
            )
            return reading

    def providers_status(self) -> list[dict]:
        """Status of the live provider and the synthetic fallback."""
        return [self.provider.status().to_dict(), self.fallback.status().to_dict()]
