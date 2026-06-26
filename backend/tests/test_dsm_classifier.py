"""Tests for DSMClassifierAgent."""

from app.agents.dsm_classifier_agent import DSMClassifierAgent

agent = DSMClassifierAgent()


def test_low_deviation_no_penalty():
    r = agent.classify(34.0, 35.0, allowed_dsm_threshold_percent=10.0, penalty_rate_per_mwh=12000.0)
    assert r["penalty_status"] == "NO_PENALTY"
    assert r["estimated_penalty_cost"] == 0.0


def test_high_deviation_penalty_risk():
    r = agent.classify(20.0, 35.0, allowed_dsm_threshold_percent=10.0, penalty_rate_per_mwh=12000.0)
    assert r["penalty_status"] == "PENALTY_RISK"
    assert r["estimated_penalty_cost"] > 0


def test_invalid_schedule():
    r = agent.classify(10.0, 0.0, allowed_dsm_threshold_percent=10.0, penalty_rate_per_mwh=12000.0)
    assert r["penalty_status"] == "INVALID_SCHEDULE"


def test_negative_schedule():
    r = agent.classify(10.0, -5.0, allowed_dsm_threshold_percent=10.0, penalty_rate_per_mwh=12000.0)
    assert r["penalty_status"] == "INVALID_SCHEDULE"


def test_penalty_only_charges_excess_over_band():
    # 30% deviation, 10% allowed -> only the 20% over the band is chargeable
    r = agent.classify(7.0, 10.0, allowed_dsm_threshold_percent=10.0, penalty_rate_per_mwh=1000.0)
    assert r["penalty_status"] == "PENALTY_RISK"
    # deviation 3 MW, allowed 1 MW -> chargeable 2 MW * 1000 = 2000
    assert r["estimated_penalty_cost"] == 2000.0


if __name__ == "__main__":
    test_low_deviation_no_penalty()
    test_high_deviation_penalty_risk()
    test_invalid_schedule()
    test_negative_schedule()
    test_penalty_only_charges_excess_over_band()
    print("All DSMClassifier tests PASSED")
