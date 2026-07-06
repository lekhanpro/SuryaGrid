"""Async data-access layer over the database."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Consumer,
    Forecast,
    Location,
    Owner,
    Reading,
    Settlement,
    Site,
    SiteSubstationMap,
    Substation,
    TrainingRun,
    WeatherProviderLocation,
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


# ----- Substations -----
async def create_substations(db: AsyncSession, records: list[dict]) -> int:
    """Insert substations, skipping duplicates by osm_id (when present)."""
    existing_osm = set()
    result = await db.execute(select(Substation.osm_id).where(Substation.osm_id.isnot(None)))
    existing_osm = {r for (r,) in result.all()}

    objs = []
    seen_osm: set[str] = set()
    for r in records:
        osm_id = r.get("osm_id")
        if osm_id is not None:
            osm_id = str(osm_id)
            if osm_id in existing_osm or osm_id in seen_osm:
                continue
            seen_osm.add(osm_id)
        objs.append(
            Substation(
                name=r.get("name") or "Unnamed substation",
                voltage_level=r.get("voltage_level"),
                operator=r.get("operator"),
                latitude=r["latitude"],
                longitude=r["longitude"],
                district=r.get("district"),
                state=r.get("state"),
                country=r.get("country"),
                source_name=r.get("source_name") or "unknown",
                source_url=r.get("source_url"),
                source_confidence=r.get("source_confidence", 0.6),
                osm_id=osm_id,
            )
        )
    db.add_all(objs)
    await db.commit()
    return len(objs)


async def list_substations(db: AsyncSession, limit: int = 500) -> list[Substation]:
    result = await db.execute(select(Substation).order_by(Substation.name).limit(limit))
    return list(result.scalars().all())


async def count_substations(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(Substation))
    return int(result.scalar() or 0)


async def nearest_substation(db: AsyncSession, latitude: float, longitude: float):
    """Return (Substation, distance_km) nearest to a point, or (None, None)."""
    from app.utils.geo import haversine_km

    result = await db.execute(select(Substation))
    subs = list(result.scalars().all())
    if not subs:
        return None, None
    best, best_d = None, None
    for s in subs:
        d = haversine_km(latitude, longitude, s.latitude, s.longitude)
        if best_d is None or d < best_d:
            best, best_d = s, d
    return best, best_d


async def upsert_site_substation(
    db: AsyncSession, site_id: uuid.UUID, substation_id: uuid.UUID, distance_km: float
) -> SiteSubstationMap:
    await db.execute(delete(SiteSubstationMap).where(SiteSubstationMap.site_id == site_id))
    mapping = SiteSubstationMap(
        site_id=site_id, substation_id=substation_id, distance_km=distance_km
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    return mapping


# ----- Locations -----
async def create_location(db: AsyncSession, data: dict) -> Location:
    loc = Location(
        name=data["name"],
        location_type=data.get("location_type", "site"),
        latitude=data["latitude"],
        longitude=data["longitude"],
        source_name=data.get("source_name"),
        source_confidence=data.get("source_confidence", 1.0),
    )
    db.add(loc)
    await db.commit()
    await db.refresh(loc)
    return loc


async def list_locations(db: AsyncSession, limit: int = 500) -> list[Location]:
    result = await db.execute(select(Location).order_by(Location.name).limit(limit))
    return list(result.scalars().all())


# ----- Weather provider locations -----
async def create_weather_provider_location(db: AsyncSession, data: dict) -> WeatherProviderLocation:
    loc = WeatherProviderLocation(
        provider=data.get("provider", "open-meteo"),
        label=data.get("label"),
        latitude=data["latitude"],
        longitude=data["longitude"],
    )
    db.add(loc)
    await db.commit()
    await db.refresh(loc)
    return loc


async def list_weather_provider_locations(
    db: AsyncSession, limit: int = 500
) -> list[WeatherProviderLocation]:
    result = await db.execute(select(WeatherProviderLocation).limit(limit))
    return list(result.scalars().all())
