"""Tests for FuzzyRiskAgent."""
import sys
sys.path.insert(0, ".")
from app.agents.fuzzy_risk_agent import FuzzyRiskAgent

agent = FuzzyRiskAgent()


def test_low_risk():
    r = agent.score(deviation_percent=5.0, cloud_cover_percent=20.0, irradiance_w_m2=800.0, confidence_score=0.9)
    assert r["fuzzy_risk_level"] == "LOW"
    assert r["fuzzy_risk_score"] < 25


def test_medium_risk():
    r = agent.score(deviation_percent=40.0, cloud_cover_percent=50.0, irradiance_w_m2=500.0, confidence_score=0.8)
    assert r["fuzzy_risk_level"] == "MEDIUM"


def test_high_risk():
    r = agent.score(deviation_percent=80.0, cloud_cover_percent=70.0, irradiance_w_m2=250.0, confidence_score=0.7)
    assert r["fuzzy_risk_level"] == "HIGH"


def test_critical_risk():
    r = agent.score(deviation_percent=90.0, cloud_cover_percent=90.0, irradiance_w_m2=100.0, confidence_score=0.4)
    assert r["fuzzy_risk_level"] == "CRITICAL"


def test_score_clamped_0_100():
    r = agent.score(deviation_percent=200.0, cloud_cover_percent=100.0, irradiance_w_m2=0.0, confidence_score=0.1)
    assert 0 <= r["fuzzy_risk_score"] <= 100

    r2 = agent.score(deviation_percent=0.0, cloud_cover_percent=0.0, irradiance_w_m2=1000.0, confidence_score=1.0)
    assert 0 <= r2["fuzzy_risk_score"] <= 100


if __name__ == "__main__":
    test_low_risk()
    test_medium_risk()
    test_high_risk()
    test_critical_risk()
    test_score_clamped_0_100()
    print("All FuzzyRisk tests PASSED")
