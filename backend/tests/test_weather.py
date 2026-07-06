"""Tests for LiveWeatherAgent: reported fallback, horizons, cache degradation."""

import asyncio
from datetime import UTC, datetime

from app.agents.live_weather_agent import LiveWeatherAgent
from app.data_sources.synthetic_weather_provider import SyntheticWeatherProvider
from app.providers.base import WeatherPoint


class _FailingProvider:
    name = "failing"

    async def fetch_forecast(self, *a, **k):
        raise RuntimeError("upstream down")

    async def fetch_current(self, *a, **k):
        raise RuntimeError("upstream down")


class _OkProvider:
    name = "stub-live"

    async def fetch_forecast(self, latitude, longitude, timezone, forecast_days=1, past_days=0):
        return [
            WeatherPoint(
                timestamp=datetime(2026, 6, 25, h, tzinfo=UTC),
                ghi_w_m2=500.0,
                dni_w_m2=0.0,
                dhi_w_m2=0.0,
                temperature_c=30.0,
                cloud_cover_percent=20.0,
                wind_speed_mps=2.0,
            )
            for h in range(24)
        ]


def test_fallback_is_reported_not_silent():
    agent = LiveWeatherAgent(provider=_FailingProvider(), fallback=SyntheticWeatherProvider())
    res = asyncio.run(agent.fetch(12.97, 77.59, "Asia/Kolkata", horizon="24h"))
    assert res["mode"] == "synthetic"
    assert "fallback" in res["provider"]
    assert res["readings_count"] > 0
    assert "synthetic fallback" in res["note"].lower()


def test_real_fetch_uncached_when_redis_absent():
    agent = LiveWeatherAgent(provider=_OkProvider(), fallback=SyntheticWeatherProvider())
    res = asyncio.run(agent.fetch(12.97, 77.59, "Asia/Kolkata", horizon="24h"))
    assert res["mode"] == "real"
    assert res["cached"] is False  # no Redis in tests -> cache is a no-op
    assert res["provider"] == "stub-live"


def test_horizon_resolution_and_note():
    agent = LiveWeatherAgent(provider=_OkProvider(), fallback=SyntheticWeatherProvider())
    res = asyncio.run(agent.fetch(12.97, 77.59, "Asia/Kolkata", horizon="15min"))
    assert res["horizon_hours"] == 1
    assert "hourly" in res["note"].lower()


def test_latest_falls_back_to_synthetic_reported():
    agent = LiveWeatherAgent(provider=_FailingProvider(), fallback=SyntheticWeatherProvider())
    res = asyncio.run(agent.latest(12.97, 77.59, "Asia/Kolkata"))
    assert res["mode"] == "synthetic"
    assert "fallback" in res["provider"]


def test_providers_status_lists_live_and_fallback():
    agent = LiveWeatherAgent()
    st = agent.providers_status()
    assert len(st) == 2
