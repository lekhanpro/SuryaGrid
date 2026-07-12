"""NASA POWER weather provider (reanalysis / near-real-time, NOT a live forecast).

NASA POWER (https://power.larc.nasa.gov, SRC-NASA-POWER-001) serves MERRA-2/CERES
derived hourly irradiance and meteorology with a latency of days. It is used for
HISTORICAL FILL and cross-validation of Open-Meteo, never as a live forecast:

  * ``data_kind = "reanalysis_nrt"`` travels with the provider so callers can label
    the series honestly.
  * ``fetch_forecast`` only ever returns rows with timestamps <= now (the requested
    ``past_days`` window); future hours are impossible for reanalysis and are never
    fabricated.
  * Fill values (-999) are skipped, not zero-filled.
  * Responses are cached in-process (6 h TTL) and each fetch records freshness meta
    in ``last_fetch_meta``.

API: GET /api/temporal/hourly/point with time-standard=UTC; keys are YYYYMMDDHH in
UTC and are converted explicitly to the site timezone here.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import httpx

from app.core.exceptions import AppException
from app.core.logging import logger
from app.providers.base import WeatherPoint, WeatherProvider

_ENDPOINT = "https://power.larc.nasa.gov/api/temporal/hourly/point"
_PARAMETERS = "ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DNI,ALLSKY_SFC_SW_DIFF,T2M,RH2M,WS10M,PS,CLOUD_AMT"
_FILL = -999.0
_CACHE_TTL_S = 6 * 3600.0


class NasaPowerError(AppException):
    def __init__(self, detail: str):
        super().__init__(status_code=502, detail=detail, error_code="PROVIDER_ERROR")


def _resolve_tz(timezone_str: str):
    from zoneinfo import ZoneInfo

    return ZoneInfo(timezone_str)


class NasaPowerProvider(WeatherProvider):
    """Historical-fill / cross-check provider over the NASA POWER hourly API."""

    name = "nasa-power"
    source_id = "SRC-NASA-POWER-001"
    data_kind = "reanalysis_nrt"  # never a live forecast

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None, timeout_s: float = 30.0):
        self._transport = transport  # injectable for offline tests
        self._timeout_s = timeout_s
        self._cache: dict[tuple, tuple[float, list[WeatherPoint]]] = {}
        self.last_fetch_meta: dict = {}

    async def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        forecast_days: int = 1,
        past_days: int = 0,
    ) -> list[WeatherPoint]:
        """Return the PAST window only (reanalysis cannot see the future).

        ``forecast_days`` is accepted for interface compatibility but contributes no
        future rows; use Open-Meteo for live forecasts.
        """
        now_utc = datetime.now(UTC)
        start = (now_utc - timedelta(days=max(past_days, 1))).date()
        points = await self.fetch_history(latitude, longitude, timezone, start, now_utc.date())
        return [p for p in points if p.timestamp.astimezone(UTC) <= now_utc]

    async def fetch_history(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        start_date,
        end_date,
    ) -> list[WeatherPoint]:
        key = (round(latitude, 4), round(longitude, 4), str(start_date), str(end_date), timezone)
        hit = self._cache.get(key)
        if hit and (time.monotonic() - hit[0]) < _CACHE_TTL_S:
            self.last_fetch_meta = {**self.last_fetch_meta, "cache": "hit"}
            return hit[1]

        params = {
            "parameters": _PARAMETERS,
            "community": "RE",
            "latitude": latitude,
            "longitude": longitude,
            "start": str(start_date).replace("-", ""),
            "end": str(end_date).replace("-", ""),
            "format": "JSON",
            "time-standard": "UTC",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_s, transport=self._transport
            ) as client:
                resp = await client.get(_ENDPOINT, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError as exc:
            logger.error(f"NASA POWER request failed: {exc}")
            raise NasaPowerError(f"NASA POWER request failed: {exc}") from exc

        points = self._parse(payload, timezone)
        self._cache[key] = (time.monotonic(), points)
        self.last_fetch_meta = {
            "provider": self.name,
            "data_kind": self.data_kind,
            "fetched_at": datetime.now(UTC).isoformat(),
            "hours": len(points),
            "coverage_end": points[-1].timestamp.isoformat() if points else None,
            "cache": "miss",
        }
        return points

    @staticmethod
    def _parse(payload: dict, timezone: str) -> list[WeatherPoint]:
        try:
            param = payload["properties"]["parameter"]
            ghi = param["ALLSKY_SFC_SW_DWN"]
        except (KeyError, TypeError) as exc:
            raise NasaPowerError(f"NASA POWER returned no hourly data: {exc}") from exc

        def series(name: str) -> dict:
            return param.get(name, {})

        dni, dhi = series("ALLSKY_SFC_SW_DNI"), series("ALLSKY_SFC_SW_DIFF")
        t2m, rh2m = series("T2M"), series("RH2M")
        ws10m, ps, cloud = series("WS10M"), series("PS"), series("CLOUD_AMT")
        tz = _resolve_tz(timezone)

        points: list[WeatherPoint] = []
        for key in sorted(ghi):
            g = _f(ghi.get(key))
            if g is None:  # -999 fill hour: skip honestly, never zero-fill
                continue
            ts_utc = datetime.strptime(key, "%Y%m%d%H").replace(tzinfo=UTC)
            pressure_kpa = _f(ps.get(key))
            points.append(
                WeatherPoint(
                    timestamp=ts_utc.astimezone(tz),  # explicit UTC -> site tz
                    ghi_w_m2=g,
                    dni_w_m2=_f(dni.get(key)) or 0.0,
                    dhi_w_m2=_f(dhi.get(key)) or 0.0,
                    temperature_c=_f(t2m.get(key)) or 0.0,
                    cloud_cover_percent=_f(cloud.get(key)) or 0.0,
                    wind_speed_mps=_f(ws10m.get(key)) or 0.0,
                    humidity_percent=_f(rh2m.get(key)) or 0.0,
                    pressure_hpa=(pressure_kpa * 10.0) if pressure_kpa is not None else 0.0,
                )
            )
        return points


def _f(value) -> float | None:
    """Float or None for NASA fill values / absent keys."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return None if v <= _FILL else v
