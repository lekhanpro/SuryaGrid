"""Request schemas for the Suryagrid AI API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SiteCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "Asia/Kolkata"
    capacity_mw: float = Field(gt=0)
    tilt: float = Field(default=20.0, ge=0, le=90)
    azimuth: float = Field(default=180.0, ge=0, le=360)
    altitude: float = Field(default=0.0, ge=0)
    allowed_dsm_threshold_percent: float = Field(default=10.0, ge=0, le=100)
    penalty_rate_per_mwh: float = Field(default=12000.0, ge=0)


class PredictRequest(BaseModel):
    """Single-interval prediction from explicit irradiance inputs."""

    capacity_mw: float = Field(gt=0)
    latitude: float = Field(default=28.6, ge=-90, le=90)
    longitude: float = Field(default=77.2, ge=-180, le=180)
    timezone: str = "Asia/Kolkata"
    tilt: float = Field(default=20.0, ge=0, le=90)
    azimuth: float = Field(default=180.0, ge=0, le=360)
    ghi_w_m2: float = Field(ge=0, le=1500)
    dni_w_m2: float = Field(default=0.0, ge=0, le=1500)
    dhi_w_m2: float = Field(default=0.0, ge=0, le=1500)
    cloud_cover_percent: float = Field(ge=0, le=100)
    temperature_c: float = Field(ge=-40, le=60)
    wind_speed_mps: float = Field(default=2.0, ge=0)
    scheduled_generation_mw: float = Field(ge=0)
    allowed_dsm_threshold_percent: float = Field(default=10.0, ge=0, le=100)
    penalty_rate_per_mwh: float = Field(default=12000.0, ge=0)


class DSMCheckRequest(BaseModel):
    predicted_generation_mw: float = Field(ge=0)
    scheduled_generation_mw: float
    allowed_dsm_threshold_percent: float = Field(default=10.0, ge=0, le=100)
    penalty_rate_per_mwh: float = Field(default=12000.0, ge=0)
