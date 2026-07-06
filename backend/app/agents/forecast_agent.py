"""ForecastAgent - solar generation nowcasting: formula / ml / hybrid.

Modes (docs/ML_PIPELINE.md):
  - formula: deterministic pvlib physics (solar position -> POA transposition ->
    cell temperature -> PVWatts DC -> inverter AC). The baseline and fallback.
  - ml:      a trained scikit-learn model predicts irradiance from weather+site
    features; irradiance is converted to generation via the same pvlib pipeline
    (the Kaggle dataset provides irradiance, not plant generation).
  - hybrid:  the mean of the formula and ML generation.
  - auto:    hybrid when a valid model is available, else formula fallback.

All numbers are deterministic and reproducible; no LLM touches the math.
SOURCE: docs/FORMULA_SOURCES.md, docs/SOURCE_REGISTRY.md#src-pvlib-001
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from pvlib import inverter, irradiance, pvsystem, temperature
from pvlib.location import Location

from app.providers.base import WeatherPoint

FORMULA = "formula"
ML = "ml"
HYBRID = "hybrid"
AUTO = "auto"


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
    panel_efficiency: float = 0.18  # ML feature; FALLBACK_DEFAULT
    nearest_substation_distance_km: float = 0.0  # ML feature; 0 if unknown


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
    forecast_mode: str = FORMULA
    model_version: str | None = None
    source_used: str = "formula:pvlib"


class ForecastAgent:
    def forecast_timeline(
        self,
        site: SiteConfig,
        weather: list[WeatherPoint],
        mode: str = FORMULA,
        predictor=None,
    ) -> list[ForecastPoint]:
        """Compute the generation nowcast for a series of weather points.

        `mode` selects formula/ml/hybrid/auto. `predictor` is an ml.predict_model
        .ModelPredictor (dependency-injected); when absent or untrained, ml/hybrid
        fall back to formula and say so in `source_used`.
        """
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

        # Actual (cloud-affected) generation from real irradiance (formula path).
        dni, dhi = self._resolve_components(index, ghi, dni, dhi, solpos)
        poa_actual = self._poa(site, solpos, ghi, dni, dhi)
        gen_formula = self._ac_power_mw(site, poa_actual, temp_air, wind)

        # Day-ahead committed baseline from a clear-sky model.
        clearsky = loc.get_clearsky(index, model="ineichen")
        poa_clear = self._poa(site, solpos, clearsky["ghi"], clearsky["dni"], clearsky["dhi"])
        gen_clear = self._ac_power_mw(site, poa_clear, temp_air, wind)

        # Resolve effective mode and ML generation if requested/available.
        effective, ml_ok, model_version, model_type, r2 = self._resolve_mode(mode, predictor)
        gen_ml = None
        poa_ml = None
        if effective in (ML, HYBRID) and ml_ok:
            ghi_ml = self._predict_irradiance(site, weather, index, predictor)
            zeros = pd.Series(0.0, index=index)
            dni_ml, dhi_ml = self._resolve_components(index, ghi_ml, zeros, zeros, solpos)
            poa_ml = self._poa(site, solpos, ghi_ml, dni_ml, dhi_ml)
            gen_ml = self._ac_power_mw(site, poa_ml, temp_air, wind)

        points: list[ForecastPoint] = []
        for i, w in enumerate(weather):
            gen, poa, conf, source = self._combine(
                effective=effective,
                i=i,
                gen_formula=gen_formula,
                gen_ml=gen_ml,
                poa_actual=poa_actual,
                poa_ml=poa_ml,
                cloud=w.cloud_cover_percent,
                r2=r2,
                model_type=model_type,
            )
            points.append(
                ForecastPoint(
                    timestamp=w.timestamp,
                    ghi_w_m2=round(w.ghi_w_m2, 1),
                    poa_w_m2=round(float(poa), 1),
                    cloud_cover_percent=round(w.cloud_cover_percent, 1),
                    temperature_c=round(w.temperature_c, 1),
                    predicted_generation_mw=round(float(gen), 4),
                    clearsky_generation_mw=round(float(gen_clear.iloc[i]), 4),
                    confidence_score=conf,
                    forecast_mode=effective,
                    model_version=model_version if effective in (ML, HYBRID) else None,
                    source_used=source,
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
        mode: str = FORMULA,
        predictor=None,
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
        return self.forecast_timeline(site, [point], mode=mode, predictor=predictor)[0]

    # ---- mode resolution ------------------------------------------------
    @staticmethod
    def _resolve_mode(mode: str, predictor):
        """Return (effective_mode, ml_ok, model_version, model_type, r2)."""
        ml_ok = predictor is not None and predictor.is_available()
        model_version = None
        model_type = None
        r2 = 0.0
        if ml_ok:
            meta = predictor.metadata() or {}
            model_version = meta.get("model_version")
            model_type = meta.get("model_type")
            r2 = float((meta.get("metrics") or {}).get("r2") or 0.0)

        if mode == AUTO:
            return (HYBRID if ml_ok else FORMULA, ml_ok, model_version, model_type, r2)
        if mode in (ML, HYBRID) and not ml_ok:
            return (FORMULA, False, None, None, 0.0)  # graceful fallback
        return (mode, ml_ok, model_version, model_type, r2)

    def _predict_irradiance(self, site, weather, index, predictor) -> pd.Series:
        vals = []
        for w in weather:
            feats = self._features(site, w)
            out = predictor.predict_one(feats)
            vals.append(max(0.0, out["value"]) if out else w.ghi_w_m2)
        return pd.Series(vals, index=index)

    @staticmethod
    def _features(site: SiteConfig, w: WeatherPoint) -> dict:
        ts = pd.Timestamp(w.timestamp)
        return {
            "hour_of_day": ts.hour,
            "day_of_year": ts.dayofyear,
            "month": ts.month,
            "latitude": site.latitude,
            "longitude": site.longitude,
            "cloud_cover_percent": w.cloud_cover_percent,
            "temperature_c": w.temperature_c,
            "humidity_percent": w.humidity_percent,
            "wind_speed_mps": w.wind_speed_mps,
            "precipitation_probability_percent": w.precipitation_probability_percent,
            "pressure_hpa": w.pressure_hpa,
            "site_capacity_mw": site.capacity_mw,
            "panel_efficiency": site.panel_efficiency,
            "nearest_substation_distance_km": site.nearest_substation_distance_km,
        }

    def _combine(
        self, *, effective, i, gen_formula, gen_ml, poa_actual, poa_ml, cloud, r2, model_type
    ):
        f_gen = float(gen_formula.iloc[i])
        f_poa = float(poa_actual.iloc[i])
        if effective == ML and gen_ml is not None:
            gen = float(gen_ml.iloc[i])
            poa = float(poa_ml.iloc[i])
            conf = self._ml_confidence(cloud, poa, r2)
            source = f"ml:{model_type}"
        elif effective == HYBRID and gen_ml is not None:
            gen = 0.5 * (f_gen + float(gen_ml.iloc[i]))
            poa = 0.5 * (f_poa + float(poa_ml.iloc[i]))
            conf = round(
                0.5 * (self._confidence(cloud, poa) + self._ml_confidence(cloud, poa, r2)), 2
            )
            source = f"hybrid:formula+ml({model_type})"
        else:
            gen = f_gen
            poa = f_poa
            conf = self._confidence(cloud, poa)
            source = "formula:pvlib"
        return gen, poa, conf, source

    # ---- pvlib physics --------------------------------------------------
    def _resolve_components(self, index, ghi, dni, dhi, solpos):
        """Resolve beam (DNI) and diffuse (DHI); derive via Erbs when GHI-only."""
        has_beam = float(dni.abs().sum()) > 0.0
        has_diffuse = float(dhi.abs().sum()) > 0.0
        ghi_present = float(ghi.abs().sum()) > 0.0
        if not has_beam and not has_diffuse and ghi_present:
            decomposed = irradiance.erbs(ghi.clip(lower=0.0), solpos["zenith"], index)
            return (
                decomposed["dni"].fillna(0.0).clip(lower=0.0),
                decomposed["dhi"].fillna(0.0).clip(lower=0.0),
            )
        return dni, dhi

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

    @staticmethod
    def _ml_confidence(cloud_cover_percent: float, poa_w_m2: float, r2: float) -> float:
        # Anchor on model skill (R2), then reduce a little with cloud variability.
        base = 0.5 + 0.5 * max(0.0, min(1.0, r2))
        confidence = base - 0.15 * (cloud_cover_percent / 100.0)
        if poa_w_m2 < 50:
            confidence = max(confidence, 0.9)
        return round(max(0.4, min(0.99, confidence)), 2)
