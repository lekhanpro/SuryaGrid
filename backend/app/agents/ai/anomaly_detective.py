"""Rule-based anomaly detection over one orchestrator run.

Deterministic by design: the same run always yields the same anomalies, each
carrying the evidence numbers it was derived from. The LLM may narrate these
but never add or remove one.
"""

from __future__ import annotations

SEV_INFO = "info"
SEV_WARNING = "warning"
SEV_CRITICAL = "critical"


def detect_anomalies(result: dict) -> list[dict]:
    anomalies: list[dict] = []
    timeline = result.get("generation_timeline", [])
    dsm = result.get("dsm_forecast", {})
    weather = result.get("weather", {})

    risky_hours = [
        r
        for r in timeline
        if isinstance(r.get("cloud_drop_risk"), dict)
        and (r["cloud_drop_risk"].get("probability") or 0.0) >= 0.5
    ]
    if risky_hours:
        anomalies.append(
            {
                "code": "HIGH_CLOUD_DROP_RISK",
                "severity": SEV_WARNING,
                "message": f"{len(risky_hours)} of {len(timeline)} hours have >=50% "
                "probability of an irradiance drop.",
                "evidence": {
                    "hours": [r.get("timestamp") for r in risky_hours],
                    "max_probability": max(
                        r["cloud_drop_risk"]["probability"] for r in risky_hours
                    ),
                },
            }
        )

    band = dsm.get("deviation_band")
    if band and "EXCEEDS" in str(band):
        anomalies.append(
            {
                "code": "DEVIATION_BAND_EXCEEDED",
                "severity": SEV_CRITICAL,
                "message": "Estimated generation deviates from the schedule beyond the "
                "+/-15% modelling band.",
                "evidence": {
                    "deviation_percent": dsm.get("deviation_percent"),
                    "deviation_band": band,
                },
            }
        )

    breach = dsm.get("breach_risk")
    if isinstance(breach, dict):
        value = breach.get("prediction_value")
        prob = value.get("probability") if isinstance(value, dict) else None
        if prob is not None and prob >= 0.5:
            anomalies.append(
                {
                    "code": "HIGH_BREACH_RISK",
                    "severity": SEV_CRITICAL,
                    "message": "Model predicts a high probability of breaching the deviation band.",
                    "evidence": {"probability": prob},
                }
            )

    if weather.get("mode") != "live":
        anomalies.append(
            {
                "code": "WEATHER_DEGRADED_TO_CLEARSKY",
                "severity": SEV_INFO,
                "message": "Live weather was not used; irradiance is pvlib clear-sky "
                "physics at the substation coordinates.",
                "evidence": {"mode": weather.get("mode"), "live_error": weather.get("live_error")},
            }
        )

    for step in result.get("workflow", {}).get("agent_trace", []):
        if step.get("status") in ("not_available", "error"):
            anomalies.append(
                {
                    "code": "AGENT_STEP_UNAVAILABLE",
                    "severity": SEV_WARNING,
                    "message": f"{step.get('agent')} reported status '{step.get('status')}'.",
                    "evidence": {"step": step.get("step"), "detail": step.get("detail")},
                }
            )

    return anomalies
