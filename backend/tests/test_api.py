"""API integration tests using ASGI transport (no live server needed)."""
import asyncio
import sys
sys.path.insert(0, ".")
from httpx import AsyncClient, ASGITransport
from app.main import app


async def run_tests():
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

        # Get site
        r = await c.get(f"/api/v1/sites/{site_id}")
        assert r.status_code == 200

        # 404 for missing site
        r = await c.get("/api/v1/sites/nonexistent")
        assert r.status_code == 404

        # Generate toy data
        r = await c.post(f"/api/v1/toy-data/generate?site_id={site_id}&seed=42&capacity_mw=50")
        assert r.status_code == 200
        assert r.json()["data"]["readings_count"] == 48

        # Get toy data
        r = await c.get(f"/api/v1/toy-data/{site_id}")
        assert r.status_code == 200

        # Predict
        r = await c.post("/api/v1/predict", json={
            "site_id": site_id, "solar_capacity_mw": 50.0,
            "irradiance_w_m2": 750.0, "cloud_cover_percent": 40.0,
            "temperature_c": 32.0, "scheduled_generation_mw": 35.0,
        })
        assert r.status_code == 200
        pred = r.json()["data"]
        assert pred["site_id"] == site_id
        assert "predicted_generation_mw" in pred
        assert "explanation" in pred

        # DSM check
        r = await c.post("/api/v1/dsm/check", json={
            "predicted_generation_mw": 4.65, "scheduled_generation_mw": 6.5,
        })
        assert r.status_code == 200
        assert r.json()["data"]["penalty_status"] == "PENALTY_RISK"

        # DSM check - invalid schedule
        r = await c.post("/api/v1/dsm/check", json={
            "predicted_generation_mw": 10.0, "scheduled_generation_mw": 0.0,
        })
        assert r.status_code == 200
        assert r.json()["data"]["penalty_status"] == "INVALID_SCHEDULE"

        # Timeline
        r = await c.get(f"/api/v1/timeline/{site_id}?seed=42&capacity_mw=50&scheduled_mw=35")
        assert r.status_code == 200
        assert len(r.json()["data"]["timeline"]) == 48

        # Summary
        r = await c.get(f"/api/v1/summary/{site_id}?seed=42&capacity_mw=50&scheduled_mw=35")
        assert r.status_code == 200
        s = r.json()["data"]
        assert s["total_intervals"] == 48
        assert s["total_predicted_mw"] > 0

    print("All API tests PASSED")


def test_all_apis():
    asyncio.run(run_tests())


if __name__ == "__main__":
    test_all_apis()
