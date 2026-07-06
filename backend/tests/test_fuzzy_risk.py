"""Tests for the fuzzy risk agent."""

from app.agents.fuzzy_risk_agent import FuzzyRiskAgent

agent = FuzzyRiskAgent()


def test_within_band_is_low():
    r = agent.score(
        deviation_percent=3,
        allowed_dsm_threshold_percent=5,
        confidence_score=0.95,
        cloud_cover_percent=10,
    )
    assert r["fuzzy_risk_level"] == "LOW"
    assert 0 <= r["fuzzy_risk_score"] <= 100


def test_extreme_deviation_is_critical():
    r = agent.score(
        deviation_percent=30,
        allowed_dsm_threshold_percent=5,
        confidence_score=0.95,
        cloud_cover_percent=10,
    )
    assert r["fuzzy_risk_level"] == "CRITICAL"


def test_more_bad_factors_escalate_not_dilute():
    calm = agent.score(9, 5, 0.9, 10)["fuzzy_risk_score"]
    bad = agent.score(9, 5, 0.5, 90)["fuzzy_risk_score"]
    assert bad >= calm  # adding uncertainty + cloud must not lower risk


def test_score_bounded_and_monotonic():
    for dev in [0, 5, 8, 12, 20, 40]:
        s = agent.score(dev, 5, 0.7, 30)["fuzzy_risk_score"]
        assert 0 <= s <= 100
    r = agent.score(40, 5, 0.5, 80)
    assert set(r["memberships"].keys()) == {"breach", "uncertainty", "volatility"}
