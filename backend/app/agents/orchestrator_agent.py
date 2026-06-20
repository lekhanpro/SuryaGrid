"""OrchestratorAgent - coordinates all Phase 1 agents into one prediction cycle."""

from app.agents.forecast_agent import ForecastAgent
from app.agents.dsm_classifier_agent import DSMClassifierAgent
from app.agents.fuzzy_risk_agent import FuzzyRiskAgent
from app.agents.explanation_agent import ExplanationAgent


class OrchestratorAgent:
    def __init__(self):
        self.forecast = ForecastAgent()
        self.dsm = DSMClassifierAgent()
        self.fuzzy = FuzzyRiskAgent()
        self.explanation = ExplanationAgent()

    def run_prediction_cycle(
        self,
        solar_capacity_mw: float,
        irradiance_w_m2: float,
        cloud_cover_percent: float,
        temperature_c: float,
        scheduled_generation_mw: float,
        allowed_dsm_threshold_percent: float = 10.0,
        penalty_rate_per_mw: float = 15000.0,
    ) -> dict:
        # Step 1: Forecast
        forecast_result = self.forecast.predict(
            solar_capacity_mw=solar_capacity_mw,
            irradiance_w_m2=irradiance_w_m2,
            cloud_cover_percent=cloud_cover_percent,
            temperature_c=temperature_c,
        )

        predicted_mw = forecast_result["predicted_generation_mw"]
        confidence = forecast_result["confidence_score"]

        # Step 2: DSM classification
        dsm_result = self.dsm.classify(
            predicted_generation_mw=predicted_mw,
            scheduled_generation_mw=scheduled_generation_mw,
            allowed_dsm_threshold_percent=allowed_dsm_threshold_percent,
            penalty_rate_per_mw=penalty_rate_per_mw,
        )

        # Step 3: Fuzzy risk
        fuzzy_result = self.fuzzy.score(
            deviation_percent=dsm_result["deviation_percent"],
            cloud_cover_percent=cloud_cover_percent,
            irradiance_w_m2=irradiance_w_m2,
            confidence_score=confidence,
        )

        # Step 4: Explanation
        explanation_text = self.explanation.explain(
            predicted_generation_mw=predicted_mw,
            scheduled_generation_mw=scheduled_generation_mw,
            deviation_percent=dsm_result["deviation_percent"],
            penalty_status=dsm_result["penalty_status"],
            fuzzy_risk_level=fuzzy_result["fuzzy_risk_level"],
            cloud_cover_percent=cloud_cover_percent,
            irradiance_w_m2=irradiance_w_m2,
        )

        return {
            "predicted_generation_mw": predicted_mw,
            "scheduled_generation_mw": scheduled_generation_mw,
            "deviation_mw": dsm_result["deviation_mw"],
            "deviation_percent": dsm_result["deviation_percent"],
            "allowed_dsm_threshold_percent": allowed_dsm_threshold_percent,
            "penalty_status": dsm_result["penalty_status"],
            "estimated_penalty_cost": dsm_result["estimated_penalty_cost"],
            "fuzzy_risk_score": fuzzy_result["fuzzy_risk_score"],
            "fuzzy_risk_level": fuzzy_result["fuzzy_risk_level"],
            "confidence_score": confidence,
            "explanation": explanation_text,
        }
