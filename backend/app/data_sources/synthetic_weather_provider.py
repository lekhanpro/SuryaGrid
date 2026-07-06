"""Synthetic weather provider - deterministic offline fallback / test data.

This provider fabricates a physically plausible diurnal irradiance shape with
seeded cloud variation. It exists ONLY as a fallback when live sources are
unavailable and for offline tests. Every value it returns is labelled
`mode="synthetic"` and `source="synthetic"`; it is never presented as real data.

SOURCE: docs/DATA_SOURCE_CATALOG.md section 4 (synthetic fallback).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

from app.data_sources.base_provider import TYPE_SYNTHETIC, DataProvider, ProviderStatus
from app.providers.base import WeatherPoint, WeatherProvider

_PEAK_GHI_W_M2 = 950.0  # clear-sky midday peak used for the synthetic shape


def _hash01(day_of_year: int, hour: int) -> float:
    """Deterministic pseudo-random value in [0,1) from (day, hour)."""
    x = math.sin(day_of_year * 12.9898 + hour * 78.233) * 43758.5453
    return x - math.floor(x)


def _resolve_tz(timezone_str: str):
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(timezone_str)
    except Exception:
        return UTC


class SyntheticWeatherProvider(WeatherProvider, DataProvider):
    """Deterministic diurnal weather generator (offline)."""

    name = "synthetic"
    source_id = "synthetic"
    provider_type = TYPE_SYNTHETIC

    def __init__(self, cloudiness: float = 0.35):
        # Baseline cloud fraction 0..1; combined with a seeded per-hour variation.
        self.cloudiness = max(0.0, min(1.0, cloudiness))

    async def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        forecast_days: int = 1,
        past_days: int = 0,
    ) -> list[WeatherPoint]:
        tz = _resolve_tz(timezone)
        now = datetime.now(tz)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=past_days)
        total_hours = (past_days + max(1, forecast_days)) * 24
        return [self._point(start + timedelta(hours=h)) for h in range(total_hours)]

    def _point(self, ts: datetime) -> WeatherPoint:
        h = ts.hour
        doy = ts.timetuple().tm_yday
        # Diurnal elevation proxy: 0 before 6h and after 18h, peak at noon.
        elev = math.sin(math.pi * (h - 6) / 12.0) if 6 <= h <= 18 else 0.0
        elev = max(0.0, elev)
        cloud = max(0.0, min(1.0, 0.5 * self.cloudiness + 0.5 * _hash01(doy, h)))
        ghi = round(elev * _PEAK_GHI_W_M2 * (1.0 - 0.7 * cloud), 1)
        temp = round(18.0 + 10.0 * elev - 3.0 * cloud, 1)
        wind = round(2.0 + 3.0 * cloud, 1)
        # DNI/DHI left at 0 so the pvlib pipeline derives them via Erbs from GHI.
        return WeatherPoint(
            timestamp=ts,
            ghi_w_m2=ghi,
            dni_w_m2=0.0,
            dhi_w_m2=0.0,
            temperature_c=temp,
            cloud_cover_percent=round(cloud * 100.0, 1),
            wind_speed_mps=wind,
            humidity_percent=round(45.0 + 40.0 * cloud, 1),
            pressure_hpa=round(1011.0 - 2.0 * cloud, 1),
            precipitation_probability_percent=round(max(0.0, (cloud - 0.4)) * 100.0, 1),
            weather_code=0,
        )

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            source_id=self.source_id,
            provider_type=self.provider_type,
            available=True,
            detail="Synthetic fallback generator (deterministic). Not real observations.",
            loaded=True,
            mode="synthetic",
        )
