"""Database models for Suryagrid AI.

Portable across SQLite (default, local) and PostgreSQL/TimescaleDB (production)
via the GUID type. Mirrors the ER diagram in PROJECT_PLAN.md section 8.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.db.types import GUID


class Owner(Base):
    __tablename__ = "owners"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sites: Mapped[list["Site"]] = relationship(back_populates="owner")


class Consumer(Base):
    __tablename__ = "consumers"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile: Mapped[str] = mapped_column(String(50), default="commercial")
    base_load_kw: Mapped[float] = mapped_column(Float, default=50.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    settlements: Mapped[list["Settlement"]] = relationship(back_populates="consumer")


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("owners.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    capacity_mw: Mapped[float] = mapped_column(Float, nullable=False)
    tilt: Mapped[float] = mapped_column(Float, default=20.0)
    azimuth: Mapped[float] = mapped_column(Float, default=180.0)
    altitude: Mapped[float] = mapped_column(Float, default=0.0)
    allowed_dsm_threshold_percent: Mapped[float] = mapped_column(Float, default=10.0)
    penalty_rate_per_mwh: Mapped[float] = mapped_column(Float, default=12000.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["Owner"] = relationship(back_populates="sites")
    readings: Mapped[list["Reading"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )
    forecasts: Mapped[list["Forecast"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )
    settlements: Mapped[list["Settlement"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )


class Reading(Base):
    __tablename__ = "readings"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("sites.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ghi: Mapped[float] = mapped_column(Float, nullable=False)
    dni: Mapped[float] = mapped_column(Float, default=0.0)
    dhi: Mapped[float] = mapped_column(Float, default=0.0)
    temp: Mapped[float] = mapped_column(Float, nullable=False)
    cloud_cover: Mapped[float] = mapped_column(Float, nullable=False)
    wind: Mapped[float] = mapped_column(Float, default=2.0)
    source: Mapped[str] = mapped_column(String(50), default="open-meteo")
    quality_flag: Mapped[int] = mapped_column(Integer, default=1)

    site: Mapped["Site"] = relationship(back_populates="readings")


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("sites.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    predicted_kw: Mapped[float] = mapped_column(Float, nullable=False)
    clearsky_kw: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    site: Mapped["Site"] = relationship(back_populates="forecasts")


class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("sites.id"), nullable=False)
    consumer_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("consumers.id"), nullable=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    target_kw: Mapped[float] = mapped_column(Float, nullable=False)
    actual_kw: Mapped[float] = mapped_column(Float, nullable=False)
    penalty: Mapped[float] = mapped_column(Float, default=0.0)
    bonus: Mapped[float] = mapped_column(Float, default=0.0)
    discount: Mapped[float] = mapped_column(Float, default=0.0)
    net_owner: Mapped[float] = mapped_column(Float, default=0.0)
    penalty_rate: Mapped[float] = mapped_column(Float, default=0.0)
    bonus_rate: Mapped[float] = mapped_column(Float, default=0.0)
    discount_rate: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    site: Mapped["Site"] = relationship(back_populates="settlements")
    consumer: Mapped["Consumer"] = relationship(back_populates="settlements")


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    algorithm: Mapped[str] = mapped_column(String(50), default="REINFORCE")
    episodes: Mapped[int] = mapped_column(Integer, nullable=False)
    data_source: Mapped[str] = mapped_column(String(50), default="open-meteo-archive")
    best_reward: Mapped[float] = mapped_column(Float, nullable=False)
    mean_reward: Mapped[float] = mapped_column(Float, default=0.0)
    final_rates: Mapped[dict] = mapped_column(JSON, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Location(Base):
    """Generic discoverable location (solar site, substation, or weather grid point)."""

    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_type: Mapped[str] = mapped_column(
        String(50), default="site"
    )  # site|substation|weather_grid
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=True)
    source_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Substation(Base):
    """A grid substation. Coordinates are used as published; never invented.

    SOURCE: docs/SOURCE_REGISTRY.md#src-osm-substation-001 (OSM) or operator CSV.
    """

    __tablename__ = "substations"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    voltage_level: Mapped[str] = mapped_column(String(50), nullable=True)
    operator: Mapped[str] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    district: Mapped[str] = mapped_column(String(120), nullable=True)
    state: Mapped[str] = mapped_column(String(120), nullable=True)
    country: Mapped[str] = mapped_column(String(120), nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=True)
    source_confidence: Mapped[float] = mapped_column(Float, default=0.6)
    osm_id: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WeatherProviderLocation(Base):
    """A coordinate for which a weather provider has data (grid point / site)."""

    __tablename__ = "weather_provider_locations"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(50), default="open-meteo")
    label: Mapped[str] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SiteSubstationMap(Base):
    """Nearest-substation mapping for a site (distance in km)."""

    __tablename__ = "site_substation_map"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("sites.id"), nullable=False)
    substation_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("substations.id"), nullable=False
    )
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DSMRuleProfile(Base):
    """A configurable DSM rule profile (region + regulator + denominator + bands).

    DSM rules vary by country/region/regulator/generator type/time block, so no
    universal value is hardcoded. `source_status` records whether the numbers are
    official or configurable-pending. See docs/DSM_RULE_SOURCES.md.
    """

    __tablename__ = "dsm_rule_profiles"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    region: Mapped[str] = mapped_column(String(120), nullable=True)
    regulator: Mapped[str] = mapped_column(String(120), nullable=True)
    denominator: Mapped[str] = mapped_column(String(40), default="available_capacity")
    tolerance_percent: Mapped[float] = mapped_column(Float, default=10.0)
    time_block_minutes: Mapped[int] = mapped_column(Integer, default=15)
    source_name: Mapped[str] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=True)
    source_status: Mapped[str] = mapped_column(String(60), default="USER_CONFIGURABLE")
    effective_from: Mapped[str] = mapped_column(String(40), nullable=True)
    effective_to: Mapped[str] = mapped_column(String(40), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bands: Mapped[list["DSMRuleBand"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class DSMRuleBand(Base):
    __tablename__ = "dsm_rule_bands"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("dsm_rule_profiles.id"), nullable=False
    )
    min_deviation_percent: Mapped[float] = mapped_column(Float, nullable=False)
    max_deviation_percent: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(20), default="BOTH")  # UNDER/OVER/BOTH
    charge_formula: Mapped[str] = mapped_column(String(255), nullable=True)
    charge_rate: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(20), default="INR/kWh")
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    source_reference: Mapped[str] = mapped_column(String(120), nullable=True)

    profile: Mapped["DSMRuleProfile"] = relationship(back_populates="bands")


class DSMResult(Base):
    __tablename__ = "dsm_results"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("sites.id"), nullable=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    scheduled_generation_mw: Mapped[float] = mapped_column(Float, default=0.0)
    predicted_generation_mw: Mapped[float] = mapped_column(Float, default=0.0)
    actual_generation_mw: Mapped[float] = mapped_column(Float, nullable=True)
    installed_capacity_mw: Mapped[float] = mapped_column(Float, default=0.0)
    deviation_mw: Mapped[float] = mapped_column(Float, default=0.0)
    deviation_percent: Mapped[float] = mapped_column(Float, default=0.0)
    deviation_direction: Mapped[str] = mapped_column(String(20), default="WITHIN_LIMIT")
    dsm_band: Mapped[str] = mapped_column(String(60), nullable=True)
    penalty_status: Mapped[str] = mapped_column(String(30), default="NO_PENALTY")
    charge_rate: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_dsm_charge: Mapped[float] = mapped_column(Float, default=0.0)
    rule_source: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
