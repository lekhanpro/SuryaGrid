"""Tests for DSMClassifierAgent."""
import sys
sys.path.insert(0, ".")
from app.agents.dsm_classifier_agent import DSMClassifierAgent

agent = DSMClassifierAgent()


def test_low_deviation_no_penalty():
    r = agent.classify(predicted_generation_mw=34.0, scheduled_generation_mw=35.0,
                       allowed_dsm_threshold_percent=10.0, penalty_rate_per_mw=15000.0)
    assert r["penalty_status"] == "NO_PENALTY"
    assert r["estimated_penalty_cost"] == 0.0


def test_high_deviation_penalty_risk():
    r = agent.classify(predicted_generation_mw=20.0, scheduled_generation_mw=35.0,
                       allowed_dsm_threshold_percent=10.0, penalty_rate_per_mw=15000.0)
    assert r["penalty_status"] == "PENALTY_RISK"
    assert r["estimated_penalty_cost"] > 0


def test_invalid_schedule():
    r = agent.classify(predicted_generation_mw=10.0, scheduled_generation_mw=0.0,
                       allowed_dsm_threshold_percent=10.0, penalty_rate_per_mw=15000.0)
    assert r["penalty_status"] == "INVALID_SCHEDULE"


def test_negative_schedule():
    r = agent.classify(predicted_generation_mw=10.0, scheduled_generation_mw=-5.0,
                       allowed_dsm_threshold_percent=10.0, penalty_rate_per_mw=15000.0)
    assert r["penalty_status"] == "INVALID_SCHEDULE"


def test_exact_threshold_no_penalty():
    # Deviation exactly at threshold should not trigger penalty
    r = agent.classify(predicted_generation_mw=9.0, scheduled_generation_mw=10.0,
                       allowed_dsm_threshold_percent=10.0, penalty_rate_per_mw=1000.0)
    assert r["penalty_status"] == "NO_PENALTY"


if __name__ == "__main__":
    test_low_deviation_no_penalty()
    test_high_deviation_penalty_risk()
    test_invalid_schedule()
    test_negative_schedule()
    test_exact_threshold_no_penalty()
    print("All DSMClassifier tests PASSED")
