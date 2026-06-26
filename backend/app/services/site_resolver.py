"""Resolve a SiteConfig from the database, with query-param fallback.

Routes accept a site_id. If it matches a registered site, that site's stored
config and DSM settings are used. Otherwise an ad-hoc config is built from
query parameters so any location works without pre-registering a site.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.forecast_agent import SiteConfig
from app.db import repository


@dataclass(slots=True)
class ResolvedSite:
    config: SiteConfig
    threshold_percent: float
    penalty_rate_per_mwh: float
    site_uuid: object | None  # uuid.UUID when persisted, else None


async def resolve_site(
    db: AsyncSession,
    site_id: str,
    latitude: float,
    longitude: float,
    timezone: str,
    capacity_mw: float,
    tilt: float,
    azimuth: float,
) -> ResolvedSite:
    site = await repository.get_site(db, site_id)
    if site is not None:
        return ResolvedSite(
            config=SiteConfig(
                latitude=site.latitude,
                longitude=site.longitude,
                timezone=site.timezone,
                capacity_mw=site.capacity_mw,
                tilt=site.tilt,
                azimuth=site.azimuth,
                altitude=site.altitude,
            ),
            threshold_percent=site.allowed_dsm_threshold_percent,
            penalty_rate_per_mwh=site.penalty_rate_per_mwh,
            site_uuid=site.id,
        )

    return ResolvedSite(
        config=SiteConfig(
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            capacity_mw=capacity_mw,
            tilt=tilt,
            azimuth=azimuth,
        ),
        threshold_percent=10.0,
        penalty_rate_per_mwh=12000.0,
        site_uuid=None,
    )
