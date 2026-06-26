"""Tests for the pvlib-based ForecastAgent."""

from datetime import UTC, datetime

from app.agents.forecast_agent import ForecastAgent, SiteConfig

agent = ForecastAgent()
SITE = SiteConfig(latitude=28.6, longitude=77.2, timezone="Asia/Kolkata", capacity_mw=50.0)


def test_clear_noon_generates_power():
    point = agent.predict_point(
        site=SITE,
        ghi_w_m2=900.0,
        dni_w_m2=750.0,
        dhi_w_m2=120.0,
        temperature_c=30.0,
        cloud_cover_percent=5.0,
        timestamp=datetime(2026, 6, 25, 6, 30, tzinfo=UTC),  # ~noon IST
        wind_speed_mps=2.0,
    )
    assert point.predicted_generation_mw > 10.0
    assert point.predicted_generation_mw <= SITE.capacity_mw
    assert point.confidence_score >= 0.9


def test_night_generates_zero():
    point = agent.predict_point(
        site=SITE,
        ghi_w_m2=0.0,
        dni_w_m2=0.0,
        dhi_w_m2=0.0,
        temperature_c=22.0,
        cloud_cover_percent=0.0,
        timestamp=datetime(2026, 6, 25, 20, 0, tzinfo=UTC),
    )
    assert point.predicted_generation_mw == 0.0


def test_prediction_never_exceeds_capacity():
    point = agent.predict_point(
        site=SITE,
        ghi_w_m2=1400.0,
        dni_w_m2=1000.0,
        dhi_w_m2=200.0,
        temperature_c=25.0,
        cloud_cover_percent=0.0,
        timestamp=datetime(2026, 6, 25, 6, 30, tzinfo=UTC),
    )
    assert point.predicted_generation_mw <= SITE.capacity_mw


def test_cloud_lowers_confidence():
    clear = agent.predict_point(
        site=SITE,
        ghi_w_m2=800,
        dni_w_m2=700,
        dhi_w_m2=100,
        temperature_c=30,
        cloud_cover_percent=10,
        timestamp=datetime(2026, 6, 25, 6, 30, tzinfo=UTC),
    )
    cloudy = agent.predict_point(
        site=SITE,
        ghi_w_m2=400,
        dni_w_m2=200,
        dhi_w_m2=200,
        temperature_c=30,
        cloud_cover_percent=90,
        timestamp=datetime(2026, 6, 25, 6, 30, tzinfo=UTC),
    )
    assert cloudy.confidence_score < clear.confidence_score


if __name__ == "__main__":
    test_clear_noon_generates_power()
    test_night_generates_zero()
    test_prediction_never_exceeds_capacity()
    test_cloud_lowers_confidence()
    print("All ForecastAgent tests PASSED")
