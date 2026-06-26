"""ForecastAgent - physics-based solar generation nowcasting using pvlib.

Given real irradiance components (GHI/DNI/DHI) plus temperature and wind for a
site, this computes plane-of-array irradiance, cell temperature and AC power with
validated PV models. It also derives the day-ahead "committed" schedule from a
clear-sky model, which is the realistic baseline a generator declares to the grid.

All numbers are deterministic and reproducible; no LLM touches the math.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from pvlib import inverter, irradiance, pvsystem, temperature
from pvlib.location import Location

from app.providers.base import WeatherPoint


@dataclass(slots=True)
class SiteConfig:
    latitude: float
    longitude: float
    timezone: str
    capacity_mw: float
    tilt: float = 20.0
    azimuth: float = 180.0  # 180 = facing south (northern hemisphere)
    altitude: float = 0.0
    gamma_pdc: float = -0.0035  # temperature coefficient (-0.35 %/degC)
    inverter_efficiency: float = 0.96


@dataclass(slots=True)
class ForecastPoint:
    timestamp: object
    ghi_w_m2: float
    poa_w_m2: float
    cloud_cover_percent: float
    temperature_c: float
    predicted_generation_mw: float
    clearsky_generation_mw: float  # day-ahead committed baseline
    confidence_score: float


class ForecastAgent:
    def forecast_timeline(
        self, site: SiteConfig, weather: list[WeatherPoint]
    ) -> list[ForecastPoint]:
        """Compute the generation nowcast for a full series of weather points."""
        if not weather:
            return []

        loc = Location(site.latitude, site.longitude, tz=site.timezone, altitude=site.altitude)
        index = pd.DatetimeIndex([w.timestamp for w in weather])

        ghi = pd.Series([w.ghi_w_m2 for w in weather], index=index)
        dni = pd.Series([w.dni_w_m2 for w in weather], index=index)
        dhi = pd.Series([w.dhi_w_m2 for w in weather], index=index)
        temp_air = pd.Series([w.temperature_c for w in weather], index=index)
        wind = pd.Series([w.wind_speed_mps for w in weather], index=index)

        solpos = loc.get_solarposition(index)

        # Actual (cloud-affected) generation from real irradiance
        poa_actual = self._poa(site, solpos, ghi, dni, dhi)
        gen_actual = self._ac_power_mw(site, poa_actual, temp_air, wind)

        # Day-ahead committed baseline from a clear-sky model
        clearsky = loc.get_clearsky(index, model="ineichen")
        poa_clear = self._poa(site, solpos, clearsky["ghi"], clearsky["dni"], clearsky["dhi"])
        gen_clear = self._ac_power_mw(site, poa_clear, temp_air, wind)

        points: list[ForecastPoint] = []
        for i, w in enumerate(weather):
            points.append(
                ForecastPoint(
                    timestamp=w.timestamp,
                    ghi_w_m2=round(w.ghi_w_m2, 1),
                    poa_w_m2=round(float(poa_actual.iloc[i]), 1),
                    cloud_cover_percent=round(w.cloud_cover_percent, 1),
                    temperature_c=round(w.temperature_c, 1),
                    predicted_generation_mw=round(float(gen_actual.iloc[i]), 4),
                    clearsky_generation_mw=round(float(gen_clear.iloc[i]), 4),
                    confidence_score=self._confidence(
                        w.cloud_cover_percent, float(poa_actual.iloc[i])
                    ),
                )
            )
        return points

    def predict_point(
        self,
        site: SiteConfig,
        ghi_w_m2: float,
        dni_w_m2: float,
        dhi_w_m2: float,
        temperature_c: float,
        cloud_cover_percent: float,
        timestamp,
        wind_speed_mps: float = 2.0,
    ) -> ForecastPoint:
        """Single-timestep convenience wrapper around forecast_timeline."""
        point = WeatherPoint(
            timestamp=timestamp,
            ghi_w_m2=ghi_w_m2,
            dni_w_m2=dni_w_m2,
            dhi_w_m2=dhi_w_m2,
            temperature_c=temperature_c,
            cloud_cover_percent=cloud_cover_percent,
            wind_speed_mps=wind_speed_mps,
        )
        return self.forecast_timeline(site, [point])[0]

    def _poa(self, site: SiteConfig, solpos, ghi, dni, dhi):
        total = irradiance.get_total_irradiance(
            surface_tilt=site.tilt,
            surface_azimuth=site.azimuth,
            solar_zenith=solpos["apparent_zenith"],
            solar_azimuth=solpos["azimuth"],
            dni=dni,
            ghi=ghi,
            dhi=dhi,
        )
        return total["poa_global"].fillna(0.0).clip(lower=0.0)

    def _ac_power_mw(self, site: SiteConfig, poa_global, temp_air, wind):
        pdc0 = site.capacity_mw * 1_000_000.0  # W, treat capacity as nameplate
        cell_temp = temperature.faiman(poa_global, temp_air, wind)
        pdc = pvsystem.pvwatts_dc(poa_global, cell_temp, pdc0, site.gamma_pdc)
        pac = inverter.pvwatts(pdc, pdc0, eta_inv_nom=site.inverter_efficiency)
        mw = (pac / 1_000_000.0).fillna(0.0).clip(lower=0.0, upper=site.capacity_mw)
        return mw

    @staticmethod
    def _confidence(cloud_cover_percent: float, poa_w_m2: float) -> float:
        # Forecast is most certain in clear conditions; cloud cover adds variance.
        confidence = 1.0 - 0.35 * (cloud_cover_percent / 100.0)
        if poa_w_m2 < 50:  # near-dark hours: little at stake, treat as confident
            confidence = max(confidence, 0.9)
        return round(max(0.4, min(0.99, confidence)), 2)
