"""Phase 1.5 - AI reasoning layer: fallback, structured output, numeric equivalence.

Deterministic & offline: the underlying workflow runs with use_live_weather=False;
LLM behavior is exercised through injected fake clients (no network, no real LLM).

  * AI disabled (default config) -> deterministic_fallback with useful insights
  * fake LLM returning valid JSON -> status "llm", schema-validated narrative
  * fake LLM returning garbage -> retries exhausted -> deterministic_fallback
  * numbers in the AI endpoint response equal the deterministic endpoint's
  * anomalies are rule-based and identical in both paths
  * checkpoints are recorded for audit

Run: python -m pytest tests/test_ai_reasoning_layer.py -q
"""

import asyncio
import json
from datetime import datetime

import pytest

from app.agents.ai.anomaly_detective import detect_anomalies
from app.agents.ai.orchestrator import AIReasoningOrchestrator
from app.agents.ai.state import get_checkpoint_store
from app.agents.substation_orchestrator import SubstationOrchestrator
from app.config import Settings
from app.services.substation_context_service import get_substation_context_service

SVC = get_substation_context_service()
_START = datetime(2024, 6, 1, 6, 0, 0)


def _require_substations():
    if SVC.count() == 0:
        pytest.skip("substation parquet not present")


def _result(**kwargs) -> dict:
    ctx = SVC.get_context(SVC.list_catalog(limit=1)[0]["substation_id"])
    orch = SubstationOrchestrator()
    return asyncio.run(orch.run(ctx, use_live_weather=False, start_time=_START, **kwargs))


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeClient:
    """Minimal OpenAI-compatible chat client; returns queued replies in order."""

    def __init__(self, replies):
        self._replies = list(replies)
        self.calls = 0
        outer = self

        class _Completions:
            async def create(self, **kwargs):
                outer.calls += 1
                reply = outer._replies[min(outer.calls - 1, len(outer._replies) - 1)]
                if isinstance(reply, Exception):
                    raise reply
                return _FakeResponse(reply)

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


_VALID_REPLY = json.dumps(
    {
        "summary": "Forecast is clear-sky driven with moderate output.",
        "key_findings": ["Peak GHI occurs midday."],
        "operator_suggestions": ["Enable live weather when possible."],
        "confidence_note": "Estimated values only; limitations apply.",
    }
)

_AI_ON = Settings(AI_ENABLED=True, AI_MODEL="fake-model", AI_MAX_RETRIES=2)


def test_disabled_ai_returns_deterministic_fallback():
    _require_substations()
    res = _result(site_capacity_mw=50.0)
    ai = asyncio.run(AIReasoningOrchestrator(settings=Settings()).run(res))
    assert ai["status"] == "deterministic_fallback"
    assert ai["reason"] == "AI disabled by configuration"
    ins = ai["insights"]
    assert ins["summary"] and ins["confidence_note"]
    assert isinstance(ins["anomalies"], list)
    assert ai["numeric_equivalence"] is True


def test_llm_success_returns_validated_narrative():
    _require_substations()
    res = _result(site_capacity_mw=50.0)
    client = _FakeClient([_VALID_REPLY])
    ai = asyncio.run(AIReasoningOrchestrator(client=client, settings=_AI_ON).run(res))
    assert ai["status"] == "llm"
    assert ai["model"] == "fake-model"
    assert ai["attempts"] == 1
    assert ai["insights"]["summary"].startswith("Forecast is clear-sky")
    # anomalies stay deterministic even on the LLM path
    assert ai["insights"]["anomalies"] == detect_anomalies(res)


def test_llm_garbage_retries_then_falls_back():
    _require_substations()
    res = _result()
    client = _FakeClient(["not json at all", "still { broken"])
    ai = asyncio.run(AIReasoningOrchestrator(client=client, settings=_AI_ON).run(res))
    assert ai["status"] == "deterministic_fallback"
    assert ai["attempts"] == 2
    assert client.calls == 2
    assert "LLM failed after 2 attempt(s)" in ai["reason"]
    assert ai["insights"]["summary"]  # fallback still useful


def test_llm_exception_falls_back():
    _require_substations()
    res = _result()
    client = _FakeClient([RuntimeError("connection refused")])
    ai = asyncio.run(AIReasoningOrchestrator(client=client, settings=_AI_ON).run(res))
    assert ai["status"] == "deterministic_fallback"
    assert "connection refused" in ai["reason"]


def test_llm_reply_with_code_fences_is_parsed():
    _require_substations()
    res = _result()
    client = _FakeClient([f"```json\n{_VALID_REPLY}\n```"])
    ai = asyncio.run(AIReasoningOrchestrator(client=client, settings=_AI_ON).run(res))
    assert ai["status"] == "llm"


def test_checkpoints_recorded():
    _require_substations()
    res = _result()
    asyncio.run(AIReasoningOrchestrator(settings=Settings()).run(res))
    cps = get_checkpoint_store().list(limit=5)
    assert any(cp["stage"] == "start" for cp in cps)
    assert any(cp["status"] == "deterministic_fallback" for cp in cps)


# --------------------------------------------------------------------------- #
# API layer: numeric equivalence between /orchestrate/substation and .../ai
# --------------------------------------------------------------------------- #
async def _api(method, path, **kw):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        return await getattr(c, method)(path, **kw)


def test_ai_endpoint_numbers_match_deterministic_endpoint():
    _require_substations()

    async def run():
        sid = SVC.list_catalog(limit=1)[0]["substation_id"]
        body = {
            "substation_id": sid,
            "site_capacity_mw": 50,
            "scheduled_generation_mw": 20,
            "forecast_horizon_hours": 6,
            "use_live_weather": False,
        }
        det = (await _api("post", "/api/v1/orchestrate/substation", json=body)).json()["data"]
        ai = (await _api("post", "/api/v1/orchestrate/substation/ai", json=body)).json()["data"]

        assert ai["ai"]["status"] == "deterministic_fallback"  # AI disabled in tests
        assert ai["ai"]["numeric_equivalence"] is True
        # identical numeric surface (same substation, same deterministic pipeline)
        assert ai["generation_summary"] == det["generation_summary"]
        assert ai["dsm_forecast"]["deviation_percent"] == det["dsm_forecast"]["deviation_percent"]
        assert len(ai["generation_timeline"]) == len(det["generation_timeline"])
        assert (
            ai["workflow"]["calculation_trace"].keys()
            == det["workflow"]["calculation_trace"].keys()
        )

    asyncio.run(run())
