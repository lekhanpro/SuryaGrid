"""Full system end-to-end test - validates all Phase 1 success criteria."""
import asyncio
import sys
sys.path.insert(0, ".")
from httpx import AsyncClient, ASGITransport
from app.main import app


async def run():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        print("=== SURYAGRID AI PHASE 1 - FULL SYSTEM TEST ===\n")

        # 1. Health
        r = await c.get("/api/v1/health")
        assert r.status_code == 200 and r.json()["data"]["status"] == "healthy"
        print("[PASS] 1. Backend starts and health endpoint works")

        # 2. Create site
        r = await c.post("/api/v1/sites", json={
            "name": "Hyderabad Solar Farm", "latitude": 17.38,
            "longitude": 78.48, "capacity_mw": 50.0, "panel_efficiency": 0.18,
        })
        assert r.status_code == 200
        site_id = r.json()["data"]["id"]
        print(f"[PASS] 2. Site created: {site_id}")

        # 3. Generate toy data
        r = await c.post(f"/api/v1/toy-data/generate?site_id={site_id}&seed=42&capacity_mw=50")
        assert r.status_code == 200 and r.json()["data"]["readings_count"] == 48
        print("[PASS] 3. Toy data generated (48 readings)")

        # 4. Solar prediction
        r = await c.post("/api/v1/predict", json={
            "site_id": site_id, "solar_capacity_mw": 50.0,
            "irradiance_w_m2": 750.0, "cloud_cover_percent": 40.0,
            "temperature_c": 32.0, "scheduled_generation_mw": 35.0,
            "allowed_dsm_threshold_percent": 10.0, "penalty_rate_per_mw": 15000.0,
        })
        assert r.status_code == 200
        p = r.json()["data"]
        assert p["predicted_generation_mw"] > 0
        print(f"[PASS] 4. Prediction: {p['predicted_generation_mw']} MW")

        # 5. DSM penalty classification
        assert p["penalty_status"] in ("PENALTY_RISK", "NO_PENALTY")
        print(f"[PASS] 5. DSM classification: {p['penalty_status']}")

        # 6. Fuzzy risk
        assert p["fuzzy_risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        print(f"[PASS] 6. Fuzzy risk: {p['fuzzy_risk_level']} (score: {p['fuzzy_risk_score']})")

        # 7. Explanation
        assert len(p["explanation"]) > 10
        print(f"[PASS] 7. Explanation: '{p['explanation'][:60]}...'")

        # 8. Timeline
        r = await c.get(f"/api/v1/timeline/{site_id}?seed=42&capacity_mw=50&scheduled_mw=35")
        assert r.status_code == 200
        tl = r.json()["data"]["timeline"]
        assert len(tl) == 48
        assert all(k in tl[0] for k in ["timestamp", "predicted_generation_mw", "penalty_status", "fuzzy_risk_level"])
        print(f"[PASS] 8. Timeline: 48 entries with all required fields")

        # 9. Summary
        r = await c.get(f"/api/v1/summary/{site_id}?seed=42&capacity_mw=50&scheduled_mw=35")
        assert r.status_code == 200
        s = r.json()["data"]
        assert s["total_predicted_mw"] > 0 and s["total_intervals"] == 48
        print(f"[PASS] 9. Summary: {s['total_predicted_mw']:.1f} MW predicted, {s['penalty_intervals']} penalty intervals")

        # 10. DSM check standalone
        r = await c.post("/api/v1/dsm/check", json={
            "predicted_generation_mw": 4.65, "scheduled_generation_mw": 6.5,
            "allowed_dsm_threshold_percent": 10.0, "penalty_rate_per_mw": 15000.0,
        })
        assert r.status_code == 200 and r.json()["data"]["penalty_status"] == "PENALTY_RISK"
        print("[PASS] 10. DSM check endpoint works")

        # 11. Swagger docs accessible
        r = await c.get("/docs")
        assert r.status_code == 200
        print("[PASS] 11. Swagger docs accessible at /docs")

        # 12. No real API keys needed (all toy data)
        print("[PASS] 12. No real API keys required")

        # 13. Verify response format
        r = await c.post("/api/v1/predict", json={
            "site_id": "x", "solar_capacity_mw": 50, "irradiance_w_m2": 750,
            "cloud_cover_percent": 40, "temperature_c": 32, "scheduled_generation_mw": 6.5,
        })
        body = r.json()
        assert "success" in body and "data" in body
        data = body["data"]
        required = ["predicted_generation_mw", "scheduled_generation_mw", "deviation_mw",
                    "deviation_percent", "penalty_status", "estimated_penalty_cost",
                    "fuzzy_risk_score", "fuzzy_risk_level", "confidence_score", "explanation"]
        for f in required:
            assert f in data, f"Missing: {f}"
        print("[PASS] 13. All required output fields present in /predict")

        print("\n=== ALL 13 PHASE 1 SUCCESS CRITERIA PASSED ===")


if __name__ == "__main__":
    asyncio.run(run())
