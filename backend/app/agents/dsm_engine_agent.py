"""DSMEngineAgent - advanced DSM coordination (resolve profile, evaluate, persist).

Coordinator over app.dsm (engine + repository). Resolves a rule profile by
id/name, then region/regulator, then falls back to the generic configurable
profile. See docs/DSM_RULE_SOURCES.md.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.dsm import dsm_repository
from app.dsm.base_rules import RuleProfile
from app.dsm.configurable_rules import generic_configurable_profile
from app.dsm.dsm_engine import DSMEngine


class DSMEngineAgent:
    def __init__(self):
        self.engine = DSMEngine()

    async def resolve_profile(
        self,
        db: AsyncSession,
        rule_profile_id: str | None = None,
        region: str | None = None,
        regulator: str | None = None,
    ) -> RuleProfile:
        if await dsm_repository.count_profiles(db) == 0:
            await dsm_repository.seed_default_profiles(db)

        if rule_profile_id:
            row = await dsm_repository.get_profile(db, rule_profile_id)
            if row is not None:
                return dsm_repository.to_rule_profile(row)

        if region or regulator:
            for row in await dsm_repository.list_profiles(db):
                if regulator and row.regulator == regulator:
                    return dsm_repository.to_rule_profile(row)
                if region and row.region == region:
                    return dsm_repository.to_rule_profile(row)

        row = await dsm_repository.get_profile(db, "generic-configurable")
        return dsm_repository.to_rule_profile(row) if row else generic_configurable_profile()

    def evaluate(
        self,
        profile: RuleProfile,
        scheduled_mw: float,
        measured_mw: float,
        installed_capacity_mw: float,
        interval_hours: float | None = None,
    ) -> dict:
        return self.engine.evaluate(
            profile, scheduled_mw, measured_mw, installed_capacity_mw, interval_hours
        )

    async def persist(self, db: AsyncSession, site_uuid, profile: RuleProfile, result: dict):
        profile_uuid = None
        if profile.id:
            try:
                profile_uuid = uuid.UUID(profile.id)
            except (ValueError, TypeError):
                profile_uuid = None
        return await dsm_repository.save_result(db, site_uuid, profile_uuid, result)
