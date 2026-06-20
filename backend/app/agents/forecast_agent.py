"""ForecastAgent - predicts solar generation from weather + panel data."""


class ForecastAgent:
    def predict(
        self,
        solar_capacity_mw: float,
        irradiance_w_m2: float,
        cloud_cover_percent: float,
        temperature_c: float,
    ) -> dict:
        base_generation = solar_capacity_mw * (irradiance_w_m2 / 1000.0)
        cloud_loss_factor = 1.0 - ((cloud_cover_percent / 100.0) * 0.75)
        temperature_loss_factor = 1.0 - max(0.0, temperature_c - 25.0) * 0.005
        predicted = base_generation * cloud_loss_factor * temperature_loss_factor
        predicted = max(0.0, min(predicted, solar_capacity_mw))

        # Confidence based on data quality indicators
        confidence = 1.0
        if cloud_cover_percent > 70:
            confidence -= 0.2
        if irradiance_w_m2 < 200:
            confidence -= 0.15
        confidence = max(0.3, min(1.0, confidence))

        return {
            "predicted_generation_mw": round(predicted, 3),
            "confidence_score": round(confidence, 2),
        }
