"""Tests for the deterministic RiskAgent."""

from app.agents.risk_agent import RiskAgent

agent = RiskAgent()


def test_within_band_high_confidence_is_low():
    r = agent.score(
        deviation_percent=5.0, allowed_dsm_threshold_percent=10.0, confidence_score=0.95
    )
    assert r["risk_level"] == "LOW"


def test_large_breach_low_confidence_is_critical():
    r = agent.score(
        deviation_percent=80.0, allowed_dsm_threshold_percent=10.0, confidence_score=0.4
    )
    assert r["risk_level"] == "CRITICAL"


def test_score_bounded():
    r = agent.score(
        deviation_percent=500.0, allowed_dsm_threshold_percent=10.0, confidence_score=0.0
    )
    assert 0.0 <= r["risk_score"] <= 100.0


if __name__ == "__main__":
    test_within_band_high_confidence_is_low()
    test_large_breach_low_confidence_is_critical()
    test_score_bounded()
    print("All RiskAgent tests PASSED")
