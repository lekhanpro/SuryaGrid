"""Live demonstration of the real Suryagrid AI pipeline (calls Open-Meteo)."""

import asyncio
import json
import sys

sys.path.insert(0, ".")
from httpx import ASGITransport, AsyncClient

from app.main import app


async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000", timeout=60) as c:
        print("=" * 72)
        print("  SURYAGRID AI - LIVE PIPELINE DEMONSTRATION (real Open-Meteo data)")
        print("=" * 72)

        print("\n[1] GET /api/v1/health")
        r = await c.get("/api/v1/health")
        print(f"    {json.dumps(r.json()['data'])}")

        print("\n[2] POST /api/v1/sites  (Bhadla Solar Park, Rajasthan)")
        r = await c.post("/api/v1/sites", json={
            "name": "Bhadla Solar Park", "latitude": 27.53, "longitude": 71.91,
            "capacity_mw": 100.0, "tilt": 27.0, "azimuth": 180.0,
            "allowed_dsm_threshold_percent": 10.0, "penalty_rate_per_mwh": 12000.0,
        })
        site = r.json()["data"]
        site_id = site["id"]
        print(f"    Created {site['name']} ({site['capacity_mw']} MW) -> {site_id}")

        print("\n[3] GET /api/v1/weather/{site_id}  (real irradiance forecast)")
        r = await c.get(f"/api/v1/weather/{site_id}")
        w = r.json()["data"]
        noon = w["readings"][12]
        print(f"    Provider: {w['provider']}, {w['readings_count']} hourly readings")
        print(f"    Noon: GHI {noon['ghi_w_m2']} W/m2, DNI {noon['dni_w_m2']}, cloud {noon['cloud_cover_percent']}%, {noon['temperature_c']} C")

        print("\n[4] GET /api/v1/timeline/{site_id}  (nowcast + DSM per hour)")
        r = await c.get(f"/api/v1/timeline/{site_id}")
        data = r.json()["data"]
        s = data["summary"]
        print(f"    Predicted energy: {s['predicted_energy_mwh']} MWh | peak {s['peak_generation_mw']} MW")
        print(f"    Penalty intervals: {s['penalty_intervals']}/{s['intervals']} | est. charge Rs {s['total_penalty_cost']:,.0f}")
        print("    Daylight sample:")
        for e in data["timeline"]:
            if e["predicted_generation_mw"] > 0.5:
                ts = e["timestamp"][11:16]
                print(f"      {ts} | GHI {e['ghi_w_m2']:6.0f} | pred {e['predicted_generation_mw']:6.1f} MW "
                      f"| sched {e['scheduled_generation_mw']:6.1f} | dev {e['deviation_percent']:5.1f}% "
                      f"| {e['penalty_status']:12s} | {e['risk_level']}")

        print("\n" + "=" * 72)
        print("  PIPELINE OPERATIONAL - REAL DATA, REAL PHYSICS")
        print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())
