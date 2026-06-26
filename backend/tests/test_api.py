"""API integration tests using ASGI transport (no live server, no network)."""

import asyncio

from httpx import ASGITransport, AsyncClient

from app.api import routes_timeline, routes_weather
from app.main import app
from tests.conftest import FakeProvider


def _use_fake_provider():
    fake = FakeProvider()
    routes_timeline._service.provider = fake
    routes_weather._provider = fake


async def run_tests():
    _use_fake_provider()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Health
        r = await c.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "healthy"

        # Create site
        r = await c.post("/api/v1/sites", json={
            "name": "Hyderabad Solar", "latitude": 17.38, "longitude": 78.48, "capacity_mw": 50.0,
        })
        assert r.status_code == 200
        site_id = r.json()["data"]["id"]

        # Get site / 404
        assert (await c.get(f"/api/v1/sites/{site_id}")).status_code == 200
        assert (await c.get("/api/v1/sites/nonexistent")).status_code == 404

        # Weather (real fields, fake source for the test)
        r = await c.get(f"/api/v1/weather/{site_id}")
        assert r.status_code == 200
        w = r.json()["data"]
        assert w["readings_count"] == 24
        assert "ghi_w_m2" in w["readings"][12]

        # Predict (single interval)
        r = await c.post("/api/v1/predict", json={
            "capacity_mw": 50.0, "ghi_w_m2": 800.0, "dni_w_m2": 700.0, "dhi_w_m2": 100.0,
            "cloud_cover_percent": 30.0, "temperature_c": 32.0, "scheduled_generation_mw": 35.0,
        })
        assert r.status_code == 200
        pred = r.json()["data"]
        assert "predicted_generation_mw" in pred and "explanation" in pred

        # DSM check - penalty
        r = await c.post("/api/v1/dsm/check", json={
            "predicted_generation_mw": 4.65, "scheduled_generation_mw": 6.5,
        })
        assert r.json()["data"]["penalty_status"] == "PENALTY_RISK"

        # DSM check - invalid
        r = await c.post("/api/v1/dsm/check", json={
            "predicted_generation_mw": 10.0, "scheduled_generation_mw": 0.0,
        })
        assert r.json()["data"]["penalty_status"] == "INVALID_SCHEDULE"

        # Timeline
        r = await c.get(f"/api/v1/timeline/{site_id}")
        assert r.status_code == 200
        data = r.json()["data"]
        assert len(data["timeline"]) == 24
        assert data["summary"]["predicted_energy_mwh"] > 0

        # Summary
        r = await c.get(f"/api/v1/summary/{site_id}")
        assert r.status_code == 200
        assert r.json()["data"]["intervals"] == 24

    print("All API tests PASSED")


def test_all_apis():
    asyncio.run(run_tests())


if __name__ == "__main__":
    test_all_apis()
