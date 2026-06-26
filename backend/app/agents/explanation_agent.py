"""ExplanationAgent - human-readable summary of a DSM interval result."""

from __future__ import annotations


class ExplanationAgent:
    def explain(
        self,
        predicted_generation_mw: float,
        scheduled_generation_mw: float,
        deviation_percent: float,
        penalty_status: str,
        risk_level: str,
        cloud_cover_percent: float,
        ghi_w_m2: float,
        estimated_penalty_cost: float,
    ) -> str:
        if penalty_status == "INVALID_SCHEDULE":
            return "Schedule is zero or negative, so no DSM deviation can be assessed for this interval."

        parts: list[str] = []

        if penalty_status == "PENALTY_RISK":
            direction = "below" if predicted_generation_mw < scheduled_generation_mw else "above"
            parts.append(
                f"Penalty risk: forecast generation ({predicted_generation_mw:.2f} MW) is "
                f"{deviation_percent:.1f}% {direction} the scheduled {scheduled_generation_mw:.2f} MW, "
                "breaching the allowed deviation band."
            )
            if estimated_penalty_cost > 0:
                parts.append(
                    f"Estimated DSM charge for this interval: \u20b9{estimated_penalty_cost:,.0f}."
                )
        else:
            parts.append(
                f"Within band: forecast {predicted_generation_mw:.2f} MW tracks the scheduled "
                f"{scheduled_generation_mw:.2f} MW ({deviation_percent:.1f}% deviation)."
            )

        drivers = []
        if cloud_cover_percent > 50:
            drivers.append(f"{cloud_cover_percent:.0f}% cloud cover")
        if ghi_w_m2 < 200:
            drivers.append("low irradiance")
        if drivers:
            parts.append("Weather driver: " + ", ".join(drivers) + ".")

        if risk_level in ("HIGH", "CRITICAL"):
            parts.append(f"Operational risk is {risk_level}; close monitoring advised.")

        return " ".join(parts)
