"""DSMClassifierAgent - compares predicted vs scheduled, checks DSM threshold."""


class DSMClassifierAgent:
    def classify(
        self,
        predicted_generation_mw: float,
        scheduled_generation_mw: float,
        allowed_dsm_threshold_percent: float,
        penalty_rate_per_mw: float,
    ) -> dict:
        if scheduled_generation_mw <= 0:
            return {
                "deviation_mw": 0.0,
                "deviation_percent": 0.0,
                "penalty_status": "INVALID_SCHEDULE",
                "estimated_penalty_cost": 0.0,
            }

        deviation_mw = abs(predicted_generation_mw - scheduled_generation_mw)
        deviation_percent = (deviation_mw / scheduled_generation_mw) * 100.0

        if deviation_percent > allowed_dsm_threshold_percent:
            penalty_status = "PENALTY_RISK"
            estimated_penalty_cost = deviation_mw * penalty_rate_per_mw
        else:
            penalty_status = "NO_PENALTY"
            estimated_penalty_cost = 0.0

        return {
            "deviation_mw": round(deviation_mw, 3),
            "deviation_percent": round(deviation_percent, 2),
            "penalty_status": penalty_status,
            "estimated_penalty_cost": round(estimated_penalty_cost, 2),
        }
