"""Phase 4 - JWT/RBAC (flag-gated), alerts + acknowledgment, read-only connector.

Offline & deterministic. Auth is exercised in BOTH modes (disabled passthrough and
enabled enforcement) via injected Settings; the API tests use the default disabled
mode so the rest of the suite is unaffected.

Run: python -m pytest tests/test_phase4_auth_alerts_connector.py -q
"""

import asyncio
from datetime import datetime

import pytest

from app.agents.ai.alerts import AlertStore
from app.agents.substation_orchestrator import SubstationOrchestrator
from app.config import Settings
from app.core import auth
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.integrations.plant_connector import ReadOnlyPlantConnector, ReplayPlantConnector
from app.services.substation_context_service import get_substation_context_service

SVC = get_substation_context_service()
_START = datetime(2024, 6, 1, 6, 0, 0)
_AUTH_ON = Settings(AUTH_REQUIRED=True, JWT_SECRET_KEY="test-secret-not-placeholder")


def _require_substations():
    if SVC.count() == 0:
        pytest.skip("substation parquet not present")


def _result(**kwargs) -> dict:
    ctx = SVC.get_context(SVC.list_catalog(limit=1)[0]["substation_id"])
    return asyncio.run(
        SubstationOrchestrator().run(ctx, use_live_weather=False, start_time=_START, **kwargs)
    )


# --------------------------------------------------------------------------- #
# JWT / RBAC
# --------------------------------------------------------------------------- #
def test_token_roundtrip_and_role_claim():
    token = auth.create_access_token("alice", "operator", settings=_AUTH_ON)
    claims = auth.decode_token(token, settings=_AUTH_ON)
    assert claims["sub"] == "alice"
    assert claims["role"] == "operator"


def test_require_role_passthrough_when_auth_disabled():
    dep = auth.require_role("admin")
    # principal is None when auth is disabled -> allowed
    assert dep(principal=None) is None


def test_require_role_enforces_hierarchy_when_enabled():
    viewer = auth.decode_token(auth.create_access_token("v", "viewer", _AUTH_ON), _AUTH_ON)
    admin = auth.decode_token(auth.create_access_token("a", "admin", _AUTH_ON), _AUTH_ON)
    dep = auth.require_role("operator")
    with pytest.raises(ForbiddenError):
        dep(principal=viewer)  # viewer < operator
    assert dep(principal=admin) == admin  # admin >= operator


def test_enabled_auth_refuses_placeholder_secret():
    bad = Settings(AUTH_REQUIRED=True)  # keeps placeholder JWT_SECRET_KEY
    with pytest.raises(UnauthorizedError):
        auth._principal_from_request(request=None, creds=None, settings=bad)


def test_expired_token_rejected():
    s = Settings(AUTH_REQUIRED=True, JWT_SECRET_KEY="test-secret", JWT_EXPIRATION_MINUTES=-1)
    token = auth.create_access_token("bob", "viewer", settings=s)
    with pytest.raises(UnauthorizedError):
        auth.decode_token(token, settings=s)


# --------------------------------------------------------------------------- #
# Alerts + acknowledgment
# --------------------------------------------------------------------------- #
def test_alerts_evaluate_and_acknowledge_are_stable():
    _require_substations()
    res = _result()  # clear-sky, no capacity -> WEATHER_DEGRADED_TO_CLEARSKY at least
    store = AlertStore()
    first = store.evaluate(res)
    assert first, "expected at least one alert"
    # Re-evaluating the same run must not duplicate alerts (stable ids).
    second = store.evaluate(res)
    assert {a.alert_id for a in first} == {a.alert_id for a in second}
    assert len(store.list()) == len(first)

    aid = first[0].alert_id
    acked = store.acknowledge(aid, "operator-1")
    assert acked is not None and acked.acknowledged is True
    assert acked.acknowledged_by == "operator-1"
    assert store.acknowledge("nope", "x") is None
    assert len(store.list(only_unacked=True)) == len(first) - 1


# --------------------------------------------------------------------------- #
# Read-only plant connector + replay
# --------------------------------------------------------------------------- #
def test_replay_connector_is_read_only_and_validates():
    rows = [
        {
            "timestamp": "2026-07-01T12:00:00+05:30",
            "plant_id": "P1",
            "ac_power_kw": 4200.0,
            "inverter_state": "RUNNING",
            "quality_flag": "GOOD",
            "meter_id": "M1",
            "meter_source": "ABT meter",
        },
        {
            "timestamp": "bad",
            "plant_id": "P1",
            "quality_flag": "GOOD",
            "inverter_state": "RUNNING",
            "meter_id": "M1",
            "meter_source": "x",
        },  # rejected
    ]
    conn = ReplayPlantConnector("P1", rows)
    assert isinstance(conn, ReadOnlyPlantConnector)  # satisfies the read-only protocol
    first = conn.read_next()
    assert first is not None and first["generation_type"] == "MEASURED_LOCAL_PV"
    assert conn.snapshot() == first
    assert conn.read_next() is None  # second row rejected, stream exhausted
    assert len(conn.rejected) == 1

    # Hard guarantee: the connector exposes no control surface.
    for banned in ("write", "command", "set_point", "actuate", "control"):
        assert not hasattr(conn, banned), f"connector must not expose {banned}"


def test_connector_reset_replays_again():
    rows = [
        {
            "timestamp": "2026-07-01T12:00:00+05:30",
            "plant_id": "P1",
            "ac_power_kw": 1000.0,
            "inverter_state": "RUNNING",
            "quality_flag": "GOOD",
            "meter_id": "M1",
            "meter_source": "ABT meter",
        }
    ]
    conn = ReplayPlantConnector("P1", rows)
    assert conn.read_next() is not None
    assert conn.read_next() is None
    conn.reset()
    assert conn.read_next() is not None  # replays from the start


# --------------------------------------------------------------------------- #
# API layer (auth disabled by default -> endpoints open)
# --------------------------------------------------------------------------- #
async def _api(method, path, **kw):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        return await getattr(c, method)(path, **kw)


def test_alerts_api_evaluate_list_ack():
    _require_substations()

    async def run():
        sid = SVC.list_catalog(limit=1)[0]["substation_id"]
        r = await _api(
            "post",
            "/api/v1/alerts/evaluate",
            json={"substation_id": sid, "forecast_horizon_hours": 6, "use_live_weather": False},
        )
        assert r.status_code == 200
        alerts = r.json()["data"]["alerts"]
        assert alerts
        aid = alerts[0]["alert_id"]

        # auth disabled -> ack endpoint is reachable without a token
        r = await _api("post", f"/api/v1/alerts/{aid}/ack")
        assert r.status_code == 200
        assert r.json()["data"]["acknowledged"] is True

        r = await _api("post", "/api/v1/alerts/UNKNOWN/ack")
        assert r.status_code == 404

    asyncio.run(run())


def test_auth_token_endpoint_issues_jwt():
    async def run():
        r = await _api("post", "/api/v1/auth/token", json={"subject": "svc", "role": "operator"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["token_type"] == "bearer"
        assert data["auth_required"] is False
        claims = auth.decode_token(data["access_token"])
        assert claims["role"] == "operator"

    asyncio.run(run())
