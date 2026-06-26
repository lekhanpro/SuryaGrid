"""Full system end-to-end test over the real pipeline (offline-deterministic)."""

import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.conftest import use_fake_provider


async def run():
    use_fake_provider()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        print("=== SURYAGRID AI - FULL SYSTEM TEST ===\n")

        r = await c.get("/api/v1/health")
        d = r.json()["data"]
        assert r.status_code == 200 and d["status"] == "healthy"
        assert d["database"] == "connected"
        print(f"[PASS] 1. Health + DB connected ({d['database_engine']})")

        r = await c.post(
            "/api/v1/sites",
            json={
                "name": "Rajasthan Solar Park",
                "latitude": 26.9,
                "longitude": 70.9,
                "capacity_mw": 100.0,
            },
        )
        site_id = r.json()["data"]["id"]
        print(f"[PASS] 2. Site persisted: {site_id}")

        r = await c.get(f"/api/v1/weather/{site_id}")
        assert r.json()["data"]["readings_count"] == 24
        print("[PASS] 3. Weather fetched + persisted")

        r = await c.post(
            "/api/v1/predict",
            json={
                "capacity_mw": 100.0,
                "ghi_w_m2": 820.0,
                "dni_w_m2": 700.0,
                "dhi_w_m2": 120.0,
                "cloud_cover_percent": 45.0,
                "temperature_c": 34.0,
                "scheduled_generation_mw": 65.0,
            },
        )
        p = r.json()["data"]
        assert p["predicted_generation_mw"] > 0
        print(f"[PASS] 4. pvlib prediction: {p['predicted_generation_mw']} MW")

        r = await c.get(f"/api/v1/timeline/{site_id}")
        tl = r.json()["data"]["timeline"]
        assert len(tl) == 24 and r.json()["data"]["persisted"]
        print("[PASS] 5. Timeline + forecast persistence")

        r = await c.get(f"/api/v1/energy/{site_id}", params={"consumption_base_kw": 30000})
        eb = r.json()["data"]
        assert eb["total_production_kwh"] > 0
        print(f"[PASS] 6. Energy balance: self-consumption {eb['self_consumption_percent']}%")

        r = await c.post(f"/api/v1/settle/day/{site_id}")
        sd = r.json()["data"]
        assert sd["intervals"] == 24
        print(f"[PASS] 7. Settlement: net_owner Rs {sd['net_owner']:,.0f}")

        r = await c.get(f"/api/v1/settlements/{site_id}")
        assert r.json()["data"]["count"] > 0
        print("[PASS] 8. Settlements persisted and retrievable")

        r = await c.get("/api/v1/rl/rates")
        assert "penalty_rate" in r.json()["data"]
        print("[PASS] 9. RL policy serving rates")

        assert (await c.get("/docs")).status_code == 200
        print("[PASS] 10. Swagger docs accessible")

        print("\n=== ALL SYSTEM CHECKS PASSED ===")


if __name__ == "__main__":
    asyncio.run(run())
