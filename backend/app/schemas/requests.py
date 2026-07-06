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


class MLPredictRequest(BaseModel):
    """Single-interval ML/hybrid prediction from site + weather inputs."""

    # Site
    latitude: float = Field(default=12.97, ge=-90, le=90)
    longitude: float = Field(default=77.59, ge=-180, le=180)
    timezone: str = "Asia/Kolkata"
    capacity_mw: float = Field(default=50.0, gt=0)
    tilt: float = Field(default=20.0, ge=0, le=90)
    azimuth: float = Field(default=180.0, ge=0, le=360)
    panel_efficiency: float = Field(default=0.18, gt=0, le=1)
    nearest_substation_distance_km: float = Field(default=0.0, ge=0)
    # Weather (single point)
    ghi_w_m2: float = Field(default=0.0, ge=0, le=1500)
    dni_w_m2: float = Field(default=0.0, ge=0, le=1500)
    dhi_w_m2: float = Field(default=0.0, ge=0, le=1500)
    temperature_c: float = Field(default=25.0, ge=-40, le=60)
    cloud_cover_percent: float = Field(default=0.0, ge=0, le=100)
    wind_speed_mps: float = Field(default=2.0, ge=0)
    humidity_percent: float = Field(default=0.0, ge=0, le=100)
    pressure_hpa: float = Field(default=0.0, ge=0)
    precipitation_probability_percent: float = Field(default=0.0, ge=0, le=100)
    # Forecast mode: auto | formula | ml | hybrid
    mode: str = Field(default="auto")


class SubstationImportRequest(BaseModel):
    """Import substations from OSM (provide lat/lon[+radius]) or CSV (provide csv_text)."""

    csv_text: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_km: float = Field(default=25.0, gt=0, le=200)


class DSMRuleBandInput(BaseModel):
    min_deviation_percent: float = Field(ge=0)
    max_deviation_percent: float = Field(gt=0)
    charge_rate: float = Field(ge=0)
    unit: str = "INR/kWh"
    direction: str = "BOTH"  # UNDER_INJECTION | OVER_INJECTION | BOTH
    charge_formula: str = ""
    notes: str = ""
    source_reference: str = "USER_CONFIGURABLE"


class DSMRuleProfileCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    region: str | None = None
    regulator: str | None = None
    denominator: str = "scheduled"  # available_capacity | scheduled
    tolerance_percent: float = Field(default=10.0, ge=0, le=100)
    time_block_minutes: int = Field(default=15, ge=1, le=60)
    source_name: str | None = None
    source_url: str | None = None
    source_status: str = "USER_CONFIGURABLE"
    effective_from: str | None = None
    effective_to: str | None = None
    notes: str = ""
    bands: list[DSMRuleBandInput] = Field(default_factory=list)


class DSMAdvancedCheckRequest(BaseModel):
    site_id: str | None = None
    scheduled_generation_mw: float = Field(ge=0)
    predicted_generation_mw: float = Field(ge=0)
    actual_generation_mw: float | None = Field(default=None, ge=0)
    installed_capacity_mw: float = Field(gt=0)
    interval_hours: float | None = Field(default=None, gt=0)
    rule_profile_id: str | None = None  # profile UUID or name
    region: str | None = None
    regulator: str | None = None
    market_rate: float | None = None
