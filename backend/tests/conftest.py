"""Shared test fixtures: isolated SQLite DB + deterministic offline provider."""

import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest

# Use an isolated on-disk SQLite DB for tests (set before app imports).
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_suryagrid.db"

from app.providers.base import WeatherPoint, WeatherProvider  # noqa: E402


def _fixed(offset_seconds: int):
    return timezone(timedelta(seconds=offset_seconds))


def _bell(hour: float) -> float:
    import math

    return math.sin(math.pi * (hour - 6) / 12)


class FakeProvider(WeatherProvider):
    """Deterministic provider so tests never depend on the network."""

    name = "fake"

    async def fetch_forecast(self, latitude, longitude, timezone, forecast_days=1, past_days=0):
        tz = _fixed(330 * 60)  # IST
        base = datetime(2026, 6, 25, 0, 0, tzinfo=tz)
        points = []
        for h in range(24):
            ts = base + timedelta(hours=h)
            if 6 <= h <= 18:
                frac = max(0.0, _bell(h))
                ghi, dni, dhi = 950 * frac, 800 * frac, 120 * frac
            else:
                ghi = dni = dhi = 0.0
            points.append(
                WeatherPoint(
                    timestamp=ts,
                    ghi_w_m2=ghi,
                    dni_w_m2=dni,
                    dhi_w_m2=dhi,
                    temperature_c=30.0,
                    cloud_cover_percent=20.0,
                    wind_speed_mps=2.0,
                )
            )
        return points


def use_fake_provider():
    """Inject the deterministic provider into all routes that fetch weather."""
    from app.agents.api_agent import ProviderQuota
    from app.api import routes_energy, routes_settlement, routes_timeline, routes_weather

    fake = FakeProvider()
    routes_timeline._service.provider = fake
    routes_energy._service.provider = fake
    routes_settlement._service.provider = fake
    routes_weather._api_agent._providers = [(fake, ProviderQuota("fake"))]


@pytest.fixture(scope="session", autouse=True)
def _init_test_db():
    """Create tables in the isolated test DB before any test runs."""
    from app.db.database import init_db

    asyncio.run(init_db())
    yield


@pytest.fixture
def fake_provider():
    return FakeProvider()
