"""Background real-time ingestion scheduler (opt-in).

When SCHEDULER_ENABLED is true, polls the current weather for every registered
site on a fixed interval and persists a Reading. This is the real-time data
loop; it degrades to a no-op when disabled or when no provider is reachable.
"""

from __future__ import annotations

from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.agents.api_agent import APIAgent
from app.config import get_settings
from app.core.logging import logger
from app.db import repository
from app.db.database import AsyncSessionLocal

_scheduler: AsyncIOScheduler | None = None
_api_agent = APIAgent()


async def ingest_all_sites() -> int:
    """Fetch current conditions for every site and persist one reading each."""
    ingested = 0
    async with AsyncSessionLocal() as db:
        sites = await repository.list_sites(db)
        for site in sites:
            try:
                provider = _api_agent._providers[0][0]
                cur = await provider.fetch_current(site.latitude, site.longitude, site.timezone)
                if not cur.get("timestamp"):
                    continue
                ts = datetime.fromisoformat(cur["timestamp"])
                await repository.save_readings(
                    db,
                    site.id,
                    [
                        {
                            "ts": ts,
                            "ghi": cur["ghi_w_m2"],
                            "dni": cur["dni_w_m2"],
                            "dhi": cur["dhi_w_m2"],
                            "temp": cur["temperature_c"],
                            "cloud_cover": cur["cloud_cover_percent"],
                            "wind": cur["wind_speed_mps"],
                        }
                    ],
                    source="open-meteo-current",
                )
                ingested += 1
            except Exception as exc:  # noqa: BLE001 - best-effort polling
                logger.warning(f"Real-time ingest failed for {site.name}: {exc}")
    if ingested:
        logger.info(f"Real-time ingest: {ingested} site(s) updated")
    return ingested


def start_scheduler() -> None:
    global _scheduler
    settings = get_settings()
    if not settings.SCHEDULER_ENABLED:
        return
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        ingest_all_sites,
        "interval",
        minutes=settings.INGEST_INTERVAL_MINUTES,
        id="ingest_current",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(f"Real-time scheduler started (every {settings.INGEST_INTERVAL_MINUTES} min)")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
