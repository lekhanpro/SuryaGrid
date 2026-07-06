"""LocationDataAgent - collect and expose all discoverable data locations.

Manages: solar-site locations, weather grid points, substations, provider-available
locations, and nearest-substation mapping. Substations come from OpenStreetMap
(Overpass) or operator CSV; every record keeps its source and confidence, and
coordinates are stored exactly as published (never invented).

SOURCE: docs/LOCATION_AND_SUBSTATION_DATA.md, docs/SOURCE_REGISTRY.md#src-osm-substation-001
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_sources.kaggle_solar_provider import KaggleSolarProvider
from app.data_sources.substation_provider import SubstationProvider
from app.db import repository
from app.ml import model_registry


def _serialize_substation(s) -> dict:
    return {
        "id": str(s.id),
        "name": s.name,
        "voltage_level": s.voltage_level,
        "operator": s.operator,
        "latitude": s.latitude,
        "longitude": s.longitude,
        "district": s.district,
        "state": s.state,
        "country": s.country,
        "source_name": s.source_name,
        "source_url": s.source_url,
        "source_confidence": s.source_confidence,
    }


class LocationDataAgent:
    def __init__(self, provider: SubstationProvider | None = None):
        self.provider = provider or SubstationProvider()

    # ---- imports --------------------------------------------------------
    async def import_substations_osm(
        self, db: AsyncSession, latitude: float, longitude: float, radius_km: float = 25.0
    ) -> dict:
        records = await self.provider.fetch_around(latitude, longitude, radius_km)
        inserted = await repository.create_substations(db, records)
        return {
            "source": "OpenStreetMap (Overpass)",
            "fetched": len(records),
            "inserted": inserted,
            "radius_km": radius_km,
            "center": {"latitude": latitude, "longitude": longitude},
        }

    async def import_substations_csv(self, db: AsyncSession, csv_text: str) -> dict:
        records = self.provider.parse_csv(csv_text)
        inserted = await repository.create_substations(db, records)
        return {"source": "Manual CSV import", "parsed": len(records), "inserted": inserted}

    # ---- nearest --------------------------------------------------------
    async def nearest_for_site(
        self, db: AsyncSession, site_id: str, latitude: float, longitude: float
    ) -> dict:
        site = await repository.get_site(db, site_id)
        if site is not None:
            latitude, longitude = site.latitude, site.longitude
        sub, distance = await repository.nearest_substation(db, latitude, longitude)
        if sub is None:
            return {
                "site_id": site_id,
                "nearest_substation": None,
                "detail": "No substations imported. Import from OSM or CSV first.",
            }
        if site is not None:
            await repository.upsert_site_substation(db, site.id, sub.id, distance)
        result = _serialize_substation(sub)
        result["distance_km"] = round(distance, 3)
        return {"site_id": site_id, "nearest_substation": result}

    # ---- discovery ------------------------------------------------------
    async def available_locations(self, db: AsyncSession) -> dict:
        from app.data.karnataka_sites import KARNATAKA_SITES

        sites = await repository.list_sites(db)
        subs = await repository.list_substations(db)
        wx = await repository.list_weather_provider_locations(db)
        return {
            "sites": [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "latitude": s.latitude,
                    "longitude": s.longitude,
                    "capacity_mw": s.capacity_mw,
                }
                for s in sites
            ],
            "site_registry": [
                {
                    "name": e["name"],
                    "latitude": e["latitude"],
                    "longitude": e["longitude"],
                    "capacity_mw": e["capacity_mw"],
                    "region": e.get("region"),
                }
                for e in KARNATAKA_SITES
            ],
            "substations": [_serialize_substation(s) for s in subs],
            "weather_provider_locations": [
                {"provider": w.provider, "latitude": w.latitude, "longitude": w.longitude}
                for w in wx
            ],
            "weather_coverage": "global (Open-Meteo grid; any coordinate is queryable)",
            "counts": {
                "registered_sites": len(sites),
                "registry_sites": len(KARNATAKA_SITES),
                "substations": len(subs),
                "weather_provider_locations": len(wx),
            },
        }

    async def data_coverage(
        self, db: AsyncSession, site_id: str, latitude: float, longitude: float
    ) -> dict:
        site = await repository.get_site(db, site_id)
        region = None
        if site is not None:
            latitude, longitude = site.latitude, site.longitude

        sub, distance = await repository.nearest_substation(db, latitude, longitude)
        nearest = None
        if sub is not None:
            nearest = {
                "name": sub.name,
                "distance_km": round(distance, 3),
                "source": sub.source_name,
            }

        return {
            "site_id": site_id,
            "latitude": latitude,
            "longitude": longitude,
            "weather_forecast_available": True,
            "weather_provider": "open-meteo",
            "historical_kaggle_coverage": KaggleSolarProvider().is_loaded(),
            "nearest_substation_available": sub is not None,
            "nearest_substation": nearest,
            "dsm_rule_profile_available": await self._dsm_profile_available(db, region),
            "model_available": model_registry.is_trained(),
        }

    @staticmethod
    async def _dsm_profile_available(db: AsyncSession, region: str | None) -> bool:
        try:
            from app.dsm import dsm_repository

            return await dsm_repository.count_profiles(db) > 0
        except Exception:
            return False
