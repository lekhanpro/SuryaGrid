"""Phase 1 - NASA POWER provider + gated KERC DSM 2026 engine.

NASA POWER (offline, MockTransport fixtures):
  * parses hourly UTC keys into site-timezone WeatherPoints
  * converts pressure kPa -> hPa; skips -999 fill hours (never zero-fills GHI)
  * never emits future rows from fetch_forecast (reanalysis is not a forecast)
  * caches responses (second call does not hit the network)
  * carries data_kind="reanalysis_nrt" so callers can label the series honestly

KERC DSM 2026 (machinery gated on a verified official order):
  * ships blocked: no order registered -> NEEDS_OFFICIAL_SOURCE, no rupees
  * an unverified order never activates the engine
  * with a clearly-labelled TEST FIXTURE order: cumulative slabs, tolerance,
    annual cap and effective-date selection are exact
  * clear_orders() rolls the engine back to blocked

Run: python -m pytest tests/test_phase1_providers_kerc.py -q
"""

import asyncio
import json
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest

from app.dsm import kerc_dsm_2026 as kerc
from app.providers.nasa_power import NasaPowerProvider

# --------------------------------------------------------------------------- #
# NASA POWER fixtures
# --------------------------------------------------------------------------- #


def _nasa_payload(hours: list[tuple[str, float]]) -> dict:
    """Minimal NASA POWER hourly payload. hours = [(YYYYMMDDHH, ghi), ...]."""
    keys = [h[0] for h in hours]
    return {
        "properties": {
            "parameter": {
                "ALLSKY_SFC_SW_DWN": {k: g for k, g in hours},
                "ALLSKY_SFC_SW_DNI": {k: 500.0 for k in keys},
                "ALLSKY_SFC_SW_DIFF": {k: 120.0 for k in keys},
                "T2M": {k: 27.5 for k in keys},
                "RH2M": {k: 60.0 for k in keys},
                "WS10M": {k: 3.2 for k in keys},
                "PS": {k: 91.0 for k in keys},  # kPa
                "CLOUD_AMT": {k: 40.0 for k in keys},
            }
        }
    }


def _provider_with(payload: dict) -> tuple[NasaPowerProvider, dict]:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=payload)

    return NasaPowerProvider(transport=httpx.MockTransport(handler)), calls


def test_nasa_power_parses_utc_keys_to_site_timezone_and_units():
    payload = _nasa_payload([("2026010106", 450.0), ("2026010107", 520.0)])
    provider, _ = _provider_with(payload)
    pts = asyncio.run(
        provider.fetch_history(12.97, 77.59, "Asia/Kolkata", date(2026, 1, 1), date(2026, 1, 1))
    )
    assert len(pts) == 2
    # 2026-01-01T06:00 UTC == 11:30 IST
    assert pts[0].timestamp.isoformat() == "2026-01-01T11:30:00+05:30"
    assert pts[0].ghi_w_m2 == 450.0
    assert pts[0].pressure_hpa == pytest.approx(910.0)  # 91 kPa -> 910 hPa
    assert provider.data_kind == "reanalysis_nrt"
    assert provider.last_fetch_meta["cache"] == "miss"


def test_nasa_power_skips_fill_hours_never_zero_fills():
    payload = _nasa_payload([("2026010106", -999.0), ("2026010107", 500.0)])
    provider, _ = _provider_with(payload)
    pts = asyncio.run(
        provider.fetch_history(12.97, 77.59, "Asia/Kolkata", date(2026, 1, 1), date(2026, 1, 1))
    )
    assert len(pts) == 1  # fill hour dropped, not fabricated as 0
    assert pts[0].ghi_w_m2 == 500.0


def test_nasa_power_fetch_forecast_never_returns_future_rows():
    future_key = (datetime.now(UTC) + timedelta(days=2)).strftime("%Y%m%d%H")
    past_key = (datetime.now(UTC) - timedelta(hours=3)).strftime("%Y%m%d%H")
    payload = _nasa_payload([(past_key, 400.0), (future_key, 999.0)])
    provider, _ = _provider_with(payload)
    pts = asyncio.run(provider.fetch_forecast(12.97, 77.59, "Asia/Kolkata", past_days=1))
    now = datetime.now(UTC)
    assert pts, "past hour should be returned"
    assert all(p.timestamp.astimezone(UTC) <= now for p in pts)


def test_nasa_power_caches_identical_requests():
    payload = _nasa_payload([("2026010106", 450.0)])
    provider, calls = _provider_with(payload)

    async def run():
        await provider.fetch_history(
            12.97, 77.59, "Asia/Kolkata", date(2026, 1, 1), date(2026, 1, 1)
        )
        await provider.fetch_history(
            12.97, 77.59, "Asia/Kolkata", date(2026, 1, 1), date(2026, 1, 1)
        )

    asyncio.run(run())
    assert calls["n"] == 1
    assert provider.last_fetch_meta["cache"] == "hit"


# --------------------------------------------------------------------------- #
# KERC DSM 2026 gate + machinery
# --------------------------------------------------------------------------- #

_FIXTURE_ORDER = kerc.KercDsmOrder(
    order_id="TEST-FIXTURE-2026",
    title="TEST FIXTURE ONLY - not an official KERC order",
    url="tests/test_phase1_providers_kerc.py",
    effective_from=date(2026, 4, 1),
    effective_to=None,
    verified_official=True,  # test-only; production registration requires manual verification
    tolerance_percent=5.0,
    slabs=[
        kerc.KercSlab(5.0, 10.0, 2.0, "fixture clause A"),
        kerc.KercSlab(10.0, 15.0, 4.0, "fixture clause B"),
        kerc.KercSlab(15.0, 100000.0, 6.0, "fixture clause C"),
    ],
    annual_cap_inr=1000.0,
    deemed_schedule_allowed=True,
    applicability="test fixture applicability",
)


@pytest.fixture(autouse=True)
def _clean_orders():
    kerc.clear_orders()
    yield
    kerc.clear_orders()


def test_kerc_engine_ships_blocked_without_official_order():
    res = kerc.compute_block_charge(
        scheduled_kwh=1000.0, actual_kwh=800.0, on_date=date(2026, 7, 12)
    )
    assert res["status"] == kerc.NEEDS_OFFICIAL_SOURCE
    assert res["emits_rupee_values"] is False
    assert res["charge_inr"] is None


def test_kerc_unverified_order_never_activates():
    unverified = kerc.KercDsmOrder(
        order_id="STAGED-2026",
        title="staged, not verified",
        url="https://karnatakaerc.gov.in/example",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        verified_official=False,
        tolerance_percent=5.0,
        slabs=[kerc.KercSlab(5.0, 100000.0, 1.0, "unverified clause")],
    )
    kerc.register_order(unverified)
    res = kerc.compute_block_charge(
        scheduled_kwh=1000.0, actual_kwh=500.0, on_date=date(2026, 7, 12)
    )
    assert res["status"] == kerc.NEEDS_OFFICIAL_SOURCE
    assert res["emits_rupee_values"] is False


def test_kerc_cumulative_slabs_exact_math_with_fixture_order():
    kerc.register_order(_FIXTURE_ORDER)
    # 20% under-injection on 1000 kWh: 5-10% @2 (50kWh*2=100) + 10-15% @4 (50*4=200)
    # + 15-20% @6 (50*6=300) = 600 INR
    res = kerc.compute_block_charge(
        scheduled_kwh=1000.0, actual_kwh=800.0, on_date=date(2026, 7, 12)
    )
    assert res["status"] == kerc.OK
    assert res["deviation_percent"] == pytest.approx(20.0)
    assert res["charge_inr"] == pytest.approx(600.0)
    assert len(res["slab_charges"]) == 3
    assert all(s["citation"].startswith("fixture clause") for s in res["slab_charges"])
    assert res["order"]["order_id"] == "TEST-FIXTURE-2026"


def test_kerc_within_tolerance_charges_nothing():
    kerc.register_order(_FIXTURE_ORDER)
    res = kerc.compute_block_charge(
        scheduled_kwh=1000.0, actual_kwh=960.0, on_date=date(2026, 7, 12)
    )
    assert res["status"] == kerc.OK
    assert res["charge_inr"] == 0.0
    assert res["slab_charges"] == []


def test_kerc_annual_cap_and_effective_dates_and_rollback():
    kerc.register_order(_FIXTURE_ORDER)
    # cap: 1000 total, 700 already used -> 600 charge capped at 300
    res = kerc.compute_block_charge(
        scheduled_kwh=1000.0,
        actual_kwh=800.0,
        on_date=date(2026, 7, 12),
        year_to_date_charge_inr=700.0,
    )
    assert res["charge_inr"] == pytest.approx(300.0)
    assert res["annual_cap_applied"] is True

    # before effective_from -> blocked
    early = kerc.compute_block_charge(
        scheduled_kwh=1000.0, actual_kwh=800.0, on_date=date(2026, 3, 31)
    )
    assert early["status"] == kerc.NEEDS_OFFICIAL_SOURCE

    # rollback returns the engine to blocked
    kerc.clear_orders()
    rolled = kerc.compute_block_charge(
        scheduled_kwh=1000.0, actual_kwh=800.0, on_date=date(2026, 7, 12)
    )
    assert rolled["status"] == kerc.NEEDS_OFFICIAL_SOURCE


def test_kerc_invalid_schedule_is_explicit():
    kerc.register_order(_FIXTURE_ORDER)
    res = kerc.compute_block_charge(scheduled_kwh=0.0, actual_kwh=10.0, on_date=date(2026, 7, 12))
    assert res["status"] == "INVALID_SCHEDULE"
    assert res["emits_rupee_values"] is False


def test_kerc_module_is_json_serializable():
    kerc.register_order(_FIXTURE_ORDER)
    res = kerc.compute_block_charge(
        scheduled_kwh=1000.0, actual_kwh=800.0, on_date=date(2026, 7, 12)
    )
    json.dumps(res)  # must not raise
