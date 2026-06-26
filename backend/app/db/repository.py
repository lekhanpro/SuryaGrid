"""Async data-access layer over the database."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Consumer,
    Forecast,
    Owner,
    Reading,
    Settlement,
    Site,
    TrainingRun,
)


# ----- Sites -----
async def create_site(db: AsyncSession, data: dict) -> Site:
    site = Site(
        name=data["name"],
        latitude=data["latitude"],
        longitude=data["longitude"],
        timezone=data.get("timezone", "Asia/Kolkata"),
        capacity_mw=data["capacity_mw"],
        tilt=data.get("tilt", 20.0),
        azimuth=data.get("azimuth", 180.0),
        altitude=data.get("altitude", 0.0),
        allowed_dsm_threshold_percent=data.get("allowed_dsm_threshold_percent", 10.0),
        penalty_rate_per_mwh=data.get("penalty_rate_per_mwh", 12000.0),
        owner_id=data.get("owner_id"),
    )
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


async def list_sites(db: AsyncSession) -> list[Site]:
    result = await db.execute(select(Site).order_by(Site.created_at))
    return list(result.scalars().all())


async def get_site(db: AsyncSession, site_id: str | uuid.UUID) -> Site | None:
    try:
        sid = site_id if isinstance(site_id, uuid.UUID) else uuid.UUID(str(site_id))
    except (ValueError, AttributeError):
        return None
    result = await db.execute(select(Site).where(Site.id == sid))
    return result.scalar_one_or_none()


# ----- Readings -----
async def save_readings(db: AsyncSession, site_id: uuid.UUID, rows: list[dict], source: str) -> int:
    # Replace existing readings for idempotency on re-fetch.
    await db.execute(delete(Reading).where(Reading.site_id == site_id))
    objs = [
        Reading(
            site_id=site_id,
            ts=r["ts"],
            ghi=r["ghi"],
            dni=r.get("dni", 0.0),
            dhi=r.get("dhi", 0.0),
            temp=r["temp"],
            cloud_cover=r["cloud_cover"],
            wind=r.get("wind", 2.0),
            source=source,
        )
        for r in rows
    ]
    db.add_all(objs)
    await db.commit()
    return len(objs)


# ----- Forecasts -----
async def save_forecasts(db: AsyncSession, site_id: uuid.UUID, rows: list[dict]) -> int:
    await db.execute(delete(Forecast).where(Forecast.site_id == site_id))
    objs = [
        Forecast(
            site_id=site_id,
            ts=r["ts"],
            predicted_kw=r["predicted_kw"],
            clearsky_kw=r.get("clearsky_kw", 0.0),
            confidence=r.get("confidence", 0.8),
        )
        for r in rows
    ]
    db.add_all(objs)
    await db.commit()
    return len(objs)


# ----- Settlements -----
async def save_settlements(db: AsyncSession, site_id: uuid.UUID, rows: list[dict]) -> int:
    objs = [
        Settlement(
            site_id=site_id,
            window_start=r["window_start"],
            window_end=r.get("window_end"),
            target_kw=r["target_kw"],
            actual_kw=r["actual_kw"],
            penalty=r.get("penalty", 0.0),
            bonus=r.get("bonus", 0.0),
            discount=r.get("discount", 0.0),
            net_owner=r.get("net_owner", 0.0),
            penalty_rate=r.get("penalty_rate", 0.0),
            bonus_rate=r.get("bonus_rate", 0.0),
            discount_rate=r.get("discount_rate", 0.0),
        )
        for r in rows
    ]
    db.add_all(objs)
    await db.commit()
    return len(objs)


async def list_settlements(
    db: AsyncSession, site_id: uuid.UUID, limit: int = 200
) -> list[Settlement]:
    result = await db.execute(
        select(Settlement)
        .where(Settlement.site_id == site_id)
        .order_by(Settlement.window_start.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ----- Training runs -----
async def save_training_run(db: AsyncSession, data: dict) -> TrainingRun:
    run = TrainingRun(
        algorithm=data.get("algorithm", "REINFORCE"),
        episodes=data["episodes"],
        data_source=data.get("data_source", "open-meteo-archive"),
        best_reward=data["best_reward"],
        mean_reward=data.get("mean_reward", 0.0),
        final_rates=data.get("final_rates"),
        notes=data.get("notes"),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def list_training_runs(db: AsyncSession, limit: int = 20) -> list[TrainingRun]:
    result = await db.execute(
        select(TrainingRun).order_by(TrainingRun.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


# ----- Owners / Consumers -----
async def create_owner(db: AsyncSession, name: str, email: str | None = None) -> Owner:
    owner = Owner(name=name, email=email)
    db.add(owner)
    await db.commit()
    await db.refresh(owner)
    return owner


async def create_consumer(
    db: AsyncSession, name: str, profile: str = "commercial", base_load_kw: float = 50.0
) -> Consumer:
    consumer = Consumer(name=name, profile=profile, base_load_kw=base_load_kw)
    db.add(consumer)
    await db.commit()
    await db.refresh(consumer)
    return consumer


async def counts(db: AsyncSession) -> dict:
    out = {}
    for label, model in [
        ("sites", Site),
        ("readings", Reading),
        ("forecasts", Forecast),
        ("settlements", Settlement),
        ("training_runs", TrainingRun),
    ]:
        result = await db.execute(select(func.count()).select_from(model))
        out[label] = int(result.scalar() or 0)
    return out
