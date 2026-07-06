"""PersistenceAgent - ensure important records are saved.

Coordinator over the repositories. Persistence is best-effort for ad-hoc
(unregistered) sites (site_uuid is None) and guaranteed for registered sites.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db import repository


class PersistenceAgent:
    async def save_readings(self, db: AsyncSession, site_uuid, readings: list[dict], source: str):
        if site_uuid is None or not readings:
            return 0
        rows = []
        for r in readings:
            try:
                ts = datetime.fromisoformat(r["timestamp"])
            except (KeyError, ValueError):
                continue
            rows.append(
                {
                    "ts": ts,
                    "ghi": r.get("ghi_w_m2", 0.0),
                    "dni": r.get("dni_w_m2", 0.0),
                    "dhi": r.get("dhi_w_m2", 0.0),
                    "temp": r.get("temperature_c", 0.0),
                    "cloud_cover": r.get("cloud_cover_percent", 0.0),
                    "wind": r.get("wind_speed_mps", 2.0),
                }
            )
        return await repository.save_readings(db, site_uuid, rows, source=source)

    async def save_forecast_point(self, db: AsyncSession, site_uuid, point: dict):
        if site_uuid is None:
            return 0
        try:
            rows = [
                {
                    "ts": datetime.fromisoformat(point["timestamp"]),
                    "predicted_kw": point["predicted_generation_mw"] * 1000,
                    "clearsky_kw": point.get("scheduled_generation_mw", 0.0) * 1000,
                    "confidence": point.get("confidence_score", 0.8),
                }
            ]
            return await repository.save_forecasts(db, site_uuid, rows)
        except Exception as exc:
            logger.warning(f"Forecast persist skipped: {exc}")
            return 0
