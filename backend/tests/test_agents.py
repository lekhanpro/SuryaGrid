"""Tests for the Phase 1.5 agents and the full orchestrator run."""

import asyncio

from app.agents.api_management_agent import APIManagementAgent
from app.agents.dsm_engine_agent import DSMEngineAgent
from app.agents.feature_engineering_agent import FeatureEngineeringAgent
from app.agents.kaggle_data_agent import KaggleDataAgent
from app.agents.live_weather_agent import LiveWeatherAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.agents.persistence_agent import PersistenceAgent
from app.agents.source_registry_agent import SourceRegistryAgent
from app.data_sources.synthetic_weather_provider import SyntheticWeatherProvider
from app.db.database import AsyncSessionLocal


async def _synthetic_latest(self, latitude, longitude, timezone="Asia/Kolkata"):
    return {
        "ghi_w_m2": 620.0,
        "temperature_c": 31.0,
        "cloud_cover_percent": 20.0,
        "wind_speed_mps": 2.0,
        "humidity_percent": 45.0,
        "pressure_hpa": 1008.0,
        "precipitation_probability_percent": 5.0,
        "dni_w_m2": 0.0,
        "dhi_w_m2": 0.0,
        "provider": "synthetic",
        "mode": "synthetic",
        "cached": False,
    }


def test_source_registry_agent_validates():
    a = SourceRegistryAgent()
    assert a.validate()["valid"] is True
    assert len(a.formula_references()) >= 1
    assert a.cite("SRC-PVLIB-001")[0]["id"] == "SRC-PVLIB-001"


def test_kaggle_data_agent_status(tmp_path):
    from app.data_sources.kaggle_solar_provider import KaggleSolarProvider

    a = KaggleDataAgent(provider=KaggleSolarProvider(data_dir=tmp_path))
    assert a.is_loaded() is False
    assert a.status()["loaded"] is False


def test_feature_engineering_agent_builds_from_weather():
    pts = asyncio.run(
        SyntheticWeatherProvider().fetch_forecast(12.97, 77.59, "Asia/Kolkata", forecast_days=2)
    )
    a = FeatureEngineeringAgent()
    df, report = a.build_from_weather(
        pts, "synthetic", latitude=12.97, longitude=77.59, site_capacity_mw=50
    )
    assert len(df) == 48
    assert report["total_flagged"] == 0


def test_api_management_retry_and_status():
    mgmt = APIManagementAgent()
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    assert asyncio.run(mgmt.retry(flaky, attempts=3, base_delay=0.01)) == "ok"
    assert calls["n"] == 3
    status = asyncio.run(mgmt.system_status())
    assert status["database"] == "connected"


def test_persistence_agent_skips_adhoc_site():
    agent = PersistenceAgent()

    async def _():
        async with AsyncSessionLocal() as db:
            return await agent.save_forecast_point(
                db,
                None,
                {
                    "timestamp": "2026-06-25T12:00:00+00:00",
                    "predicted_generation_mw": 10,
                    "scheduled_generation_mw": 12,
                    "confidence_score": 0.8,
                },
            )

    assert asyncio.run(_()) == 0  # no site_uuid -> skip, best-effort


def test_dsm_engine_agent_resolves_and_evaluates():
    async def _():
        async with AsyncSessionLocal() as db:
            agent = DSMEngineAgent()
            prof = await agent.resolve_profile(db, regulator="KERC/BESCOM")
            r = agent.evaluate(prof, 30, 24, 50)
            return prof, r

    prof, r = asyncio.run(_())
    assert prof.name == "kerc-solar"
    assert r["penalty_status"] == "PENALTY_RISK"


def test_orchestrator_run_full(monkeypatch):
    monkeypatch.setattr(LiveWeatherAgent, "latest", _synthetic_latest)

    async def _():
        async with AsyncSessionLocal() as db:
            orch = OrchestratorAgent()
            return await orch.run_full(
                db,
                site_id="adhoc",
                latitude=14.1,
                longitude=77.28,
                capacity_mw=100,
                regulator="KERC/BESCOM",
                mode="auto",
            )

    out = asyncio.run(_())
    for key in (
        "forecast_mode",
        "predicted_generation_mw",
        "deviation_direction",
        "dsm_band",
        "penalty_status",
        "fuzzy_risk_score",
        "fuzzy_risk_level",
        "confidence_score",
        "data_sources",
        "sources",
        "explanation",
        "rule_source",
    ):
        assert key in out, f"missing {key}"
    assert out["forecast_mode"] in ("formula", "ml", "hybrid")
