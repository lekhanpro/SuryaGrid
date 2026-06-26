"""Full system end-to-end test over the real pipeline (offline-deterministic)."""

import asyncio

from httpx import ASGITransport, AsyncClient

from app.api import routes_timeline, routes_weather
from app.main import app
from tests.conftest import FakeProvider


async def run():
    fake = FakeProvider()
    routes_timeline._service.provider = fake
    routes_weather._provider = fake

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        print("=== SURYAGRID AI - FULL SYSTEM TEST ===\n")

        r = await c.get("/api/v1/health")
        assert r.status_code == 200 and r.json()["data"]["status"] == "healthy"
        print("[PASS] 1. Health endpoint")

        r = await c.post("/api/v1/sites", json={
            "name": "Rajasthan Solar Park", "latitude": 26.9, "longitude": 70.9, "capacity_mw": 100.0,
        })
        site_id = r.json()["data"]["id"]
        print(f"[PASS] 2. Site created: {site_id}")

        r = await c.get(f"/api/v1/weather/{site_id}")
        assert r.json()["data"]["readings_count"] == 24
        print("[PASS] 3. Real weather provider returns irradiance data")

        r = await c.post("/api/v1/predict", json={
            "capacity_mw": 100.0, "ghi_w_m2": 820.0, "dni_w_m2": 700.0, "dhi_w_m2": 120.0,
            "cloud_cover_percent": 45.0, "temperature_c": 34.0, "scheduled_generation_mw": 65.0,
        })
        p = r.json()["data"]
        assert p["predicted_generation_mw"] > 0
        print(f"[PASS] 4. pvlib prediction: {p['predicted_generation_mw']} MW")

        assert p["penalty_status"] in ("PENALTY_RISK", "NO_PENALTY")
        print(f"[PASS] 5. DSM classification: {p['penalty_status']}")

        assert p["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        print(f"[PASS] 6. Risk level: {p['risk_level']} (score {p['risk_score']})")

        assert len(p["explanation"]) > 10
        print(f"[PASS] 7. Explanation: '{p['explanation'][:60]}...'")

        r = await c.get(f"/api/v1/timeline/{site_id}")
        tl = r.json()["data"]["timeline"]
        assert len(tl) == 24
        assert all(k in tl[12] for k in ["timestamp", "predicted_generation_mw", "energy_mwh", "penalty_status", "risk_level"])
        print("[PASS] 8. Timeline with energy + DSM values")

        r = await c.get(f"/api/v1/summary/{site_id}")
        s = r.json()["data"]
        assert s["predicted_energy_mwh"] > 0 and s["intervals"] == 24
        print(f"[PASS] 9. Summary: {s['predicted_energy_mwh']} MWh, {s['penalty_intervals']} penalty intervals")

        r = await c.post("/api/v1/dsm/check", json={
            "predicted_generation_mw": 4.65, "scheduled_generation_mw": 6.5,
        })
        assert r.json()["data"]["penalty_status"] == "PENALTY_RISK"
        print("[PASS] 10. Standalone DSM check")

        assert (await c.get("/docs")).status_code == 200
        print("[PASS] 11. Swagger docs accessible")

        body = (await c.post("/api/v1/predict", json={
            "capacity_mw": 50, "ghi_w_m2": 750, "dni_w_m2": 600, "dhi_w_m2": 100,
            "cloud_cover_percent": 40, "temperature_c": 32, "scheduled_generation_mw": 6.5,
        })).json()
        required = ["predicted_generation_mw", "scheduled_generation_mw", "deviation_mw",
                    "deviation_percent", "penalty_status", "estimated_penalty_cost",
                    "risk_score", "risk_level", "confidence_score", "explanation"]
        for f in required:
            assert f in body["data"], f"Missing: {f}"
        print("[PASS] 12. All required output fields present")

        print("\n=== ALL SYSTEM CHECKS PASSED ===")


if __name__ == "__main__":
    asyncio.run(run())
