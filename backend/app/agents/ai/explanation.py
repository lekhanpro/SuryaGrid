"""Deterministic explanation builder - the LLM fallback path.

Composes operator-readable insights purely from the orchestrator result, so the
AI endpoint returns something useful even with no LLM configured or reachable.
"""

from __future__ import annotations

from app.agents.ai.anomaly_detective import detect_anomalies
from app.agents.ai.tools import numeric_digest


def deterministic_explanation(result: dict) -> dict:
    d = numeric_digest(result)
    anomalies = detect_anomalies(result)

    parts = [
        f"Substation {d['substation_label'] or d['substation_id']}: "
        f"{d['horizon_hours']}h horizon, weather mode '{d['weather_mode']}'."
    ]
    if d["peak_estimated_generation_mw"] is not None:
        parts.append(
            f"Estimated peak {d['peak_estimated_generation_mw']} MW, "
            f"total {d['total_estimated_energy_mwh']} MWh (ESTIMATED from irradiance)."
        )
    else:
        parts.append("No MW estimate: site capacity was not provided (irradiance only).")
    if d["deviation_percent"] is not None:
        parts.append(f"Deviation vs schedule {d['deviation_percent']}% ({d['deviation_band']}).")

    findings: list[str] = []
    if d["max_forecast_ghi_wm2"] is not None:
        findings.append(f"Peak forecast GHI {d['max_forecast_ghi_wm2']} W/m2.")
    if d["max_cloud_drop_risk"] is not None:
        findings.append(f"Max cloud drop risk {round(d['max_cloud_drop_risk'] * 100)}%.")
    if d["blocked_calculations"]:
        findings.append(
            "Blocked calculations (missing real sources): " + ", ".join(d["blocked_calculations"])
        )

    suggestions: list[str] = []
    if d["peak_estimated_generation_mw"] is None:
        suggestions.append("Provide site_capacity_mw to unlock MW/MWh estimates.")
    if d["deviation_percent"] is None:
        suggestions.append(
            "Provide scheduled_generation_mw (and capacity) to assess DSM deviation."
        )
    if any(a["code"] == "HIGH_CLOUD_DROP_RISK" for a in anomalies):
        suggestions.append(
            "Cloud-drop risk is elevated; consider conservative scheduling for the flagged hours."
        )
    if any(a["code"] == "WEATHER_DEGRADED_TO_CLEARSKY" for a in anomalies):
        suggestions.append(
            "Run with live weather enabled for cloud-aware forecasts when connectivity allows."
        )

    return {
        "summary": " ".join(parts),
        "key_findings": findings,
        "operator_suggestions": suggestions,
        "confidence_note": (
            f"{d['limitations_count']} limitation(s) recorded; generation is estimated, "
            "never measured; no rupee DSM values (official tariff not parsed)."
        ),
        "anomalies": anomalies,
    }
