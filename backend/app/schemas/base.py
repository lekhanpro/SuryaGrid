"""Base Pydantic schemas used across the application."""

from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class TimestampMixin(BaseModel):
    created_at: datetime | None = None


class SiteBase(BaseModel):
    name: str
    latitude: float
    longitude: float
    timezone: str = "Asia/Kolkata"
    capacity_mw: float
    panel_efficiency: float = 0.18
    tilt: float = 15.0
    azimuth: float = 180.0


class WeatherReading(BaseModel):
    timestamp: datetime
    irradiance_w_m2: float
    cloud_cover_percent: float
    temperature_c: float
    humidity_percent: float = 50.0
    wind_speed_mps: float = 2.0


class PredictionResult(BaseModel):
    predicted_generation_mw: float
    confidence_score: float


class DSMResult(BaseModel):
    deviation_mw: float
    deviation_percent: float
    penalty_status: str
    estimated_penalty_cost: float


class FuzzyRiskResult(BaseModel):
    fuzzy_risk_score: float
    fuzzy_risk_level: str


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    redis: str
