"""Shared test fixtures, including a deterministic offline weather provider."""

from datetime import datetime, timedelta, timezone

import pytest

from app.providers.base import WeatherPoint, WeatherProvider


class FakeProvider(WeatherProvider):
    """Deterministic provider so tests never depend on the network.

    Produces a simple clear-ish day: irradiance follows a daytime bell curve.
    """

    name = "fake"

    async def fetch_forecast(self, latitude, longitude, timezone, forecast_days=1, past_days=0):
        tz = _fixed(330 * 60)  # IST
        base = datetime(2026, 6, 25, 0, 0, tzinfo=tz)
        points = []
        for h in range(24):
            ts = base + timedelta(hours=h)
            if 6 <= h <= 18:
                frac = max(0.0, _bell(h))
                ghi = 950 * frac
                dni = 800 * frac
                dhi = 120 * frac
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


def _bell(hour: float) -> float:
    import math

    return math.sin(math.pi * (hour - 6) / 12)


def _fixed(offset_seconds: int):
    return timezone(timedelta(seconds=offset_seconds))


@pytest.fixture
def fake_provider():
    return FakeProvider()
