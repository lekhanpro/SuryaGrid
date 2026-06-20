"""Service layer for ToyDataAgent - handles DB persistence."""

from datetime import date, datetime, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.toy_data_agent import ToyDataAgent
from app.db.models import ToyWeatherReading, ScheduleWindow


class ToyDataService:
    def __init__(self):
        self.agent = ToyDataAgent()

    async def generate_and_store(
        self,
        db: AsyncSession,
        site_id: UUID,
        capacity_mw: float,
        target_date: date,
        interval_minutes: int = 30,
        seed: int | None = None,
    ) -> dict:
        points = self.agent.generate_site_day(
            site_id=str(site_id),
            target_date=target_date,
            capacity_mw=capacity_mw,
            interval_minutes=interval_minutes,
            seed=seed,
        )

        # Store weather readings
        readings = [
            ToyWeatherReading(
                site_id=site_id,
                ts=p.timestamp,
                irradiance_w_m2=p.irradiance_w_m2,
                cloud_cover_percent=p.cloud_cover_percent,
                temperature_c=p.temperature_c,
                humidity_percent=p.humidity_percent,
                wind_speed_mps=p.wind_speed_mps,
                rain_probability_percent=p.rain_probability_percent,
            )
            for p in points
        ]
        db.add_all(readings)

        # Generate and store schedule
        schedule_data = self.agent.generate_schedule(capacity_mw, target_date, interval_minutes)
        daylight = [(ts, mw) for ts, mw in schedule_data if mw > 0]
        if daylight:
            window = ScheduleWindow(
                site_id=site_id,
                window_start=daylight[0][0],
                window_end=daylight[-1][0],
                scheduled_generation_mw=max(mw for _, mw in daylight),
            )
            db.add(window)

        await db.commit()

        return {
            "readings_count": len(readings),
            "date": target_date.isoformat(),
            "interval_minutes": interval_minutes,
        }
