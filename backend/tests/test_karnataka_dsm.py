"""Tests for the KERC/BESCOM Karnataka DSM engine and connector."""

from app.integrations.bescom import BescomConnector, FeedMode
from app.integrations.karnataka_dsm import KERC_SOLAR_BAND_PERCENT, KarnatakaDSM

dsm = KarnatakaDSM()


def test_default_band_is_kerc_five_percent():
    assert dsm.band_percent == 5.0
    assert KERC_SOLAR_BAND_PERCENT == 5.0


def test_within_band_no_charge():
    # 3% deviation on a 100 MW plant → within ±5% band → no charge
    r = dsm.settle(actual_mw=97.0, scheduled_mw=100.0, available_capacity_mw=100.0)
    assert r.within_band is True
    assert r.dsm_charge_inr == 0.0
    assert r.direction == "under-injection"


def test_breach_incurs_slab_charge():
    # 20% under-injection → beyond band → slab charges apply
    r = dsm.settle(actual_mw=80.0, scheduled_mw=100.0, available_capacity_mw=100.0)
    assert r.within_band is False
    assert r.dsm_charge_inr > 0
    assert len(r.slab_breakdown) >= 1


def test_over_injection_direction():
    r = dsm.settle(actual_mw=112.0, scheduled_mw=100.0, available_capacity_mw=100.0)
    assert r.direction == "over-injection"
    assert r.within_band is False


def test_bescom_connector_simulated():
    conn = BescomConnector()
    assert conn.mode == FeedMode.SIMULATED
    assert conn.is_live is False
    point = conn.actual_injection(nowcast_mw=42.0, timestamp="2026-06-27T12:00")
    assert point.actual_injection_mw == 42.0
    assert "simulated" in point.source
    assert conn.status()["is_live"] is False


if __name__ == "__main__":
    test_default_band_is_kerc_five_percent()
    test_within_band_no_charge()
    test_breach_incurs_slab_charge()
    test_over_injection_direction()
    test_bescom_connector_simulated()
    print("All Karnataka DSM tests PASSED")
