"""SubstationContextService - load real substations and build SubstationContext.

Single source of truth for turning a selected substation (from the dropdown) into a
fully-populated :class:`SubstationContext`. Reads the real OpenStreetMap-derived
parquet (``bengaluru_substations_cleaned.parquet``, 344 rows). Honesty rules enforced
here:

  * Missing values (``None``, ``NaN``, or the strings "nan"/"none"/"null"/"") are
    coerced to ``None`` - never guessed or defaulted to a plausible number.
  * ``capacity_mva`` and ``district`` are entirely null in OSM, so their status is
    ``NOT_AVAILABLE`` and downstream capacity/loading calculations are blocked.
  * Every context carries its provenance label (``REAL_BENGALURU``) and a list of
    human-readable ``limitation_notes``.
"""

from __future__ import annotations

import math

from app.ml import provenance as prov
from app.schemas.substation_context import SubstationContext

SUBSTATION_PARQUET = "bengaluru_substations_cleaned.parquet"
_MISSING_STRINGS = {"nan", "none", "null", "", "na", "n/a"}
# Real fields that OSM frequently omits; used to compute honest missing_fields.
_OPTIONAL_FIELDS = ("operator", "voltage_kv", "capacity_mva", "district")


def _clean(value):
    """Return ``None`` for any form of missing value, else the value unchanged."""
    if value is None:
        return None
    # float NaN
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        if value.strip().lower() in _MISSING_STRINGS:
            return None
        return value.strip()
    return value


def _clean_float(value) -> float | None:
    v = _clean(value)
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _clean_str(value) -> str | None:
    v = _clean(value)
    return None if v is None else str(v)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 3)


class SubstationContextService:
    """Loads the substation parquet (mtime-cached) and builds SubstationContext objects."""

    def __init__(self, parquet_name: str = SUBSTATION_PARQUET):
        self._parquet_name = parquet_name
        self._rows: dict[str, dict] | None = None
        self._order: list[str] = []
        self._mtime: float | None = None

    # ---- loading --------------------------------------------------------
    def _path(self):
        return prov.ml_data_dir() / self._parquet_name

    def _ensure_loaded(self) -> None:
        path = self._path()
        if not path.exists():
            self._rows = {}
            self._order = []
            self._mtime = None
            return
        mtime = path.stat().st_mtime
        if self._rows is not None and self._mtime == mtime:
            return
        import pandas as pd

        df = pd.read_parquet(path)
        rows: dict[str, dict] = {}
        order: list[str] = []
        for rec in df.to_dict("records"):
            sid = _clean_str(rec.get("substation_id"))
            if not sid:
                continue
            rows[sid] = rec
            order.append(sid)
        self._rows = rows
        self._order = order
        self._mtime = mtime

    @property
    def available(self) -> bool:
        self._ensure_loaded()
        return bool(self._rows)

    def count(self) -> int:
        self._ensure_loaded()
        return len(self._rows or {})

    # ---- context building ----------------------------------------------
    def _parse_missing_fields(self, raw, cleaned: dict) -> list[str]:
        """Union of the dataset's missing_fields column and fields we found empty."""
        declared: list[str] = []
        raw = _clean(raw)
        if isinstance(raw, str):
            declared = [f.strip() for f in raw.split(",") if f.strip()]
        computed = [f for f in _OPTIONAL_FIELDS if cleaned.get(f) is None]
        # preserve order, dedupe
        out: list[str] = []
        for f in [*computed, *declared]:
            if f not in out:
                out.append(f)
        return out

    def _display_label(self, name: str | None, sid: str, voltage_kv: float | None) -> str:
        base = name or sid
        volt = f"{voltage_kv:g} kV" if voltage_kv is not None else "voltage unknown"
        return f"{base} - {volt}"

    def _build(
        self, rec: dict, site_lat: float | None, site_lon: float | None
    ) -> SubstationContext:
        cleaned = {
            "substation_id": _clean_str(rec.get("substation_id")),
            "name": _clean_str(rec.get("name")),
            "latitude": _clean_float(rec.get("latitude")),
            "longitude": _clean_float(rec.get("longitude")),
            "operator": _clean_str(rec.get("operator")),
            "voltage_kv": _clean_float(rec.get("voltage_kv")),
            "capacity_mva": _clean_float(rec.get("capacity_mva")),
            "district": _clean_str(rec.get("district")),
            "state": _clean_str(rec.get("state")),
            "source": _clean_str(rec.get("source")),
            "source_url": _clean_str(rec.get("source_url")),
            "source_label": _clean_str(rec.get("source_label")) or prov.REAL_BENGALURU,
            "reliability_score": _clean_float(rec.get("reliability_score")),
            "data_geography": _clean_str(rec.get("data_geography")),
            "ingestion_time": _clean_str(rec.get("ingestion_time")),
        }
        missing = self._parse_missing_fields(rec.get("missing_fields"), cleaned)

        lat, lon = cleaned["latitude"], cleaned["longitude"]
        distance = None
        if site_lat is not None and site_lon is not None and lat is not None and lon is not None:
            distance = _haversine_km(site_lat, site_lon, lat, lon)

        # Honest status flags -------------------------------------------------
        source_status = cleaned["source_label"]
        capacity_status = (
            source_status if cleaned["capacity_mva"] is not None else prov.NOT_AVAILABLE
        )
        voltage_status = source_status if cleaned["voltage_kv"] is not None else prov.NOT_AVAILABLE

        notes = self._limitation_notes(cleaned)

        return SubstationContext(
            **cleaned,
            missing_fields=missing,
            display_label=self._display_label(
                cleaned["name"], cleaned["substation_id"], cleaned["voltage_kv"]
            ),
            distance_from_site_km=distance,
            nearest_weather_location=(
                {
                    "latitude": lat,
                    "longitude": lon,
                    "note": "Open-Meteo is queried at the substation's own coordinates.",
                }
                if lat is not None and lon is not None
                else None
            ),
            weather_source=f"Open-Meteo @ ({lat}, {lon}) [{prov.REAL_COORDINATE_BASED}]",
            solar_source=f"solar_forecast_model.pkl [{prov.REAL_BENGALURU}]",
            tariff_region="Karnataka (KERC)",
            source_status=source_status,
            capacity_status=capacity_status,
            voltage_status=voltage_status,
            load_data_status=prov.NOT_AVAILABLE,
            tariff_status=prov.NEEDS_OFFICIAL_SOURCE,
            limitation_notes=notes,
        )

    @staticmethod
    def _limitation_notes(cleaned: dict) -> list[str]:
        notes: list[str] = []
        if cleaned["capacity_mva"] is None:
            notes.append(
                "Substation capacity (MVA) is unavailable from OpenStreetMap; "
                "substation-loading and capacity-based DSM are disabled "
                "(NEEDS_OFFICIAL_SOURCE: KPTCL/BESCOM)."
            )
        if cleaned["voltage_kv"] is None:
            notes.append(
                "Voltage level unavailable for this substation; "
                "voltage-band optimisation is disabled."
            )
        if cleaned["operator"] is None:
            notes.append("Operator is unknown for this substation (not published in OSM).")
        notes.append(
            "No substation-level real-time load/generation telemetry exists; plant "
            "generation is ESTIMATED from forecast irradiance, never measured."
        )
        notes.append(
            "No official KERC/CERC rupee tariff is parsed; DSM output is framework-only "
            "(deviation bands, no rupee charges)."
        )
        return notes

    # ---- public API -----------------------------------------------------
    def get_context(
        self,
        substation_id: str,
        site_latitude: float | None = None,
        site_longitude: float | None = None,
    ) -> SubstationContext | None:
        """Return the SubstationContext for ``substation_id`` or ``None`` if unknown."""
        self._ensure_loaded()
        rec = (self._rows or {}).get(substation_id)
        if rec is None:
            return None
        return self._build(rec, site_latitude, site_longitude)

    def list_catalog(self, limit: int = 1000) -> list[dict]:
        """Dropdown-ready list: id + display_label + coords + honesty hints."""
        self._ensure_loaded()
        out: list[dict] = []
        for sid in self._order:
            rec = self._rows[sid]
            voltage = _clean_float(rec.get("voltage_kv"))
            name = _clean_str(rec.get("name"))
            out.append(
                {
                    "substation_id": sid,
                    "display_label": self._display_label(name, sid, voltage),
                    "name": name,
                    "latitude": _clean_float(rec.get("latitude")),
                    "longitude": _clean_float(rec.get("longitude")),
                    "voltage_kv": voltage,
                    "capacity_mva": _clean_float(rec.get("capacity_mva")),  # always None (honest)
                    "reliability_score": _clean_float(rec.get("reliability_score")),
                    "source_label": _clean_str(rec.get("source_label")) or prov.REAL_BENGALURU,
                }
            )
        # Highest reliability first, then stable by label.
        out.sort(key=lambda r: (-(r["reliability_score"] or 0.0), r["display_label"]))
        return out[:limit]


# Module-level singleton (mtime-cached) reused by the router + orchestrator.
_service = SubstationContextService()


def get_substation_context_service() -> SubstationContextService:
    return _service
