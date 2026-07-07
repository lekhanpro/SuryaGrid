"""SubstationContext - the central context object for the substation-driven workflow.

When a substation is selected from the dropdown, it becomes a single, typed context
object that flows through every agent: weather -> solar irradiance -> cloud risk ->
generation timeline -> DSM -> orchestrator. Nothing is ever fabricated:

  * A missing real field (capacity_mva, voltage_kv, operator, district) stays ``None``
    and its ``*_status`` becomes ``NOT_AVAILABLE`` - never a guessed number.
  * ``source_status`` / provenance labels travel with the object so every downstream
    number can be traced to REAL_BENGALURU / REAL_COORDINATE_BASED / ESTIMATED_FROM_REAL.

The real substation records come from OpenStreetMap (Overpass), 344 rows in
``backend/data/ml/bengaluru_substations_cleaned.parquet``. capacity_mva and district
are entirely null in that source, so capacity/loading calculations are honestly blocked
downstream (see ``limitation_notes``).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.ml import provenance as prov


class SubstationContext(BaseModel):
    """Typed, honesty-preserving context for one substation.

    Only ``substation_id``, ``latitude`` and ``longitude`` are guaranteed present
    (every OSM row has them). Everything else may be ``None`` and carries a status.
    """

    model_config = {"extra": "ignore"}

    # ---- identity & geography (always present in the OSM source) ----------
    substation_id: str
    name: str | None = None
    latitude: float
    longitude: float

    # ---- attributes that may be missing in the real source ---------------
    operator: str | None = None
    voltage_kv: float | None = None
    capacity_mva: float | None = None  # ALWAYS null in OSM -> never fabricated
    district: str | None = None
    state: str | None = None

    # ---- provenance carried from the dataset -----------------------------
    source: str | None = None
    source_url: str | None = None
    source_label: str | None = None  # e.g. REAL_BENGALURU
    reliability_score: float | None = None
    missing_fields: list[str] = Field(default_factory=list)
    data_geography: str | None = None
    ingestion_time: str | None = None

    # ---- derived workflow context ----------------------------------------
    display_label: str = ""  # dropdown label, e.g. "Substation 123 - 66 kV (Bengaluru)"
    distance_from_site_km: float | None = None
    nearest_weather_location: dict | None = None  # {latitude, longitude, note}
    weather_source: str | None = None  # Open-Meteo @ coords [REAL_COORDINATE_BASED]
    solar_source: str | None = None  # trained model file + label
    tariff_region: str | None = None  # e.g. "Karnataka (KERC)"

    # ---- honest per-field status flags -----------------------------------
    source_status: str = prov.NOT_AVAILABLE
    capacity_status: str = prov.NOT_AVAILABLE
    voltage_status: str = prov.NOT_AVAILABLE
    load_data_status: str = prov.NOT_AVAILABLE
    tariff_status: str = prov.NEEDS_OFFICIAL_SOURCE

    # ---- human-readable honesty notes ------------------------------------
    limitation_notes: list[str] = Field(default_factory=list)

    # ---- convenience -----------------------------------------------------
    @property
    def has_capacity(self) -> bool:
        return self.capacity_mva is not None

    @property
    def has_voltage(self) -> bool:
        return self.voltage_kv is not None
