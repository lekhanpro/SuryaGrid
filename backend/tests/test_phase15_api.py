"""API tests for Phase 1.5 groups: sources, system, ml, dsm, full predict, errors."""

import asyncio

from httpx import ASGITransport, AsyncClient

from app.agents.live_weather_agent import LiveWeatherAgent
from app.main import app


async def _synthetic_latest(self, latitude, longitude, timezone="Asia/Kolkata"):
    # Offline stand-in so /predict/{id} never hits the network in tests.
    return {
        "ghi_w_m2": 600.0,
        "dni_w_m2": 0.0,
        "dhi_w_m2": 0.0,
        "temperature_c": 31.0,
        "cloud_cover_percent": 25.0,
        "wind_speed_mps": 2.5,
        "humidity_percent": 45.0,
        "pressure_hpa": 1008.0,
        "precipitation_probability_percent": 5.0,
        "provider": "synthetic",
        "mode": "synthetic",
        "cached": False,
    }


async def run(patched: bool):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Sources
        r = await c.get("/api/v1/sources")
        assert r.status_code == 200 and r.json()["data"]["count"] >= 6
        assert (await c.get("/api/v1/sources/SRC-OPENMETEO-001")).status_code == 200
        assert (await c.get("/api/v1/sources/NOPE")).status_code == 404  # error response

        # Data-sources status
        r = await c.get("/api/v1/data-sources/status")
        assert any(
            p["provider_type"] == "historical_dataset" for p in r.json()["data"]["providers"]
        )

        # System status
        r = await c.get("/api/v1/system/status")
        d = r.json()["data"]
        assert d["database"] == "connected"
        assert "model" in d and "weather_providers" in d

        # ML model status (untrained by default in the test models dir)
        r = await c.get("/api/v1/ml/model/status")
        assert "model" in r.json()["data"]

        # DSM rule-profiles (seeds if empty) + advanced check
        r = await c.get("/api/v1/dsm/rule-profiles")
        names = [p["name"] for p in r.json()["data"]["profiles"]]
        assert "kerc-solar" in names
        r = await c.post(
            "/api/v1/dsm/advanced-check",
            json={
                "scheduled_generation_mw": 30,
                "predicted_generation_mw": 24,
                "installed_capacity_mw": 50,
                "regulator": "KERC/BESCOM",
            },
        )
        adv = r.json()["data"]
        assert adv["penalty_status"] == "PENALTY_RISK"
        assert adv["rule_source"]["status"].startswith("USER_CONFIGURABLE")
        assert adv["sources"]

        # Full site prediction (weather patched to synthetic offline)
        if patched:
            r = await c.get(
                "/api/v1/predict/adhoc",
                params={
                    "latitude": 14.1,
                    "longitude": 77.28,
                    "capacity_mw": 100,
                    "regulator": "KERC/BESCOM",
                },
            )
            assert r.status_code == 200
            p = r.json()["data"]
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
            ):
                assert key in p, f"missing {key}"

        # Validation error (POST /predict missing required field)
        r = await c.post("/api/v1/predict", json={"ghi_w_m2": 500})
        assert r.status_code == 422

    print("Phase 1.5 API tests PASSED")


def test_phase15_api(monkeypatch):
    monkeypatch.setattr(LiveWeatherAgent, "latest", _synthetic_latest)
    asyncio.run(run(patched=True))


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
