"""OrchestratorAgent - sequences the agents for a single DSM interval, and
coordinates the full end-to-end site prediction run.

Per-interval pipeline: ForecastAgent (pvlib/ml) -> DSM -> RiskAgent -> ExplanationAgent.
Full run (run_full): coverage/nearest-substation -> live weather -> forecast
(formula/ml/hybrid) -> advanced DSM -> fuzzy risk -> explanation (+sources) ->
persist -> full response. See docs/AGENT_WORKFLOWS.md.
"""

from __future__ import annotations

from app.agents.dsm_classifier_agent import DSMClassifierAgent
from app.agents.explanation_agent import ExplanationAgent
from app.agents.forecast_agent import ForecastAgent, ForecastPoint, SiteConfig
from app.agents.risk_agent import RiskAgent


class OrchestratorAgent:
    def __init__(self):
        self.forecast = ForecastAgent()
        self.dsm = DSMClassifierAgent()
        self.risk = RiskAgent()
        self.explanation = ExplanationAgent()

    def evaluate(
        self,
        forecast_point: ForecastPoint,
        scheduled_generation_mw: float,
        allowed_dsm_threshold_percent: float,
        penalty_rate_per_mwh: float,
        interval_hours: float = 1.0,
    ) -> dict:
        """Run DSM + risk + explanation for one already-computed forecast point."""
        predicted_mw = forecast_point.predicted_generation_mw

        dsm = self.dsm.classify(
            predicted_generation_mw=predicted_mw,
            scheduled_generation_mw=scheduled_generation_mw,
            allowed_dsm_threshold_percent=allowed_dsm_threshold_percent,
            penalty_rate_per_mwh=penalty_rate_per_mwh,
            interval_hours=interval_hours,
        )
        risk = self.risk.score(
            deviation_percent=dsm["deviation_percent"],
            allowed_dsm_threshold_percent=allowed_dsm_threshold_percent,
            confidence_score=forecast_point.confidence_score,
        )
        explanation = self.explanation.explain(
            predicted_generation_mw=predicted_mw,
            scheduled_generation_mw=scheduled_generation_mw,
            deviation_percent=dsm["deviation_percent"],
            penalty_status=dsm["penalty_status"],
            risk_level=risk["risk_level"],
            cloud_cover_percent=forecast_point.cloud_cover_percent,
            ghi_w_m2=forecast_point.ghi_w_m2,
            estimated_penalty_cost=dsm["estimated_penalty_cost"],
        )

        return {
            "timestamp": forecast_point.timestamp.isoformat(),
            "ghi_w_m2": forecast_point.ghi_w_m2,
            "poa_w_m2": forecast_point.poa_w_m2,
            "cloud_cover_percent": forecast_point.cloud_cover_percent,
            "temperature_c": forecast_point.temperature_c,
            "predicted_generation_mw": predicted_mw,
            "energy_mwh": round(predicted_mw * interval_hours, 4),
            "scheduled_generation_mw": round(scheduled_generation_mw, 4),
            "deviation_mw": dsm["deviation_mw"],
            "deviation_percent": dsm["deviation_percent"],
            "allowed_dsm_threshold_percent": allowed_dsm_threshold_percent,
            "penalty_status": dsm["penalty_status"],
            "estimated_penalty_cost": dsm["estimated_penalty_cost"],
            "risk_score": risk["risk_score"],
            "risk_level": risk["risk_level"],
            "confidence_score": forecast_point.confidence_score,
            "explanation": explanation,
        }

    def run_for_site(
        self,
        site: SiteConfig,
        forecast_point: ForecastPoint,
        scheduled_generation_mw: float | None,
        allowed_dsm_threshold_percent: float,
        penalty_rate_per_mwh: float,
        interval_hours: float = 1.0,
    ) -> dict:
        """Evaluate one point, defaulting the schedule to the clear-sky baseline."""
        if scheduled_generation_mw is None:
            scheduled_generation_mw = forecast_point.clearsky_generation_mw
        return self.evaluate(
            forecast_point=forecast_point,
            scheduled_generation_mw=scheduled_generation_mw,
            allowed_dsm_threshold_percent=allowed_dsm_threshold_percent,
            penalty_rate_per_mwh=penalty_rate_per_mwh,
            interval_hours=interval_hours,
        )

    async def run_full(
        self,
        db,
        *,
        site_id: str,
        latitude: float = 12.97,
        longitude: float = 77.59,
        timezone: str = "Asia/Kolkata",
        capacity_mw: float = 50.0,
        tilt: float = 20.0,
        azimuth: float = 180.0,
        panel_efficiency: float = 0.18,
        scheduled_generation_mw: float | None = None,
        mode: str = "auto",
        region: str | None = None,
        regulator: str | None = None,
        rule_profile_id: str | None = None,
    ) -> dict:
        """End-to-end site prediction: weather -> forecast -> DSM -> fuzzy risk -> persist."""
        from datetime import UTC, datetime

        from app.agents.dsm_engine_agent import DSMEngineAgent
        from app.agents.fuzzy_risk_agent import FuzzyRiskAgent
        from app.agents.live_weather_agent import LiveWeatherAgent
        from app.agents.persistence_agent import PersistenceAgent
        from app.data_sources import source_registry as sr
        from app.db import repository
        from app.dsm.dsm_sources import source_for_regulator
        from app.ml.predict_model import predictor
        from app.providers.base import WeatherPoint
        from app.services.site_resolver import resolve_site

        resolved = await resolve_site(
            db, site_id, latitude, longitude, timezone, capacity_mw, tilt, azimuth
        )
        cfg: SiteConfig = resolved.config
        cfg.panel_efficiency = panel_efficiency

        # Nearest substation (feeds ML feature + response)
        sub, distance = await repository.nearest_substation(db, cfg.latitude, cfg.longitude)
        nearest = None
        if sub is not None:
            cfg.nearest_substation_distance_km = round(distance, 3)
            nearest = {
                "name": sub.name,
                "distance_km": round(distance, 3),
                "source": sub.source_name,
            }

        # Live weather (current conditions; synthetic fallback is reported)
        live = LiveWeatherAgent()
        latest = await live.latest(cfg.latitude, cfg.longitude, cfg.timezone)
        weather_mode = latest.get("mode", "real")
        wp = WeatherPoint(
            timestamp=datetime.now(UTC),
            ghi_w_m2=float(latest.get("ghi_w_m2", 0.0)),
            dni_w_m2=float(latest.get("dni_w_m2", 0.0)),
            dhi_w_m2=float(latest.get("dhi_w_m2", 0.0)),
            temperature_c=float(latest.get("temperature_c", 25.0)),
            cloud_cover_percent=float(latest.get("cloud_cover_percent", 0.0)),
            wind_speed_mps=float(latest.get("wind_speed_mps", 2.0)),
            humidity_percent=float(latest.get("humidity_percent", 0.0)),
            pressure_hpa=float(latest.get("pressure_hpa", 0.0)),
            precipitation_probability_percent=float(
                latest.get("precipitation_probability_percent", 0.0)
            ),
        )

        # Forecast (formula/ml/hybrid/auto)
        fp = self.forecast.forecast_timeline(cfg, [wp], mode=mode, predictor=predictor)[0]
        predicted = fp.predicted_generation_mw
        scheduled = (
            scheduled_generation_mw
            if scheduled_generation_mw is not None
            else fp.clearsky_generation_mw
        )

        # Advanced DSM
        dsm_agent = DSMEngineAgent()
        profile = await dsm_agent.resolve_profile(db, rule_profile_id, region, regulator)
        dsm_res = dsm_agent.evaluate(profile, scheduled, predicted, cfg.capacity_mw, 1.0)

        # Fuzzy risk
        fuzzy = FuzzyRiskAgent().score(
            deviation_percent=dsm_res["deviation_percent"],
            allowed_dsm_threshold_percent=profile.tolerance_percent,
            confidence_score=fp.confidence_score,
            cloud_cover_percent=wp.cloud_cover_percent,
        )

        explanation = self.explanation.explain(
            predicted_generation_mw=predicted,
            scheduled_generation_mw=scheduled,
            deviation_percent=dsm_res["deviation_percent"],
            penalty_status=dsm_res["penalty_status"],
            risk_level=fuzzy["fuzzy_risk_level"],
            cloud_cover_percent=wp.cloud_cover_percent,
            ghi_w_m2=wp.ghi_w_m2,
            estimated_penalty_cost=dsm_res["estimated_dsm_charge"],
        )

        # Sources
        data_sources = ["synthetic_weather"] if weather_mode == "synthetic" else ["live_weather"]
        src_ids = ["SRC-PVLIB-001"]
        if weather_mode != "synthetic":
            src_ids.append("SRC-OPENMETEO-001")
        if fp.forecast_mode in ("ml", "hybrid"):
            src_ids.append("SRC-KAGGLE-SOLAR-001")
            data_sources.append("kaggle")
        dsm_src = source_for_regulator(profile.regulator)
        if dsm_src:
            src_ids.append(dsm_src)
        # de-dup preserving order
        seen: set[str] = set()
        src_ids = [s for s in src_ids if not (s in seen or seen.add(s))]

        # Persist
        persist = PersistenceAgent()
        timestamp = wp.timestamp.isoformat()
        await persist.save_forecast_point(
            db,
            resolved.site_uuid,
            {
                "timestamp": timestamp,
                "predicted_generation_mw": predicted,
                "scheduled_generation_mw": scheduled,
                "confidence_score": fp.confidence_score,
            },
        )
        if resolved.site_uuid is not None:
            await dsm_agent.persist(db, resolved.site_uuid, profile, dsm_res)

        return {
            "site_id": site_id,
            "timestamp": timestamp,
            "forecast_mode": fp.forecast_mode,
            "model_version": fp.model_version,
            "source_used": fp.source_used,
            "data_sources": data_sources,
            "weather_mode": weather_mode,
            "ghi_w_m2": wp.ghi_w_m2,
            "cloud_cover_percent": wp.cloud_cover_percent,
            "temperature_c": wp.temperature_c,
            "capacity_mw": cfg.capacity_mw,
            "predicted_generation_mw": round(predicted, 4),
            "scheduled_generation_mw": round(scheduled, 4),
            "deviation_mw": dsm_res["deviation_mw"],
            "deviation_percent": dsm_res["deviation_percent"],
            "deviation_direction": dsm_res["deviation_direction"],
            "dsm_band": dsm_res["dsm_band"],
            "penalty_status": dsm_res["penalty_status"],
            "charge_rate": dsm_res["charge_rate"],
            "estimated_dsm_charge": dsm_res["estimated_dsm_charge"],
            "dsm_profile": profile.name,
            "rule_source": dsm_res["rule_source"],
            "fuzzy_risk_score": fuzzy["fuzzy_risk_score"],
            "fuzzy_risk_level": fuzzy["fuzzy_risk_level"],
            "confidence_score": fp.confidence_score,
            "nearest_substation": nearest,
            "sources": sr.cite(*src_ids),
            "explanation": explanation,
            "persisted": resolved.site_uuid is not None,
        }
