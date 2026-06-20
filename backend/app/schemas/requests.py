"""Request schemas for Phase 1 API."""

from pydantic import BaseModel, Field
from datetime import date
from uuid import UUID


class SiteCreateRequest(BaseModel):
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "Asia/Kolkata"
    capacity_mw: float = Field(gt=0)
    panel_efficiency: float = Field(default=0.18, gt=0, le=1)


class ToyDataGenerateRequest(BaseModel):
    site_id: str
    target_date: date | None = None
    interval_minutes: int = Field(default=30, ge=5, le=60)
    seed: int | None = None


class PredictRequest(BaseModel):
    site_id: str
    solar_capacity_mw: float = Field(gt=0)
    irradiance_w_m2: float = Field(ge=0, le=1500)
    cloud_cover_percent: float = Field(ge=0, le=100)
    temperature_c: float = Field(ge=-40, le=60)
    scheduled_generation_mw: float
    allowed_dsm_threshold_percent: float = Field(default=10.0, ge=0)
    penalty_rate_per_mw: float = Field(default=15000.0, ge=0)


class DSMCheckRequest(BaseModel):
    predicted_generation_mw: float = Field(ge=0)
    scheduled_generation_mw: float
    allowed_dsm_threshold_percent: float = Field(default=10.0, ge=0)
    penalty_rate_per_mw: float = Field(default=15000.0, ge=0)
