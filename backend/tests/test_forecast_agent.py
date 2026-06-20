"""Tests for ForecastAgent."""
import sys
sys.path.insert(0, ".")
from app.agents.forecast_agent import ForecastAgent

agent = ForecastAgent()


def test_sunny_day_high_generation():
    r = agent.predict(solar_capacity_mw=50.0, irradiance_w_m2=950.0, cloud_cover_percent=10.0, temperature_c=28.0)
    assert r["predicted_generation_mw"] > 35.0


def test_cloudy_day_low_generation():
    r = agent.predict(solar_capacity_mw=50.0, irradiance_w_m2=400.0, cloud_cover_percent=80.0, temperature_c=30.0)
    assert r["predicted_generation_mw"] < 10.0


def test_zero_irradiance_gives_zero():
    r = agent.predict(solar_capacity_mw=50.0, irradiance_w_m2=0.0, cloud_cover_percent=0.0, temperature_c=25.0)
    assert r["predicted_generation_mw"] == 0.0


def test_never_exceeds_capacity():
    r = agent.predict(solar_capacity_mw=10.0, irradiance_w_m2=1500.0, cloud_cover_percent=0.0, temperature_c=20.0)
    assert r["predicted_generation_mw"] <= 10.0


def test_confidence_drops_with_clouds():
    r = agent.predict(solar_capacity_mw=50.0, irradiance_w_m2=800.0, cloud_cover_percent=80.0, temperature_c=30.0)
    assert r["confidence_score"] < 1.0


if __name__ == "__main__":
    test_sunny_day_high_generation()
    test_cloudy_day_low_generation()
    test_zero_irradiance_gives_zero()
    test_never_exceeds_capacity()
    test_confidence_drops_with_clouds()
    print("All ForecastAgent tests PASSED")
