"""AI reasoning orchestrator - LLM narrative with a deterministic fallback.

Contract:
  * The deterministic orchestrator result is computed FIRST and passed in; this
    layer never changes a number in it (numeric equivalence by construction).
  * If the LLM is disabled, unreachable, times out, or returns invalid JSON
    ``AI_MAX_RETRIES`` times, the response degrades to the deterministic
    explanation with ``status="deterministic_fallback"`` and the reason recorded.
  * Anomalies are always the rule-based detective's output, in both paths.
  * Every run writes start/done checkpoints for audit.
"""

from __future__ import annotations

import json
import uuid

from pydantic import BaseModel

from app.agents.ai.anomaly_detective import detect_anomalies
from app.agents.ai.explanation import deterministic_explanation
from app.agents.ai.policies import policy_summary
from app.agents.ai.prompts import SYSTEM_PROMPT, user_prompt
from app.agents.ai.state import AICheckpoint, get_checkpoint_store
from app.agents.ai.tools import numeric_digest
from app.config import Settings, get_settings
from app.core.logging import logger


class AIInsights(BaseModel):
    """Strict structured output required from the LLM."""

    summary: str
    key_findings: list[str]
    operator_suggestions: list[str]
    confidence_note: str


def _extract_json(text: str) -> dict:
    """Parse a JSON object out of an LLM reply (tolerates code fences)."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in LLM reply")
    return json.loads(text[start : end + 1])


class AIReasoningOrchestrator:
    def __init__(self, client=None, settings: Settings | None = None):
        self._client = client  # injectable OpenAI-compatible client (tests, custom)
        self._settings = settings

    def _config(self) -> Settings:
        return self._settings or get_settings()

    def _make_client(self, s: Settings):
        from openai import AsyncOpenAI

        return AsyncOpenAI(base_url=s.AI_BASE_URL or None, api_key=s.AI_API_KEY or "not-needed")

    async def run(self, result: dict) -> dict:
        s = self._config()
        run_id = uuid.uuid4().hex[:12]
        substation_id = result.get("substation", {}).get("substation_id", "?")
        store = get_checkpoint_store()
        store.append(AICheckpoint(run_id, substation_id, "start", "running"))

        digest = numeric_digest(result)
        anomalies = detect_anomalies(result)

        if not (s.AI_ENABLED and s.AI_MODEL):
            return self._fallback(
                result, run_id, substation_id, attempts=0, reason="AI disabled by configuration"
            )

        client = self._client or self._make_client(s)
        attempts = 0
        last_error = ""
        while attempts < max(1, s.AI_MAX_RETRIES):
            attempts += 1
            try:
                resp = await client.chat.completions.create(
                    model=s.AI_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt(digest, anomalies)},
                    ],
                    temperature=0.2,
                    timeout=s.AI_TIMEOUT_S,
                )
                insights = AIInsights.model_validate(
                    _extract_json(resp.choices[0].message.content or "")
                )
                store.append(
                    AICheckpoint(
                        run_id, substation_id, "done", "llm", attempts=attempts, model=s.AI_MODEL
                    )
                )
                return {
                    "status": "llm",
                    "model": s.AI_MODEL,
                    "attempts": attempts,
                    "run_id": run_id,
                    "numeric_equivalence": True,  # numbers are the deterministic run's, untouched
                    "insights": {**insights.model_dump(), "anomalies": anomalies},
                    "policy": policy_summary(),
                    "reason": None,
                }
            except Exception as exc:  # noqa: BLE001 - any LLM failure degrades, never breaks
                last_error = str(exc)
                logger.warning(f"AI attempt {attempts} failed: {exc}")
                store.append(
                    AICheckpoint(
                        run_id,
                        substation_id,
                        "llm_attempt",
                        "error",
                        attempts=attempts,
                        model=s.AI_MODEL,
                        error=last_error[:500],
                    )
                )

        return self._fallback(
            result,
            run_id,
            substation_id,
            attempts=attempts,
            reason=f"LLM failed after {attempts} attempt(s): {last_error[:300]}",
        )

    @staticmethod
    def _fallback(result: dict, run_id: str, substation_id: str, *, attempts: int, reason: str):
        get_checkpoint_store().append(
            AICheckpoint(run_id, substation_id, "done", "deterministic_fallback", attempts=attempts)
        )
        return {
            "status": "deterministic_fallback",
            "model": None,
            "attempts": attempts,
            "run_id": run_id,
            "numeric_equivalence": True,
            "insights": deterministic_explanation(result),
            "policy": policy_summary(),
            "reason": reason,
        }


_ai_orchestrator = AIReasoningOrchestrator()


def get_ai_orchestrator() -> AIReasoningOrchestrator:
    return _ai_orchestrator
