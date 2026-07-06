"""Open-Meteo weather provider.

Open-Meteo (https://open-meteo.com) is a free, key-less weather API that exposes
real hourly solar irradiance components (GHI/DNI/DHI), temperature, cloud cover and
wind. It is the primary real data source for the platform; the same pvlib pipeline
runs unchanged if a paid provider (Solcast) is added later.
"""

from __future__ import annotations

from datetime import datetime

import httpx

from app.core.exceptions import AppException
from app.core.logging import logger
from app.providers.base import WeatherPoint, WeatherProvider

_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
_ARCHIVE_ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"

_HOURLY_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "cloud_cover",
    "shortwave_radiation",  # GHI
    "direct_normal_irradiance",  # DNI
    "diffuse_radiation",  # DHI
    "wind_speed_10m",
    "surface_pressure",
    "precipitation_probability",
    "weather_code",
]


class ProviderError(AppException):
    def __init__(self, detail: str = "Weather provider unavailable"):
        super().__init__(status_code=502, detail=detail, error_code="PROVIDER_ERROR")


class OpenMeteoProvider(WeatherProvider):
    name = "open-meteo"

    def __init__(self, timeout_seconds: float = 20.0):
        self._timeout = timeout_seconds

    async def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        forecast_days: int = 1,
        past_days: int = 0,
    ) -> list[WeatherPoint]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(_HOURLY_FIELDS),
            "timezone": timezone,
            "forecast_days": max(1, min(forecast_days, 16)),
        }
        if past_days:
            params["past_days"] = max(0, min(past_days, 92))

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(_ENDPOINT, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError as exc:
            logger.error(f"Open-Meteo request failed: {exc}")
            raise ProviderError(f"Open-Meteo request failed: {exc}") from exc

        return self._parse(payload)

    async def fetch_current(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
    ) -> dict:
        """Fetch the latest real-time conditions (15-min resolution)."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,cloud_cover,shortwave_radiation,"
            "direct_normal_irradiance,diffuse_radiation,wind_speed_10m,surface_pressure,"
            "precipitation,weather_code",
            "timezone": timezone,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(_ENDPOINT, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError as exc:
            logger.error(f"Open-Meteo current request failed: {exc}")
            raise ProviderError(f"Open-Meteo current request failed: {exc}") from exc

        cur = payload.get("current", {})
        return {
            "timestamp": cur.get("time"),
            "ghi_w_m2": _f(cur.get("shortwave_radiation")),
            "dni_w_m2": _f(cur.get("direct_normal_irradiance")),
            "dhi_w_m2": _f(cur.get("diffuse_radiation")),
            "temperature_c": _f(cur.get("temperature_2m")),
            "cloud_cover_percent": _f(cur.get("cloud_cover")),
            "wind_speed_mps": _f(cur.get("wind_speed_10m")),
            "humidity_percent": _f(cur.get("relative_humidity_2m")),
            "pressure_hpa": _f(cur.get("surface_pressure")),
            "precipitation_probability_percent": _f(cur.get("precipitation")),
            "weather_code": int(_f(cur.get("weather_code"))),
        }

    async def fetch_archive(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        start_date: str,
        end_date: str,
    ) -> list[WeatherPoint]:
        """Fetch real historical hourly weather from the Open-Meteo archive.

        Used to train the RL policy on genuine past irradiance, not simulation.
        Dates are ISO strings (YYYY-MM-DD).
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(_HOURLY_FIELDS),
            "timezone": timezone,
            "start_date": start_date,
            "end_date": end_date,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout * 2) as client:
                resp = await client.get(_ARCHIVE_ENDPOINT, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError as exc:
            logger.error(f"Open-Meteo archive request failed: {exc}")
            raise ProviderError(f"Open-Meteo archive request failed: {exc}") from exc

        return self._parse(payload)

    @staticmethod
    def _parse(payload: dict) -> list[WeatherPoint]:
        hourly = payload.get("hourly")
        if not hourly or "time" not in hourly:
            raise ProviderError("Open-Meteo returned no hourly data")

        times = hourly["time"]
        offset_seconds = payload.get("utc_offset_seconds", 0)
        tz = _fixed_timezone(offset_seconds)

        def col(key: str) -> list:
            return hourly.get(key) or [0.0] * len(times)

        temp = col("temperature_2m")
        cloud = col("cloud_cover")
        ghi = col("shortwave_radiation")
        dni = col("direct_normal_irradiance")
        dhi = col("diffuse_radiation")
        wind = col("wind_speed_10m")
        humidity = col("relative_humidity_2m")
        pressure = col("surface_pressure")
        precip = col("precipitation_probability")
        wcode = col("weather_code")

        points: list[WeatherPoint] = []
        for i, t in enumerate(times):
            ts = datetime.fromisoformat(t).replace(tzinfo=tz)
            points.append(
                WeatherPoint(
                    timestamp=ts,
                    ghi_w_m2=_f(ghi[i]),
                    dni_w_m2=_f(dni[i]),
                    dhi_w_m2=_f(dhi[i]),
                    temperature_c=_f(temp[i]),
                    cloud_cover_percent=_f(cloud[i]),
                    wind_speed_mps=_f(wind[i]),
                    humidity_percent=_f(humidity[i]),
                    pressure_hpa=_f(pressure[i]),
                    precipitation_probability_percent=_f(precip[i]),
                    weather_code=int(_f(wcode[i])),
                )
            )
        return points


def _f(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _fixed_timezone(offset_seconds: int):
    from datetime import timedelta, timezone

    return timezone(timedelta(seconds=offset_seconds))
