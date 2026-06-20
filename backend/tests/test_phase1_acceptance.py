"""Phase 1 Acceptance Tests - validates the system works as a real operational MVP."""
import asyncio
import sys
sys.path.insert(0, ".")
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.agents.forecast_agent import ForecastAgent
from app.agents.dsm_classifier_agent import DSMClassifierAgent
from app.agents.fuzzy_risk_agent import FuzzyRiskAgent
from app.agents.synthetic_data_agent import SyntheticDataAgent
from datetime import date


# --- Agent-level acceptance ---

def test_1_site_creation_works():
    """AC-1: Sites can be created via API."""
    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/sites", json={
                "name": "Rajasthan Solar Park", "latitude": 26.9, "longitude": 70.9, "capacity_mw": 100.0,
            })
            assert r.status_code == 200
            d = r.json()["data"]
            assert d["name"] == "Rajasthan Solar Park"
            assert d["capacity_mw"] == 100.0
            assert "id" in d
    asyncio.run(_run())


def test_2_synthetic_data_generation():
    """AC-2: Synthetic weather/irradiance data generation works."""
    agent = SyntheticDataAgent()
    points = agent.generate_site_day("site-1", date(2026, 6, 20), 50.0, seed=42)
    assert len(points) == 48
    noon = points[24]
    assert noon.irradiance_w_m2 > 800
    assert 0 <= noon.cloud_cover_percent <= 100


def test_3_forecast_prediction():
    """AC-3: Forecast prediction produces valid MW output."""
    agent = ForecastAgent()
    r = agent.predict(solar_capacity_mw=100.0, irradiance_w_m2=800.0, cloud_cover_percent=30.0, temperature_c=30.0)
    assert r["predicted_generation_mw"] > 0
    assert r["predicted_generation_mw"] <= 100.0
    assert 0 < r["confidence_score"] <= 1.0


def test_4_dsm_threshold_classification():
    """AC-4: DSM classifier correctly identifies penalty risk."""
    agent = DSMClassifierAgent()
    # High deviation -> penalty
    r = agent.classify(20.0, 35.0, 10.0, 15000.0)
    assert r["penalty_status"] == "PENALTY_RISK"
    # Low deviation -> no penalty
    r2 = agent.classify(34.0, 35.0, 10.0, 15000.0)
    assert r2["penalty_status"] == "NO_PENALTY"


def test_5_fuzzy_risk_classification():
    """AC-5: Fuzzy risk correctly assigns levels."""
    agent = FuzzyRiskAgent()
    low = agent.score(5.0, 20.0, 800.0, 0.9)
    assert low["fuzzy_risk_level"] == "LOW"
    critical = agent.score(90.0, 90.0, 100.0, 0.4)
    assert critical["fuzzy_risk_level"] == "CRITICAL"


def test_6_explanation_generated():
    """AC-6: Explanation text is generated with prediction."""
    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/predict", json={
                "site_id": "s1", "solar_capacity_mw": 50.0, "irradiance_w_m2": 300.0,
                "cloud_cover_percent": 70.0, "temperature_c": 35.0, "scheduled_generation_mw": 35.0,
            })
            assert r.status_code == 200
            assert len(r.json()["data"]["explanation"]) > 20
    asyncio.run(_run())


def test_7_timeline_api_graph_ready():
    """AC-7: Timeline API returns graph-ready data with all required fields."""
    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/timeline/site1?seed=42&capacity_mw=50&scheduled_mw=35")
            assert r.status_code == 200
            tl = r.json()["data"]["timeline"]
            assert len(tl) == 48
            required_fields = ["timestamp", "irradiance_w_m2", "cloud_cover_percent",
                             "predicted_generation_mw", "scheduled_generation_mw",
                             "deviation_mw", "deviation_percent", "penalty_status", "fuzzy_risk_level"]
            for f in required_fields:
                assert f in tl[0], f"Missing timeline field: {f}"
    asyncio.run(_run())


def test_8_summary_api_correct_totals():
    """AC-8: Summary API returns correct totals."""
    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/summary/site1?seed=42&capacity_mw=50&scheduled_mw=35")
            assert r.status_code == 200
            s = r.json()["data"]
            assert s["total_intervals"] == 48
            assert s["total_predicted_mw"] > 0
            assert s["total_scheduled_mw"] > 0
            assert s["penalty_intervals"] >= 0
    asyncio.run(_run())


def test_9_no_divide_by_zero():
    """AC-9: Invalid schedule (zero) never causes divide-by-zero."""
    agent = DSMClassifierAgent()
    r = agent.classify(10.0, 0.0, 10.0, 15000.0)
    assert r["penalty_status"] == "INVALID_SCHEDULE"
    assert r["deviation_percent"] == 0.0
    r2 = agent.classify(10.0, -5.0, 10.0, 15000.0)
    assert r2["penalty_status"] == "INVALID_SCHEDULE"


def test_10_prediction_never_exceeds_capacity():
    """AC-10: Predicted generation is always clamped to solar capacity."""
    agent = ForecastAgent()
    # Extreme irradiance
    r = agent.predict(solar_capacity_mw=10.0, irradiance_w_m2=1500.0, cloud_cover_percent=0.0, temperature_c=15.0)
    assert r["predicted_generation_mw"] <= 10.0
    # Normal case
    r2 = agent.predict(solar_capacity_mw=50.0, irradiance_w_m2=950.0, cloud_cover_percent=0.0, temperature_c=25.0)
    assert r2["predicted_generation_mw"] <= 50.0


def test_11_api_response_schema_stable():
    """AC-12: API response always has success, message, data, timestamp."""
    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/health")
            body = r.json()
            assert "success" in body
            assert "message" in body
            assert "data" in body
            assert "timestamp" in body
    asyncio.run(_run())


def test_12_predict_response_complete():
    """AC-13: Predict response has all required output fields."""
    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/predict", json={
                "site_id": "s1", "solar_capacity_mw": 50.0, "irradiance_w_m2": 750.0,
                "cloud_cover_percent": 40.0, "temperature_c": 32.0, "scheduled_generation_mw": 35.0,
            })
            d = r.json()["data"]
            required = ["predicted_generation_mw", "scheduled_generation_mw", "deviation_mw",
                       "deviation_percent", "penalty_status", "estimated_penalty_cost",
                       "fuzzy_risk_score", "fuzzy_risk_level", "confidence_score", "explanation"]
            for f in required:
                assert f in d, f"Missing: {f}"
    asyncio.run(_run())


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for t in sorted(tests, key=lambda f: f.__name__):
        t()
        print(f"[PASS] {t.__doc__}")
    print(f"\n=== ALL {len(tests)} ACCEPTANCE TESTS PASSED ===")
