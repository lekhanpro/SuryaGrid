"""Substation-driven agent workflow tests - honesty & provenance.

Verifies that a selected substation becomes the central context object flowing through
weather -> solar -> cloud -> generation timeline -> DSM, and that nothing is fabricated:

  * a valid substation returns a full context; missing capacity/voltage stay null;
  * the orchestrator uses the substation's own lat/lon;
  * every timeline row carries the substation_id and is clearly ESTIMATED;
  * the DSM step receives the context and BLOCKS capacity/load/tariff calculations that
    have no real source (no rupee charge is ever emitted);
  * responses always include agent_trace + calculation_trace + data_sources + limitations;
  * in APP_DATA_MODE=real nothing is synthetic.

Deterministic & offline: the orchestrator is run with use_live_weather=False and a fixed
start_time, so no network is touched (pvlib clear-sky physics at the substation coords).

Run: python -m pytest tests/ -q
"""

import asyncio
from datetime import datetime

import pytest

from app.agents.substation_orchestrator import SubstationOrchestrator
from app.ml import provenance as prov
from app.services.substation_context_service import get_substation_context_service

SVC = get_substation_context_service()
_START = datetime(2024, 6, 1, 6, 0, 0)  # 06:00 IST so a 12h horizon covers midday


def _require_substations():
    if SVC.count() == 0:
        pytest.skip(
            "bengaluru_substations_cleaned.parquet not present; "
            "run the substation ingestion to populate backend/data/ml/."
        )


def _first_id() -> str:
    return SVC.list_catalog(limit=1)[0]["substation_id"]


def _run(context, **kwargs) -> dict:
    orch = SubstationOrchestrator()
    return asyncio.run(orch.run(context, use_live_weather=False, start_time=_START, **kwargs))


def _solar_model_present() -> bool:
    return (prov.trained_models_dir() / "solar_forecast_model.pkl").exists()


# --------------------------------------------------------------------------- #
# Context (service)
# --------------------------------------------------------------------------- #
def test_valid_substation_returns_context():
    _require_substations()
    sid = _first_id()
    ctx = SVC.get_context(sid)
    assert ctx is not None
    assert ctx.substation_id == sid
    assert ctx.latitude is not None and ctx.longitude is not None
    assert ctx.display_label
    assert ctx.source_status in {prov.REAL_BENGALURU, prov.REAL_KARNATAKA}


def test_unknown_substation_returns_none():
    _require_substations()
    assert SVC.get_context("DOES-NOT-EXIST-999") is None


def test_missing_capacity_and_voltage_are_null_not_fabricated():
    _require_substations()
    # capacity_mva is entirely null in OSM: every context must keep it None + NOT_AVAILABLE.
    for row in SVC.list_catalog(limit=100):
        ctx = SVC.get_context(row["substation_id"])
        assert ctx.capacity_mva is None, "capacity_mva must never be fabricated"
        assert ctx.capacity_status == prov.NOT_AVAILABLE
        assert ctx.source_status in {prov.REAL_BENGALURU, prov.REAL_KARNATAKA}
        if ctx.voltage_kv is None:
            assert ctx.voltage_status == prov.NOT_AVAILABLE
            assert "voltage_kv" in ctx.missing_fields
        else:
            # voltage_status inherits the substation's own provenance label (never fabricated)
            assert ctx.voltage_status == ctx.source_status


def test_display_label_handles_unknown_voltage():
    _require_substations()
    for row in SVC.list_catalog(limit=200):
        ctx = SVC.get_context(row["substation_id"])
        if ctx.voltage_kv is None:
            assert "voltage unknown" in ctx.display_label
            break
    else:
        pytest.skip("no substation with unknown voltage in the first 200 rows")


# --------------------------------------------------------------------------- #
# Orchestrator uses the substation context
# --------------------------------------------------------------------------- #
def test_orchestrator_uses_substation_latlon():
    _require_substations()
    ctx = SVC.get_context(_first_id())
    res = _run(ctx, site_capacity_mw=50.0, forecast_horizon_hours=6)
    cs = res["workflow"]["calculation_trace"]["clearsky_ghi_wm2"]["inputs"]
    assert cs["latitude"] == ctx.latitude
    assert cs["longitude"] == ctx.longitude
    assert res["weather"]["source_label"] == prov.REAL_COORDINATE_BASED


def test_timeline_rows_carry_substation_id_and_are_estimated():
    _require_substations()
    sid = _first_id()
    ctx = SVC.get_context(sid)
    res = _run(ctx, site_capacity_mw=50.0, forecast_horizon_hours=8)
    tl = res["generation_timeline"]
    assert len(tl) == 8
    assert all(r["substation_id"] == sid for r in tl)
    assert all(r["generation_type"] == "ESTIMATED_FROM_IRRADIANCE" for r in tl)
    assert all(r["actual_generation_available"] is False for r in tl)


def test_generation_requires_capacity_else_none():
    _require_substations()
    ctx = SVC.get_context(_first_id())
    res = _run(ctx, site_capacity_mw=None, forecast_horizon_hours=6)
    assert res["generation_summary"]["peak_estimated_generation_mw"] is None
    assert all(r["estimated_generation_mw"] is None for r in res["generation_timeline"])


@pytest.mark.skipif(not _solar_model_present(), reason="solar_forecast_model.pkl not trained")
def test_estimated_generation_positive_at_midday_with_model():
    _require_substations()
    ctx = SVC.get_context(_first_id())
    res = _run(ctx, site_capacity_mw=50.0, forecast_horizon_hours=12)
    midday = [r for r in res["generation_timeline"] if r["timestamp"].endswith("T12:00:00")]
    assert midday, "expected a 12:00 row within the horizon"
    assert midday[0]["forecast_ghi_wm2"] and midday[0]["forecast_ghi_wm2"] > 0
    assert midday[0]["estimated_generation_mw"] and midday[0]["estimated_generation_mw"] > 0


# --------------------------------------------------------------------------- #
# DSM receives context + honest blocking
# --------------------------------------------------------------------------- #
def test_dsm_receives_substation_context():
    _require_substations()
    sid = _first_id()
    ctx = SVC.get_context(sid)
    res = _run(ctx, site_capacity_mw=50.0, scheduled_generation_mw=20.0, forecast_horizon_hours=12)
    dsm = res["dsm_forecast"]
    assert dsm["substation_id"] == sid
    used = dsm["context_inputs_used"]
    assert used["substation_id"] == sid
    assert used["latitude"] == ctx.latitude
    assert used["longitude"] == ctx.longitude
    assert dsm["capacity_status"] == ctx.capacity_status


def test_dsm_blocks_capacity_load_and_tariff_and_no_rupees():
    _require_substations()
    ctx = SVC.get_context(_first_id())
    res = _run(ctx, site_capacity_mw=50.0, scheduled_generation_mw=20.0)
    dsm = res["dsm_forecast"]
    blocked = {b["calculation"] for b in dsm["blocked_calculations"]}
    assert "substation_loading_percent" in blocked  # capacity_mva is null
    assert "load_following_optimisation" in blocked  # no real load telemetry
    assert "dsm_rupee_charge" in blocked  # no official tariff
    assert dsm["substation_loading_percent"] is None
    assert dsm["capacity_status"] == prov.NOT_AVAILABLE
    assert dsm["load_data_status"] == prov.NOT_AVAILABLE
    assert dsm["tariff_status"] == prov.NEEDS_OFFICIAL_SOURCE
    assert dsm["emits_rupee_values"] is False


# --------------------------------------------------------------------------- #
# Trace + provenance + real-mode
# --------------------------------------------------------------------------- #
def test_workflow_has_full_agent_trace_and_calculation_trace():
    _require_substations()
    ctx = SVC.get_context(_first_id())
    res = _run(ctx, site_capacity_mw=50.0, scheduled_generation_mw=20.0)
    agents = [t["agent"] for t in res["workflow"]["agent_trace"]]
    for expected in (
        "SubstationContextAgent",
        "WeatherAgent",
        "SolarIrradianceAgent",
        "CloudRiskAgent",
        "GenerationTimelineAgent",
        "DSMAgent",
        "OrchestratorAgent",
    ):
        assert expected in agents
    calc = res["workflow"]["calculation_trace"]
    assert "clearsky_ghi_wm2" in calc
    assert "estimated_generation_mw" in calc  # capacity was provided


def test_real_mode_has_no_synthetic_data():
    _require_substations()
    ctx = SVC.get_context(_first_id())
    res = _run(ctx, site_capacity_mw=50.0)
    assert res["is_synthetic"] is False
    assert res["is_estimated"] is True
    assert res["data_mode"] == prov.DATA_MODE_REAL
    labels = {d["label"] for d in res["data_sources"]}
    assert prov.SYNTHETIC_AUGMENTED_FROM_REAL not in labels
    assert prov.DEMO_ONLY not in labels


def test_response_has_data_sources_and_limitations():
    _require_substations()
    ctx = SVC.get_context(_first_id())
    res = _run(ctx, site_capacity_mw=50.0)
    assert isinstance(res["data_sources"], list) and len(res["data_sources"]) >= 3
    assert all("label" in d and "url" in d for d in res["data_sources"])
    assert isinstance(res["limitations"], list) and len(res["limitations"]) >= 1


# --------------------------------------------------------------------------- #
# API layer
# --------------------------------------------------------------------------- #
async def _api(method, path, **kw):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        return await getattr(c, method)(path, **kw)


def test_api_catalog_detail_and_404():
    _require_substations()

    async def run():
        r = await _api("get", "/api/v1/substations/catalog", params={"limit": 5})
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["count"] >= 1
        assert data["total_available"] == SVC.count()
        sid = data["substations"][0]["substation_id"]
        assert "display_label" in data["substations"][0]

        r = await _api("get", f"/api/v1/substations/{sid}")
        assert r.status_code == 200
        assert r.json()["data"]["capacity_status"] == prov.NOT_AVAILABLE

        r = await _api("get", "/api/v1/substations/NOT-A-REAL-ID")
        assert r.status_code == 404

    asyncio.run(run())


def test_api_orchestrate_endpoint_is_honest():
    _require_substations()

    async def run():
        sid = _first_id()
        r = await _api(
            "post",
            "/api/v1/orchestrate/substation",
            json={
                "substation_id": sid,
                "site_capacity_mw": 50,
                "scheduled_generation_mw": 20,
                "forecast_horizon_hours": 6,
                "use_live_weather": False,  # deterministic, no network
            },
        )
        assert r.status_code == 200
        d = r.json()["data"]
        assert len(d["generation_timeline"]) == 6
        assert all(row["substation_id"] == sid for row in d["generation_timeline"])
        assert d["is_synthetic"] is False
        assert d["dsm_forecast"]["emits_rupee_values"] is False
        assert len(d["workflow"]["agent_trace"]) == 7

    asyncio.run(run())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
