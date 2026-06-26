"""DSMClassifierAgent - Deviation Settlement Mechanism classification.

Compares the generation nowcast against the scheduled (declared) generation and
decides whether the deviation breaches the allowed band, estimating the penalty.
This mirrors the Indian DSM regime: deviation beyond the permitted percentage of
the schedule attracts a charge proportional to the deviated energy.
"""

from __future__ import annotations

PENALTY_RISK = "PENALTY_RISK"
NO_PENALTY = "NO_PENALTY"
INVALID_SCHEDULE = "INVALID_SCHEDULE"


class DSMClassifierAgent:
    def classify(
        self,
        predicted_generation_mw: float,
        scheduled_generation_mw: float,
        allowed_dsm_threshold_percent: float,
        penalty_rate_per_mwh: float,
        interval_hours: float = 1.0,
    ) -> dict:
        if scheduled_generation_mw <= 0:
            return {
                "deviation_mw": 0.0,
                "deviation_percent": 0.0,
                "penalty_status": INVALID_SCHEDULE,
                "estimated_penalty_cost": 0.0,
            }

        deviation_mw = abs(predicted_generation_mw - scheduled_generation_mw)
        deviation_percent = (deviation_mw / scheduled_generation_mw) * 100.0

        if deviation_percent > allowed_dsm_threshold_percent:
            penalty_status = PENALTY_RISK
            # Charge applies to energy deviated beyond the allowed band.
            allowed_mw = scheduled_generation_mw * (allowed_dsm_threshold_percent / 100.0)
            chargeable_mw = max(0.0, deviation_mw - allowed_mw)
            estimated_penalty_cost = chargeable_mw * penalty_rate_per_mwh * interval_hours
        else:
            penalty_status = NO_PENALTY
            estimated_penalty_cost = 0.0

        return {
            "deviation_mw": round(deviation_mw, 4),
            "deviation_percent": round(deviation_percent, 2),
            "penalty_status": penalty_status,
            "estimated_penalty_cost": round(estimated_penalty_cost, 2),
        }
