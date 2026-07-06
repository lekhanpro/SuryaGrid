"""Async DB access for DSM rule profiles, bands, and results."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import DSMResult, DSMRuleBand, DSMRuleProfile
from app.dsm.base_rules import RuleBand, RuleProfile


async def count_profiles(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(DSMRuleProfile))
    return int(result.scalar() or 0)


async def list_profiles(db: AsyncSession) -> list[DSMRuleProfile]:
    result = await db.execute(
        select(DSMRuleProfile)
        .options(selectinload(DSMRuleProfile.bands))
        .order_by(DSMRuleProfile.name)
    )
    return list(result.scalars().all())


async def get_profile(db: AsyncSession, id_or_name: str) -> DSMRuleProfile | None:
    query = select(DSMRuleProfile).options(selectinload(DSMRuleProfile.bands))
    try:
        pid = uuid.UUID(str(id_or_name))
        result = await db.execute(query.where(DSMRuleProfile.id == pid))
    except (ValueError, AttributeError):
        result = await db.execute(query.where(DSMRuleProfile.name == id_or_name))
    return result.scalar_one_or_none()


async def create_profile(db: AsyncSession, profile: RuleProfile) -> DSMRuleProfile:
    row = DSMRuleProfile(
        name=profile.name,
        region=profile.region,
        regulator=profile.regulator,
        denominator=profile.denominator,
        tolerance_percent=profile.tolerance_percent,
        time_block_minutes=profile.time_block_minutes,
        source_name=profile.source_name,
        source_url=profile.source_url,
        source_status=profile.source_status,
        effective_from=profile.effective_from,
        effective_to=profile.effective_to,
        notes=profile.notes,
    )
    row.bands = [
        DSMRuleBand(
            min_deviation_percent=b.min_deviation_percent,
            max_deviation_percent=b.max_deviation_percent,
            direction=b.direction,
            charge_formula=b.charge_formula,
            charge_rate=b.charge_rate,
            unit=b.unit,
            notes=b.notes,
            source_reference=b.source_reference,
        )
        for b in profile.bands
    ]
    db.add(row)
    await db.commit()
    # reload with bands
    return await get_profile(db, str(row.id))


async def seed_default_profiles(db: AsyncSession) -> int:
    """Insert the default profiles if they are not present (idempotent by name)."""
    from app.dsm.india_dsm_rules import default_profiles

    existing = {p.name for p in await list_profiles(db)}
    created = 0
    for profile in default_profiles():
        if profile.name in existing:
            continue
        await create_profile(db, profile)
        created += 1
    return created


def to_rule_profile(row: DSMRuleProfile) -> RuleProfile:
    """Hydrate an engine RuleProfile dataclass from a DB row (bands eager-loaded)."""
    return RuleProfile(
        id=str(row.id),
        name=row.name,
        region=row.region,
        regulator=row.regulator,
        denominator=row.denominator,
        tolerance_percent=row.tolerance_percent,
        time_block_minutes=row.time_block_minutes,
        source_name=row.source_name,
        source_url=row.source_url,
        source_status=row.source_status,
        effective_from=row.effective_from,
        effective_to=row.effective_to,
        notes=row.notes or "",
        bands=[
            RuleBand(
                min_deviation_percent=b.min_deviation_percent,
                max_deviation_percent=b.max_deviation_percent,
                charge_rate=b.charge_rate,
                unit=b.unit,
                direction=b.direction,
                charge_formula=b.charge_formula or "",
                notes=b.notes or "",
                source_reference=b.source_reference or "",
            )
            for b in row.bands
        ],
    )


async def save_result(db: AsyncSession, site_uuid, profile_uuid, result: dict) -> DSMResult:
    row = DSMResult(
        site_id=site_uuid,
        profile_id=profile_uuid,
        scheduled_generation_mw=result.get("scheduled_generation_mw", 0.0),
        predicted_generation_mw=result.get("measured_generation_mw", 0.0),
        actual_generation_mw=result.get("actual_generation_mw"),
        installed_capacity_mw=result.get("installed_capacity_mw", 0.0),
        deviation_mw=result.get("deviation_mw", 0.0),
        deviation_percent=result.get("deviation_percent", 0.0),
        deviation_direction=result.get("deviation_direction", "WITHIN_LIMIT"),
        dsm_band=result.get("dsm_band"),
        penalty_status=result.get("penalty_status", "NO_PENALTY"),
        charge_rate=result.get("charge_rate", 0.0),
        estimated_dsm_charge=result.get("estimated_dsm_charge", 0.0),
        rule_source=str((result.get("rule_source") or {}).get("name") or ""),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
