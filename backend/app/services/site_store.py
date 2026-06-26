"""In-memory site registry.

Holds solar site configuration for the running instance. Models for PostgreSQL
persistence exist in app.db.models and can back this store in a clustered
deployment; the in-memory store keeps the system runnable without a database.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.agents.forecast_agent import SiteConfig
from app.core.exceptions import NotFoundError


class SiteStore:
    def __init__(self):
        self._sites: dict[str, dict] = {}

    def create(self, data: dict) -> dict:
        site_id = str(uuid.uuid4())
        record = {
            "id": site_id,
            "name": data["name"],
            "latitude": data["latitude"],
            "longitude": data["longitude"],
            "timezone": data.get("timezone", "Asia/Kolkata"),
            "capacity_mw": data["capacity_mw"],
            "tilt": data.get("tilt", 20.0),
            "azimuth": data.get("azimuth", 180.0),
            "altitude": data.get("altitude", 0.0),
            "allowed_dsm_threshold_percent": data.get("allowed_dsm_threshold_percent", 10.0),
            "penalty_rate_per_mwh": data.get("penalty_rate_per_mwh", 12000.0),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._sites[site_id] = record
        return record

    def list(self) -> list[dict]:
        return list(self._sites.values())

    def get(self, site_id: str) -> dict:
        site = self._sites.get(site_id)
        if site is None:
            raise NotFoundError(f"Site {site_id} not found")
        return site

    def to_config(self, site: dict) -> SiteConfig:
        return SiteConfig(
            latitude=site["latitude"],
            longitude=site["longitude"],
            timezone=site["timezone"],
            capacity_mw=site["capacity_mw"],
            tilt=site["tilt"],
            azimuth=site["azimuth"],
            altitude=site["altitude"],
        )


site_store = SiteStore()
