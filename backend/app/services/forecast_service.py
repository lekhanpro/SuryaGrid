"""ForecastService - real end-to-end DSM nowcasting over live provider data."""

from __future__ import annotations

from app.agents.forecast_agent import ForecastAgent, SiteConfig
from app.agents.orchestrator_agent import OrchestratorAgent
from app.providers.base import WeatherProvider
from app.providers.open_meteo import OpenMeteoProvider

INTERVAL_HOURS = 1.0  # Open-Meteo hourly resolution


class ForecastService:
    def __init__(self, provider: WeatherProvider | None = None):
        self.provider: WeatherProvider = provider or OpenMeteoProvider()
        self.forecast_agent = ForecastAgent()
        self.orchestrator = OrchestratorAgent()

    async def build_timeline(
        self,
        site: SiteConfig,
        scheduled_generation_mw: float | None,
        allowed_dsm_threshold_percent: float,
        penalty_rate_per_mwh: float,
        forecast_days: int = 1,
        past_days: int = 0,
    ) -> dict:
        weather = await self.provider.fetch_forecast(
            latitude=site.latitude,
            longitude=site.longitude,
            timezone=site.timezone,
            forecast_days=forecast_days,
            past_days=past_days,
        )
        forecast_points = self.forecast_agent.forecast_timeline(site, weather)

        timeline = [
            self.orchestrator.run_for_site(
                site=site,
                forecast_point=fp,
                scheduled_generation_mw=scheduled_generation_mw,
                allowed_dsm_threshold_percent=allowed_dsm_threshold_percent,
                penalty_rate_per_mwh=penalty_rate_per_mwh,
                interval_hours=INTERVAL_HOURS,
            )
            for fp in forecast_points
        ]
        return {
            "provider": self.provider.name,
            "timeline": timeline,
            "summary": self.summarize(timeline),
        }

    @staticmethod
    def summarize(timeline: list[dict]) -> dict:
        if not timeline:
            return {
                "intervals": 0,
                "daylight_intervals": 0,
                "predicted_energy_mwh": 0.0,
                "scheduled_energy_mwh": 0.0,
                "peak_generation_mw": 0.0,
                "penalty_intervals": 0,
                "total_penalty_cost": 0.0,
                "max_deviation_percent": 0.0,
            }

        predicted_energy = sum(e["energy_mwh"] for e in timeline)
        scheduled_energy = sum(
            e["scheduled_generation_mw"] * INTERVAL_HOURS for e in timeline
        )
        peak = max(e["predicted_generation_mw"] for e in timeline)
        penalty_intervals = sum(1 for e in timeline if e["penalty_status"] == "PENALTY_RISK")
        total_penalty = sum(e["estimated_penalty_cost"] for e in timeline)
        max_dev = max(e["deviation_percent"] for e in timeline)
        daylight = sum(1 for e in timeline if e["predicted_generation_mw"] > 0.01)

        return {
            "intervals": len(timeline),
            "daylight_intervals": daylight,
            "predicted_energy_mwh": round(predicted_energy, 3),
            "scheduled_energy_mwh": round(scheduled_energy, 3),
            "peak_generation_mw": round(peak, 3),
            "penalty_intervals": penalty_intervals,
            "total_penalty_cost": round(total_penalty, 2),
            "max_deviation_percent": round(max_dev, 2),
        }
