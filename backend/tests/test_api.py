"""API integration tests using ASGI transport (no live server, no network)."""

import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.conftest import use_fake_provider


async def run_tests():
    use_fake_provider()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Health
        r = await c.get("/api/v1/health")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

        # Create site (persisted in DB → returns a UUID)
        r = await c.post(
            "/api/v1/sites",
            json={
                "name": "Hyderabad Solar",
                "latitude": 17.38,
                "longitude": 78.48,
                "capacity_mw": 50.0,
            },
        )
        assert r.status_code == 200
        site_id = r.json()["data"]["id"]
        assert len(site_id) >= 32  # uuid string

        # Get site / 404
        assert (await c.get(f"/api/v1/sites/{site_id}")).status_code == 200
        assert (
            await c.get("/api/v1/sites/00000000-0000-0000-0000-000000000000")
        ).status_code == 404

        # List includes the created site
        r = await c.get("/api/v1/sites")
        assert any(s["id"] == site_id for s in r.json()["data"])

        # Weather (persisted because site exists)
        r = await c.get(f"/api/v1/weather/{site_id}")
        assert r.status_code == 200
        w = r.json()["data"]
        assert w["readings_count"] == 24
        assert w["persisted"] is True

        # Predict (single interval)
        r = await c.post(
            "/api/v1/predict",
            json={
                "capacity_mw": 50.0,
                "ghi_w_m2": 800.0,
                "dni_w_m2": 700.0,
                "dhi_w_m2": 100.0,
                "cloud_cover_percent": 30.0,
                "temperature_c": 32.0,
                "scheduled_generation_mw": 35.0,
            },
        )
        assert r.status_code == 200
        assert "predicted_generation_mw" in r.json()["data"]

        # DSM checks
        r = await c.post(
            "/api/v1/dsm/check",
            json={"predicted_generation_mw": 4.65, "scheduled_generation_mw": 6.5},
        )
        assert r.json()["data"]["penalty_status"] == "PENALTY_RISK"
        r = await c.post(
            "/api/v1/dsm/check",
            json={"predicted_generation_mw": 10.0, "scheduled_generation_mw": 0.0},
        )
        assert r.json()["data"]["penalty_status"] == "INVALID_SCHEDULE"

        # Timeline (persists forecasts for the registered site)
        r = await c.get(f"/api/v1/timeline/{site_id}")
        assert r.status_code == 200
        td = r.json()["data"]
        assert len(td["timeline"]) == 24
        assert td["summary"]["predicted_energy_mwh"] > 0
        assert td["persisted"] is True

        # Energy balance
        r = await c.get(f"/api/v1/energy/{site_id}", params={"consumption_base_kw": 5000})
        assert r.status_code == 200
        eb = r.json()["data"]
        assert eb["total_production_kwh"] > 0
        assert "self_consumption_percent" in eb

        # Settlement day (persists settlements)
        r = await c.post(f"/api/v1/settle/day/{site_id}", params={"use_rl_rates": "true"})
        assert r.status_code == 200
        sd = r.json()["data"]
        assert sd["intervals"] == 24

        # Settlements list reflects persistence
        r = await c.get(f"/api/v1/settlements/{site_id}")
        assert r.json()["data"]["count"] > 0

        # RL rates
        r = await c.get("/api/v1/rl/rates")
        assert "penalty_rate" in r.json()["data"]

    print("All API tests PASSED")


def test_all_apis():
    asyncio.run(run_tests())


if __name__ == "__main__":
    test_all_apis()
