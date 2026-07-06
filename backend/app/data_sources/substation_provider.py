"""Substation / grid-location provider.

Collects substation locations from OpenStreetMap via the Overpass API
(tag power=substation), and supports manual CSV import. Every record carries its
`source_name`, `source_url` and a `source_confidence`. Coordinates are used exactly
as published - the provider never invents coordinates.

SOURCE: docs/SOURCE_REGISTRY.md#src-osm-substation-001 (SRC-OSM-SUBSTATION-001)
License: ODbL 1.0 - attribution "(c) OpenStreetMap contributors".
"""

from __future__ import annotations

import csv
import io

import httpx

from app.core.logging import logger
from app.data_sources.base_provider import TYPE_SUBSTATION, DataProvider, ProviderStatus

OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"
_HTTP_HEADERS = {
    "User-Agent": "SuryaGrid-AI/1.5 (solar DSM platform; substation import)",
    "Accept": "application/json",
}
SOURCE_ID = "SRC-OSM-SUBSTATION-001"
OSM_SOURCE_NAME = "OpenStreetMap (Overpass)"
OSM_SOURCE_URL = "https://www.openstreetmap.org"
OSM_DEFAULT_CONFIDENCE = 0.6  # OSM completeness varies by region
CSV_DEFAULT_CONFIDENCE = 1.0  # operator-provided data is authoritative

CSV_COLUMNS = [
    "name",
    "voltage_level",
    "operator",
    "latitude",
    "longitude",
    "district",
    "state",
    "country",
]


class SubstationProvider(DataProvider):
    name = "osm-substation"
    source_id = SOURCE_ID
    provider_type = TYPE_SUBSTATION

    def __init__(self, timeout_seconds: float = 60.0):
        self._timeout = timeout_seconds

    # ---- OpenStreetMap / Overpass --------------------------------------
    @staticmethod
    def _build_query(south: float, west: float, north: float, east: float) -> str:
        bbox = f"{south},{west},{north},{east}"
        return (
            "[out:json][timeout:60];"
            "("
            f'node["power"="substation"]({bbox});'
            f'way["power"="substation"]({bbox});'
            f'relation["power"="substation"]({bbox});'
            ");"
            "out center tags;"
        )

    async def fetch_bbox(self, south: float, west: float, north: float, east: float) -> list[dict]:
        """Fetch substations within a bounding box from Overpass."""
        query = self._build_query(south, west, north, east)
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, headers=_HTTP_HEADERS, follow_redirects=True
            ) as client:
                resp = await client.post(OVERPASS_ENDPOINT, data={"data": query})
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError as exc:
            logger.error(f"Overpass request failed: {exc}")
            raise RuntimeError(f"Overpass request failed: {exc}") from exc
        return self._parse_overpass(payload)

    async def fetch_around(self, latitude: float, longitude: float, radius_km: float) -> list[dict]:
        """Fetch substations within radius_km of a point (bbox approximation)."""
        # 1 degree latitude ~= 111 km; widen longitude by cos(lat).
        import math

        dlat = radius_km / 111.0
        dlon = radius_km / (111.0 * max(0.1, math.cos(math.radians(latitude))))
        return await self.fetch_bbox(
            south=latitude - dlat,
            west=longitude - dlon,
            north=latitude + dlat,
            east=longitude + dlon,
        )

    def _parse_overpass(self, payload: dict) -> list[dict]:
        records: list[dict] = []
        for el in payload.get("elements", []):
            lat = el.get("lat")
            lon = el.get("lon")
            if lat is None or lon is None:
                center = el.get("center") or {}
                lat, lon = center.get("lat"), center.get("lon")
            if lat is None or lon is None:
                continue  # never invent coordinates
            tags = el.get("tags", {})
            records.append(
                {
                    "name": tags.get("name") or f"Substation {el.get('id')}",
                    "voltage_level": tags.get("voltage"),
                    "operator": tags.get("operator"),
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "district": tags.get("addr:district"),
                    "state": tags.get("addr:state"),
                    "country": tags.get("addr:country"),
                    "source_name": OSM_SOURCE_NAME,
                    "source_url": OSM_SOURCE_URL,
                    "source_confidence": OSM_DEFAULT_CONFIDENCE,
                    "osm_id": el.get("id"),
                }
            )
        return records

    # ---- Manual CSV import ---------------------------------------------
    @staticmethod
    def parse_csv(text: str) -> list[dict]:
        """Parse an operator-provided substation CSV. Coordinates used as-is."""
        records: list[dict] = []
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            try:
                lat = float(row.get("latitude"))
                lon = float(row.get("longitude"))
            except (TypeError, ValueError):
                continue  # skip rows without valid coordinates; never invent
            records.append(
                {
                    "name": (row.get("name") or "").strip() or "Unnamed substation",
                    "voltage_level": (row.get("voltage_level") or "").strip() or None,
                    "operator": (row.get("operator") or "").strip() or None,
                    "latitude": lat,
                    "longitude": lon,
                    "district": (row.get("district") or "").strip() or None,
                    "state": (row.get("state") or "").strip() or None,
                    "country": (row.get("country") or "").strip() or None,
                    "source_name": (row.get("source_name") or "Manual CSV import").strip(),
                    "source_url": (row.get("source_url") or "").strip() or None,
                    "source_confidence": CSV_DEFAULT_CONFIDENCE,
                }
            )
        return records

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            source_id=self.source_id,
            provider_type=self.provider_type,
            available=True,
            detail="OpenStreetMap substations via Overpass (ODbL). CSV import supported.",
            mode="real",
            extra={"endpoint": OVERPASS_ENDPOINT, "license": "ODbL 1.0"},
        )
