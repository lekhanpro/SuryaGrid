"""Configuration & route-registration validation (guards against wiring regressions)."""

import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app

EXPECTED_ROUTES = {
    ("GET", "/api/v1/health"),
    ("POST", "/api/v1/sites"),
    ("GET", "/api/v1/sites"),
    ("GET", "/api/v1/sites/{site_id}"),
    ("GET", "/api/v1/weather/{site_id}"),
    ("POST", "/api/v1/predict"),
    ("POST", "/api/v1/dsm/check"),
    ("GET", "/api/v1/timeline/{site_id}"),
    ("GET", "/api/v1/summary/{site_id}"),
}


def _registered_routes() -> set[tuple[str, str]]:
    """Read routes from the OpenAPI schema — stable across FastAPI versions."""
    routes = set()
    paths = app.openapi().get("paths", {})
    for path, methods in paths.items():
        for method in methods:
            routes.add((method.upper(), path))
    return routes


def test_all_expected_routes_registered():
    registered = _registered_routes()
    missing = EXPECTED_ROUTES - registered
    assert not missing, f"Missing routes: {missing}"


def test_no_legacy_toy_routes():
    registered = {path for _, path in _registered_routes()}
    assert not any("toy" in p or "synthetic" in p for p in registered)


def test_health_reports_dependency_status():
    """Regression: /health must report database and redis status keys."""

    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/v1/health")
            assert r.status_code == 200
            body = r.json()
            assert "timestamp" in body
            data = body["data"]
            assert data["status"] == "healthy"
            assert "database" in data and "redis" in data

    asyncio.run(_run())


if __name__ == "__main__":
    test_all_expected_routes_registered()
    test_no_legacy_toy_routes()
    test_health_reports_dependency_status()
    print("All app-config tests PASSED")
