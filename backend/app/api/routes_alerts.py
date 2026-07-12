"""Alerts + acknowledgment API (Phase 4).

  POST /alerts/evaluate       - run the workflow for a substation, return alerts
  GET  /alerts                - list alerts (optionally only unacknowledged)
  POST /alerts/{id}/ack       - acknowledge an alert (operator role when auth on)
  POST /auth/token            - issue a JWT (dev helper; real IdP would replace it)

Alert acknowledgment requires the 'operator' role only when AUTH_REQUIRED is on;
with auth off the dependency is a passthrough so dev/tests are unaffected.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.agents.ai.alerts import get_alert_store
from app.agents.substation_orchestrator import get_substation_orchestrator
from app.config import get_settings
from app.core.auth import create_access_token, get_current_principal, require_role
from app.core.exceptions import NotFoundError
from app.services.substation_context_service import get_substation_context_service
from app.utils.response import success_response

router = APIRouter()
_service = get_substation_context_service()
_orchestrator = get_substation_orchestrator()
_alerts = get_alert_store()
_require_operator = require_role("operator")  # build the dependency once (avoids B008)


class EvaluateAlertsRequest(BaseModel):
    substation_id: str
    site_capacity_mw: float | None = Field(default=None, gt=0)
    scheduled_generation_mw: float | None = Field(default=None, ge=0)
    forecast_horizon_hours: int = Field(default=6, ge=1, le=48)
    use_live_weather: bool = True


class TokenRequest(BaseModel):
    subject: str = Field(..., description="user id / service name")
    role: str = Field(default="viewer", description="viewer | operator | admin")


@router.post("/auth/token")
async def issue_token(body: TokenRequest):
    """Dev helper to mint a JWT. A real deployment integrates an external IdP."""
    token = create_access_token(body.subject, body.role)
    s = get_settings()
    return success_response(
        data={
            "access_token": token,
            "token_type": "bearer",
            "expires_in_minutes": s.JWT_EXPIRATION_MINUTES,
            "auth_required": s.AUTH_REQUIRED,
        }
    )


@router.post("/alerts/evaluate")
async def evaluate_alerts(body: EvaluateAlertsRequest):
    context = _service.get_context(body.substation_id)
    if context is None:
        raise NotFoundError(f"Substation '{body.substation_id}' not found.")
    result = await _orchestrator.run(
        context,
        site_capacity_mw=body.site_capacity_mw,
        forecast_horizon_hours=body.forecast_horizon_hours,
        scheduled_generation_mw=body.scheduled_generation_mw,
        use_live_weather=body.use_live_weather,
    )
    alerts = _alerts.evaluate(result)
    from dataclasses import asdict

    return success_response(
        data={"count": len(alerts), "alerts": [asdict(a) for a in alerts]},
        message="Alerts evaluated from the deterministic anomaly detective.",
    )


@router.get("/alerts")
async def list_alerts(
    only_unacked: bool = Query(default=False),
    _principal=Depends(get_current_principal),
):
    return success_response(data={"alerts": _alerts.list(only_unacked=only_unacked)})


@router.post("/alerts/{alert_id}/ack")
async def acknowledge_alert(
    alert_id: str,
    principal=Depends(_require_operator),
):
    user = (principal or {}).get("sub", "anonymous")
    alert = _alerts.acknowledge(alert_id, user)
    if alert is None:
        raise NotFoundError(f"Alert '{alert_id}' not found.")
    from dataclasses import asdict

    return success_response(data=asdict(alert), message="Alert acknowledged.")
