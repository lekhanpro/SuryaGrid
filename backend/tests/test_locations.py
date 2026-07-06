"""API tests for locations & substations (offline: CSV import, nearest, coverage)."""

import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app

CSV = (
    "name,voltage_level,operator,latitude,longitude,district,state,country\n"
    "Test BTM Substation,220000,BESCOM,12.91,77.61,Bengaluru,Karnataka,IN\n"
    "Test Hebbal Substation,66000,BESCOM,13.04,77.59,Bengaluru,Karnataka,IN\n"
)


async def run():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Seed DSM profiles so coverage can report the flag deterministically.
        await c.get("/api/v1/dsm/rule-profiles")

        # Import substations from CSV (offline; coordinates used as-is)
        r = await c.post("/api/v1/substations/import", json={"csv_text": CSV})
        assert r.status_code == 200
        assert r.json()["data"]["inserted"] >= 2

        # List substations
        r = await c.get("/api/v1/substations")
        assert r.status_code == 200
        subs = r.json()["data"]["substations"]
        assert any(s["name"].startswith("Test BTM") for s in subs)
        assert all("source_confidence" in s for s in subs)

        # Nearest substation to a Bangalore point
        r = await c.get(
            "/api/v1/substations/nearest/adhoc", params={"latitude": 12.97, "longitude": 77.59}
        )
        near = r.json()["data"]["nearest_substation"]
        assert near is not None
        assert near["distance_km"] >= 0

        # Available locations aggregate
        r = await c.get("/api/v1/locations/available")
        data = r.json()["data"]
        assert data["counts"]["substations"] >= 2
        assert data["counts"]["registry_sites"] >= 1

        # Unified locations list
        r = await c.get("/api/v1/locations")
        assert r.json()["data"]["count"] >= 2

        # Data coverage flags
        r = await c.get(
            "/api/v1/sites/adhoc/data-coverage", params={"latitude": 12.97, "longitude": 77.59}
        )
        cov = r.json()["data"]
        assert cov["weather_forecast_available"] is True
        assert cov["nearest_substation_available"] is True
        assert cov["dsm_rule_profile_available"] is True  # seeded above

        # Import validation error (neither csv nor coords)
        r = await c.post("/api/v1/substations/import", json={})
        assert r.status_code == 400

    print("Locations API tests PASSED")


def test_locations_api():
    asyncio.run(run())


if __name__ == "__main__":
    test_locations_api()
