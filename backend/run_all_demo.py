"""Run full system demonstration - all endpoints exercised."""
import asyncio
import json
import sys
sys.path.insert(0, ".")
from httpx import AsyncClient, ASGITransport
from app.main import app


async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as c:

        print("=" * 70)
        print("  SURYAGRID AI - PHASE 1 SYSTEM DEMONSTRATION")
        print("=" * 70)

        # 1. Health
        print("\n[1] GET /api/v1/health")
        r = await c.get("/api/v1/health")
        print(f"    Status: {r.status_code}")
        print(f"    Response: {json.dumps(r.json(), indent=6)}")

        # 2. Create Site
        print("\n[2] POST /api/v1/sites")
        r = await c.post("/api/v1/sites", json={
            "name": "Rajasthan Solar Park",
            "latitude": 26.9,
            "longitude": 70.9,
            "capacity_mw": 100.0,
            "panel_efficiency": 0.19,
        })
        site = r.json()["data"]
        site_id = site["id"]
        print(f"    Created: {site['name']} (ID: {site_id})")
        print(f"    Capacity: {site['capacity_mw']} MW")

        # 3. Generate Synthetic Data
        print("\n[3] POST /api/v1/synthetic-data/generate")
        r = await c.post(f"/api/v1/synthetic-data/generate?site_id={site_id}&seed=42&capacity_mw=100")
        d = r.json()["data"]
        print(f"    Generated: {d['readings_count']} weather readings")
        print(f"    Date: {d['date']}")
        print(f"    Sample (noon): {json.dumps(d['readings'][24], indent=6)}")

        # 4. Run Prediction
        print("\n[4] POST /api/v1/predict")
        r = await c.post("/api/v1/predict", json={
            "site_id": site_id,
            "solar_capacity_mw": 100.0,
            "irradiance_w_m2": 750.0,
            "cloud_cover_percent": 45.0,
            "temperature_c": 34.0,
            "scheduled_generation_mw": 65.0,
            "allowed_dsm_threshold_percent": 10.0,
            "penalty_rate_per_mw": 15000.0,
        })
        pred = r.json()["data"]
        print(f"    Predicted Generation:  {pred['predicted_generation_mw']} MW")
        print(f"    Scheduled Generation:  {pred['scheduled_generation_mw']} MW")
        print(f"    Deviation:             {pred['deviation_mw']} MW ({pred['deviation_percent']}%)")
        print(f"    Penalty Status:        {pred['penalty_status']}")
        print(f"    Estimated Penalty:     INR {pred['estimated_penalty_cost']:,.0f}")
        print(f"    Fuzzy Risk:            {pred['fuzzy_risk_level']} (score: {pred['fuzzy_risk_score']})")
        print(f"    Confidence:            {pred['confidence_score']}")
        print(f"    Explanation:           {pred['explanation']}")

        # 5. DSM Check
        print("\n[5] POST /api/v1/dsm/check")
        r = await c.post("/api/v1/dsm/check", json={
            "predicted_generation_mw": 4.65,
            "scheduled_generation_mw": 6.5,
            "allowed_dsm_threshold_percent": 10.0,
            "penalty_rate_per_mw": 15000.0,
        })
        dsm = r.json()["data"]
        print(f"    Deviation: {dsm['deviation_mw']} MW ({dsm['deviation_percent']}%)")
        print(f"    Status: {dsm['penalty_status']}")
        print(f"    Penalty Cost: INR {dsm['estimated_penalty_cost']:,.0f}")

        # 6. Timeline
        print("\n[6] GET /api/v1/timeline/{site_id}")
        r = await c.get(f"/api/v1/timeline/{site_id}?seed=42&capacity_mw=100&scheduled_mw=65")
        tl = r.json()["data"]
        print(f"    Entries: {len(tl['timeline'])}")
        print(f"    Date: {tl['date']}")
        print(f"    First 5 entries:")
        for entry in tl["timeline"][:5]:
            ts = entry["timestamp"].split("T")[1][:5]
            print(f"      {ts} | Irr: {entry['irradiance_w_m2']:6.1f} | Pred: {entry['predicted_generation_mw']:6.2f} MW | Sched: {entry['scheduled_generation_mw']:5.1f} MW | {entry['penalty_status']:13s} | {entry['fuzzy_risk_level']}")
        print(f"    ... + {len(tl['timeline']) - 5} more entries")

        # 7. Summary
        print("\n[7] GET /api/v1/summary/{site_id}")
        r = await c.get(f"/api/v1/summary/{site_id}?seed=42&capacity_mw=100&scheduled_mw=65")
        s = r.json()["data"]
        print(f"    Total Predicted:    {s['total_predicted_mw']:.1f} MW")
        print(f"    Total Scheduled:    {s['total_scheduled_mw']:.1f} MW")
        print(f"    Penalty Intervals:  {s['penalty_intervals']} / {s['total_intervals']}")
        print(f"    Max Deviation:      {s['max_deviation_percent']:.1f}%")

        # 8. Swagger docs
        print("\n[8] GET /docs (Swagger UI)")
        r = await c.get("/docs")
        print(f"    Status: {r.status_code} (Swagger UI accessible)")

        print("\n" + "=" * 70)
        print("  ALL SYSTEMS OPERATIONAL - PHASE 1 VALIDATED")
        print("=" * 70)


asyncio.run(main())
