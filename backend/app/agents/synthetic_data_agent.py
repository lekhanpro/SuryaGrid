"""SyntheticDataAgent - generates simulated weather/cloud/irradiance/schedule data for Phase 1."""

import math
import random
from datetime import date, datetime, timedelta, timezone
from dataclasses import dataclass


@dataclass
class WeatherDataPoint:
    timestamp: datetime
    irradiance_w_m2: float
    cloud_cover_percent: float
    temperature_c: float
    humidity_percent: float
    wind_speed_mps: float
    rain_probability_percent: float


class SyntheticDataAgent:
    """Generates a full day of simulated solar/weather data for a site.
    
    Phase 1 uses deterministic synthetic data. In later phases, this agent
    will be replaced by real provider integrations (Solcast, Open-Meteo, NASA POWER).
    """

    def generate_site_day(
        self,
        site_id: str,
        target_date: date,
        capacity_mw: float,
        interval_minutes: int = 30,
        seed: int | None = None,
    ) -> list[WeatherDataPoint]:
        if seed is not None:
            random.seed(seed)

        points = []
        cloud_base = random.uniform(10, 50)
        cloud_blocks = self._generate_cloud_blocks()

        current = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
        end = current + timedelta(days=1)

        while current < end:
            hour = current.hour + current.minute / 60.0
            irradiance = self._solar_irradiance(hour)
            cloud = self._cloud_at_hour(hour, cloud_base, cloud_blocks)
            temp = self._temperature(hour)
            humidity = max(20, min(95, 80 - temp * 0.8 + random.gauss(0, 5)))
            wind = max(0, random.gauss(3.0, 1.5))
            rain = min(100, max(0, (cloud - 60) * 1.5)) if cloud > 60 else 0.0

            points.append(WeatherDataPoint(
                timestamp=current,
                irradiance_w_m2=round(irradiance, 1),
                cloud_cover_percent=round(cloud, 1),
                temperature_c=round(temp, 1),
                humidity_percent=round(humidity, 1),
                wind_speed_mps=round(wind, 2),
                rain_probability_percent=round(rain, 1),
            ))
            current += timedelta(minutes=interval_minutes)

        return points

    def generate_schedule(
        self, capacity_mw: float, target_date: date, interval_minutes: int = 30
    ) -> list[tuple[datetime, float]]:
        """Generate a smooth scheduled generation curve for daylight hours."""
        schedule = []
        current = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
        end = current + timedelta(days=1)

        while current < end:
            hour = current.hour + current.minute / 60.0
            if 6 <= hour <= 18:
                fraction = math.sin(math.pi * (hour - 6) / 12) * 0.7
                mw = capacity_mw * fraction
            else:
                mw = 0.0
            schedule.append((current, round(mw, 3)))
            current += timedelta(minutes=interval_minutes)
        return schedule

    @staticmethod
    def _solar_irradiance(hour: float, max_irradiance: float = 950.0) -> float:
        if hour < 6 or hour > 18:
            return 0.0
        return max_irradiance * math.sin(math.pi * (hour - 6) / 12)

    @staticmethod
    def _temperature(hour: float) -> float:
        base = 25.0 + 8.0 * math.sin(math.pi * (hour - 6) / 16)
        return base + random.gauss(0, 1.5)

    @staticmethod
    def _generate_cloud_blocks() -> list[tuple[float, float, float]]:
        blocks = []
        n = random.randint(0, 3)
        for _ in range(n):
            start = random.uniform(7, 16)
            duration = random.uniform(1, 3)
            intensity = random.uniform(40, 90)
            blocks.append((start, start + duration, intensity))
        return blocks

    @staticmethod
    def _cloud_at_hour(hour: float, base: float, blocks: list[tuple[float, float, float]]) -> float:
        cloud = base + random.gauss(0, 5)
        for start, end, intensity in blocks:
            if start <= hour <= end:
                cloud = max(cloud, intensity + random.gauss(0, 5))
        return max(0, min(100, cloud))


# Backward compatibility alias
ToyDataAgent = SyntheticDataAgent
ToyWeatherPoint = WeatherDataPoint
