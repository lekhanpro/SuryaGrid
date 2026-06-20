"""FuzzyRiskAgent - assigns risk level based on DSM + weather conditions."""


class FuzzyRiskAgent:
    def score(
        self,
        deviation_percent: float,
        cloud_cover_percent: float,
        irradiance_w_m2: float,
        confidence_score: float,
    ) -> dict:
        risk_score = 0.0
        risk_score += deviation_percent * 0.5
        risk_score += cloud_cover_percent * 0.2

        if irradiance_w_m2 < 300:
            risk_score += 20
        if confidence_score < 0.6:
            risk_score += 15

        risk_score = max(0.0, min(100.0, risk_score))

        if risk_score < 25:
            level = "LOW"
        elif risk_score < 50:
            level = "MEDIUM"
        elif risk_score < 75:
            level = "HIGH"
        else:
            level = "CRITICAL"

        return {
            "fuzzy_risk_score": round(risk_score, 2),
            "fuzzy_risk_level": level,
        }
