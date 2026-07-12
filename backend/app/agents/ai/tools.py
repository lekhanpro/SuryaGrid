"""Read-only tools over the deterministic orchestrator result.

``numeric_digest`` compacts the result into the ONLY numbers the LLM ever sees,
so the reasoning layer cannot fabricate values that are not in the run.
"""

from __future__ import annotations


def _max_or_none(values: list) -> float | None:
    vals = [v for v in values if v is not None]
    return max(vals) if vals else None


def numeric_digest(result: dict) -> dict:
    """Compact, purely-derived numeric summary of one orchestrator run."""
    summary = result.get("generation_summary", {})
    dsm = result.get("dsm_forecast", {})
    weather = result.get("weather", {})
    timeline = result.get("generation_timeline", [])
    calc = result.get("workflow", {}).get("calculation_trace", {})
    breach = dsm.get("breach_risk") if isinstance(dsm.get("breach_risk"), dict) else {}
    breach_value = breach.get("prediction_value") if isinstance(breach, dict) else None

    return {
        "substation_id": result.get("substation", {}).get("substation_id"),
        "substation_label": result.get("substation", {}).get("display_label"),
        "weather_mode": weather.get("mode"),
        "weather_source_label": weather.get("source_label"),
        "horizon_hours": weather.get("hours"),
        "daylight_intervals": summary.get("daylight_intervals"),
        "peak_estimated_generation_mw": summary.get("peak_estimated_generation_mw"),
        "total_estimated_energy_mwh": summary.get("total_estimated_energy_mwh"),
        "max_forecast_ghi_wm2": _max_or_none([r.get("forecast_ghi_wm2") for r in timeline]),
        "max_cloud_drop_risk": _max_or_none(
            [
                (r.get("cloud_drop_risk") or {}).get("probability")
                if isinstance(r.get("cloud_drop_risk"), dict)
                else r.get("cloud_drop_risk")
                for r in timeline
            ]
        ),
        "deviation_percent": dsm.get("deviation_percent"),
        "deviation_band": dsm.get("deviation_band"),
        "breach_probability": breach_value.get("probability")
        if isinstance(breach_value, dict)
        else None,
        "blocked_calculations": [b.get("calculation") for b in dsm.get("blocked_calculations", [])],
        "calculations_skipped": calc.get("calculations_skipped", []),
        "limitations_count": len(result.get("limitations", [])),
        "is_estimated": result.get("is_estimated"),
        "is_synthetic": result.get("is_synthetic"),
    }
