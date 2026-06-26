"""Weather provider abstraction.

A provider returns real, time-stamped irradiance and weather observations/forecasts
for a geographic location. The forecast pipeline (pvlib) is provider-agnostic, so
new sources (Solcast, NASA POWER, ...) can be added by implementing WeatherProvider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class WeatherPoint:
    """A single hourly weather/irradiance observation or forecast.

    Irradiance components are in W/m^2, the inputs pvlib needs for transposition.
    """

    timestamp: datetime          # timezone-aware, in the site's local timezone
    ghi_w_m2: float              # global horizontal irradiance
    dni_w_m2: float              # direct normal irradiance
    dhi_w_m2: float              # diffuse horizontal irradiance
    temperature_c: float         # air temperature at 2m
    cloud_cover_percent: float   # total cloud cover
    wind_speed_mps: float        # wind speed at 10m


class WeatherProvider(ABC):
    """Interface for a real weather/irradiance data source."""

    name: str = "base"

    @abstractmethod
    async def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        forecast_days: int = 1,
        past_days: int = 0,
    ) -> list[WeatherPoint]:
        """Return hourly weather points for the location."""
        raise NotImplementedError
