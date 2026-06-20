"""Database models for Suryagrid AI Phase 1."""

import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, JSON, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")  # admin, operator, viewer
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    site_accesses: Mapped[list["SiteAccess"]] = relationship(back_populates="user")


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    capacity_mw: Mapped[float] = mapped_column(Float, nullable=False)
    panel_efficiency: Mapped[float] = mapped_column(Float, default=0.18)
    tilt: Mapped[float] = mapped_column(Float, default=15.0)
    azimuth: Mapped[float] = mapped_column(Float, default=180.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    site_accesses: Mapped[list["SiteAccess"]] = relationship(back_populates="site")
    weather_readings: Mapped[list["ToyWeatherReading"]] = relationship(back_populates="site")
    generation_readings: Mapped[list["GenerationReading"]] = relationship(back_populates="site")
    schedule_windows: Mapped[list["ScheduleWindow"]] = relationship(back_populates="site")
    dsm_results: Mapped[list["DSMResult"]] = relationship(back_populates="site")


class SiteAccess(Base):
    __tablename__ = "site_access"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sites.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")

    user: Mapped["User"] = relationship(back_populates="site_accesses")
    site: Mapped["Site"] = relationship(back_populates="site_accesses")


class ToyWeatherReading(Base):
    __tablename__ = "toy_weather_readings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sites.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    irradiance_w_m2: Mapped[float] = mapped_column(Float, nullable=False)
    cloud_cover_percent: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    humidity_percent: Mapped[float] = mapped_column(Float, default=50.0)
    wind_speed_mps: Mapped[float] = mapped_column(Float, default=2.0)
    rain_probability_percent: Mapped[float] = mapped_column(Float, default=0.0)
    quality_flag: Mapped[int] = mapped_column(Integer, default=1)

    site: Mapped["Site"] = relationship(back_populates="weather_readings")


class GenerationReading(Base):
    __tablename__ = "generation_readings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sites.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_generation_mw: Mapped[float] = mapped_column(Float, nullable=True)
    predicted_generation_mw: Mapped[float] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="toy")

    site: Mapped["Site"] = relationship(back_populates="generation_readings")


class ScheduleWindow(Base):
    __tablename__ = "schedule_windows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sites.id"), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_generation_mw: Mapped[float] = mapped_column(Float, nullable=False)
    allowed_dsm_threshold_percent: Mapped[float] = mapped_column(Float, default=10.0)
    penalty_rate_per_mw: Mapped[float] = mapped_column(Float, default=1000.0)

    site: Mapped["Site"] = relationship(back_populates="schedule_windows")
    dsm_results: Mapped[list["DSMResult"]] = relationship(back_populates="schedule_window")


class DSMResult(Base):
    __tablename__ = "dsm_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sites.id"), nullable=False)
    schedule_window_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedule_windows.id"), nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    predicted_generation_mw: Mapped[float] = mapped_column(Float, nullable=False)
    scheduled_generation_mw: Mapped[float] = mapped_column(Float, nullable=False)
    deviation_mw: Mapped[float] = mapped_column(Float, nullable=False)
    deviation_percent: Mapped[float] = mapped_column(Float, nullable=False)
    penalty_status: Mapped[str] = mapped_column(String(30), nullable=False)
    estimated_penalty_cost: Mapped[float] = mapped_column(Float, default=0.0)
    fuzzy_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    fuzzy_risk_level: Mapped[str] = mapped_column(String(20), default="LOW")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.8)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)

    site: Mapped["Site"] = relationship(back_populates="dsm_results")
    schedule_window: Mapped["ScheduleWindow"] = relationship(back_populates="dsm_results")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="audit_logs")
