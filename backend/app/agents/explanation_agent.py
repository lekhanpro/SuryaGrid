"""ExplanationAgent - generates human-readable explanation of prediction result."""


class ExplanationAgent:
    def explain(
        self,
        predicted_generation_mw: float,
        scheduled_generation_mw: float,
        deviation_percent: float,
        penalty_status: str,
        fuzzy_risk_level: str,
        cloud_cover_percent: float,
        irradiance_w_m2: float,
    ) -> str:
        parts = []

        if penalty_status == "INVALID_SCHEDULE":
            return "Schedule is invalid (zero or negative). Cannot assess DSM deviation."

        if penalty_status == "PENALTY_RISK":
            if predicted_generation_mw < scheduled_generation_mw:
                parts.append("Penalty risk detected because predicted generation is lower than scheduled generation.")
            else:
                parts.append("Penalty risk detected because predicted generation exceeds scheduled generation.")
        else:
            parts.append("No penalty risk. Predicted generation is within the allowed DSM threshold.")

        # Weather factors
        reasons = []
        if cloud_cover_percent > 50:
            reasons.append("high cloud cover")
        if irradiance_w_m2 < 400:
            reasons.append("low solar irradiance")

        if reasons:
            parts.append(f"Contributing factors: {', '.join(reasons)} reduced expected solar output.")

        if fuzzy_risk_level in ("HIGH", "CRITICAL"):
            parts.append(f"Overall risk level is {fuzzy_risk_level} — close monitoring recommended.")

        return " ".join(parts)
