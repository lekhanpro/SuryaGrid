"""Tests for OrchestratorAgent - full prediction cycle."""
import sys
sys.path.insert(0, ".")
from app.agents.orchestrator_agent import OrchestratorAgent

agent = OrchestratorAgent()

REQUIRED_FIELDS = [
    "predicted_generation_mw", "scheduled_generation_mw", "deviation_mw",
    "deviation_percent", "allowed_dsm_threshold_percent", "penalty_status",
    "estimated_penalty_cost", "fuzzy_risk_score", "fuzzy_risk_level",
    "confidence_score", "explanation",
]


def test_full_cycle_returns_all_fields():
    r = agent.run_prediction_cycle(
        solar_capacity_mw=50.0, irradiance_w_m2=750.0, cloud_cover_percent=40.0,
        temperature_c=32.0, scheduled_generation_mw=35.0,
    )
    for field in REQUIRED_FIELDS:
        assert field in r, f"Missing field: {field}"


def test_penalty_scenario():
    r = agent.run_prediction_cycle(
        solar_capacity_mw=50.0, irradiance_w_m2=300.0, cloud_cover_percent=70.0,
        temperature_c=35.0, scheduled_generation_mw=35.0,
    )
    assert r["penalty_status"] == "PENALTY_RISK"
    assert r["estimated_penalty_cost"] > 0


def test_no_penalty_scenario():
    r = agent.run_prediction_cycle(
        solar_capacity_mw=50.0, irradiance_w_m2=950.0, cloud_cover_percent=5.0,
        temperature_c=25.0, scheduled_generation_mw=35.0,
    )
    # With 950 irradiance and low cloud, prediction should be near capacity
    assert r["penalty_status"] == "NO_PENALTY" or r["predicted_generation_mw"] > 30


if __name__ == "__main__":
    test_full_cycle_returns_all_fields()
    test_penalty_scenario()
    test_no_penalty_scenario()
    print("All Orchestrator tests PASSED")
