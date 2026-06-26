"""Tests for the Erbs GHI->DNI/DHI decomposition fallback in ForecastAgent.

Real providers (Open-Meteo) return measured DNI/DHI; a GHI-only source should
still yield an accurate physics forecast via Erbs decomposition rather than
collapsing to near-zero plane-of-array irradiance.
"""

from datetime import UTC, datetime

from app.agents.forecast_agent import ForecastAgent, SiteConfig

agent = ForecastAgent()
SITE = SiteConfig(latitude=28.6, longitude=77.2, timezone="Asia/Kolkata", capacity_mw=50.0)
NOON_UTC = datetime(2026, 6, 25, 6, 30, tzinfo=UTC)  # ~solar noon IST


def test_ghi_only_uses_erbs_fallback():
    # GHI only (no beam/diffuse): without Erbs this would be near-zero.
    point = agent.predict_point(
        site=SITE,
        ghi_w_m2=850.0,
        dni_w_m2=0.0,
        dhi_w_m2=0.0,
        temperature_c=30.0,
        cloud_cover_percent=10.0,
        timestamp=NOON_UTC,
    )
    assert point.predicted_generation_mw > 10.0
    assert point.poa_w_m2 > 300.0


def test_explicit_components_are_respected():
    # When DNI/DHI are supplied, they are used directly (no decomposition).
    point = agent.predict_point(
        site=SITE,
        ghi_w_m2=850.0,
        dni_w_m2=780.0,
        dhi_w_m2=110.0,
        temperature_c=30.0,
        cloud_cover_percent=10.0,
        timestamp=NOON_UTC,
    )
    assert 10.0 < point.predicted_generation_mw <= SITE.capacity_mw


def test_ghi_only_night_stays_zero():
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


def test_ghi_only_never_exceeds_capacity():
    point = agent.predict_point(
        site=SITE,
        ghi_w_m2=1300.0,
        dni_w_m2=0.0,
        dhi_w_m2=0.0,
        temperature_c=25.0,
        cloud_cover_percent=0.0,
        timestamp=NOON_UTC,
    )
    assert point.predicted_generation_mw <= SITE.capacity_mw


if __name__ == "__main__":
    test_ghi_only_uses_erbs_fallback()
    test_explicit_components_are_respected()
    test_ghi_only_night_stays_zero()
    test_ghi_only_never_exceeds_capacity()
    print("All Erbs fallback tests PASSED")
