"""Tests for the OrchestratorAgent single-interval pipeline."""

from datetime import datetime, timezone

from app.agents.forecast_agent import ForecastAgent, SiteConfig
from app.agents.orchestrator_agent import OrchestratorAgent

site = SiteConfig(latitude=28.6, longitude=77.2, timezone="Asia/Kolkata", capacity_mw=50.0)
forecast = ForecastAgent()
orch = OrchestratorAgent()


def _point(ghi, dni, dhi, cloud, temp=30.0):
    return forecast.predict_point(
        site=site, ghi_w_m2=ghi, dni_w_m2=dni, dhi_w_m2=dhi,
        temperature_c=temp, cloud_cover_percent=cloud,
        timestamp=datetime(2026, 6, 25, 6, 30, tzinfo=timezone.utc),
    )


def test_full_cycle_returns_all_fields():
    point = _point(800, 700, 100, 20)
    r = orch.evaluate(point, scheduled_generation_mw=30.0,
                      allowed_dsm_threshold_percent=10.0, penalty_rate_per_mwh=12000.0)
    for key in ["predicted_generation_mw", "energy_mwh", "deviation_percent",
                "penalty_status", "risk_level", "confidence_score", "explanation"]:
        assert key in r


def test_clearsky_default_schedule():
    point = _point(300, 100, 200, 85)  # cloudy -> below clear-sky baseline
    r = orch.run_for_site(site, point, scheduled_generation_mw=None,
                          allowed_dsm_threshold_percent=10.0, penalty_rate_per_mwh=12000.0)
    assert r["scheduled_generation_mw"] == point.clearsky_generation_mw


def test_no_penalty_when_on_schedule():
    point = _point(850, 750, 100, 10)
    r = orch.evaluate(point, scheduled_generation_mw=point.predicted_generation_mw,
                      allowed_dsm_threshold_percent=10.0, penalty_rate_per_mwh=12000.0)
    assert r["penalty_status"] == "NO_PENALTY"


if __name__ == "__main__":
    test_full_cycle_returns_all_fields()
    test_clearsky_default_schedule()
    test_no_penalty_when_on_schedule()
    print("All Orchestrator tests PASSED")
