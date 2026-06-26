"""Energy balance service - production vs consumption per interval.

Computes surplus/deficit, self-consumption %, grid import/export for each
interval. Inputs are the forecast timeline (production MW) and a consumption
profile (kW). All numbers in kW for consistency with settlement.
"""

from __future__ import annotations


def compute_energy_balance(
    production_kw: list[float],
    consumption_kw: list[float],
    interval_hours: float = 1.0,
) -> dict:
    """Compute per-interval and aggregate energy balance.

    Args:
        production_kw: generation output per interval (kW).
        consumption_kw: load per interval (kW).
        interval_hours: duration of each interval in hours (default 1h).

    Returns:
        Dict with per-interval breakdown and aggregates.
    """
    n = min(len(production_kw), len(consumption_kw))
    intervals = []
    total_production = 0.0
    total_consumption = 0.0
    total_surplus = 0.0
    total_deficit = 0.0
    total_self_consumed = 0.0
    total_grid_export = 0.0
    total_grid_import = 0.0

    for i in range(n):
        prod = production_kw[i]
        cons = consumption_kw[i]
        surplus = max(0.0, prod - cons)
        deficit = max(0.0, cons - prod)
        self_consumed = min(prod, cons)

        total_production += prod * interval_hours
        total_consumption += cons * interval_hours
        total_surplus += surplus * interval_hours
        total_deficit += deficit * interval_hours
        total_self_consumed += self_consumed * interval_hours
        total_grid_export += surplus * interval_hours
        total_grid_import += deficit * interval_hours

        intervals.append(
            {
                "hour": i,
                "production_kw": round(prod, 2),
                "consumption_kw": round(cons, 2),
                "surplus_kw": round(surplus, 2),
                "deficit_kw": round(deficit, 2),
                "self_consumed_kw": round(self_consumed, 2),
                "grid_export_kw": round(surplus, 2),
                "grid_import_kw": round(deficit, 2),
            }
        )

    self_consumption_pct = (
        (total_self_consumed / total_production * 100) if total_production > 0 else 0.0
    )

    return {
        "intervals": n,
        "interval_hours": interval_hours,
        "total_production_kwh": round(total_production, 2),
        "total_consumption_kwh": round(total_consumption, 2),
        "total_surplus_kwh": round(total_surplus, 2),
        "total_deficit_kwh": round(total_deficit, 2),
        "total_self_consumed_kwh": round(total_self_consumed, 2),
        "total_grid_export_kwh": round(total_grid_export, 2),
        "total_grid_import_kwh": round(total_grid_import, 2),
        "self_consumption_percent": round(self_consumption_pct, 1),
        "breakdown": intervals,
    }
