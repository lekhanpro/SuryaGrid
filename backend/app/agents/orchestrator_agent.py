"""OrchestratorAgent - sequences the agents for a single DSM interval.

Pipeline: ForecastAgent (pvlib) -> DSMClassifierAgent -> RiskAgent -> ExplanationAgent.
Timeline/summary orchestration over real provider data lives in ForecastService.
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
