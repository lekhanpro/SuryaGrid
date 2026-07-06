"""Phase 1.7 provenance, path, and model-card helpers.

Single source of truth for:
  * Source-geography labels (REAL_LOCAL ... NEEDS_OFFICIAL_SOURCE).
  * The Phase 1.7 on-disk layout (backend/data/ml, backend/models/trained,
    backend/models/metadata).
  * Region config (Bengaluru / Karnataka / India).
  * A model-card builder that ENFORCES every required field, so no card can be
    written that hides geography, domain shift, synthetic %, or production status.
  * The real-mode guard: in data_mode="real" nothing may fall back to synthetic.

Honesty rules (hard, enforced here and by callers):
  1. No synthetic fallback when data_mode == "real".
  2. No fabricated confidence, PV generation, load, capacity, or rupee values.
  3. If real data is unavailable, callers return / persist NOT_AVAILABLE.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# --------------------------------------------------------------------------- #
# Source-geography / provenance labels (the 11 required labels)
# --------------------------------------------------------------------------- #
REAL_LOCAL = "REAL_LOCAL"  # Bengaluru-specific real data (generic local)
REAL_BENGALURU = "REAL_BENGALURU"  # explicitly Bengaluru-city real data
REAL_KARNATAKA = "REAL_KARNATAKA"  # Karnataka-state real data
REAL_INDIA = "REAL_INDIA"  # India-wide real data
REAL_COORDINATE_BASED = "REAL_COORDINATE_BASED"  # global API queried at Bengaluru lat/lon
REAL_NON_LOCAL = "REAL_NON_LOCAL"  # real but foreign (e.g. HI-SEAS Hawaii)
PRETRAINING_ONLY = "PRETRAINING_ONLY"  # usable only to pretrain, never production truth
ESTIMATED_FROM_REAL = "ESTIMATED_FROM_REAL"  # derived from real inputs via a documented formula
SYNTHETIC_AUGMENTED_FROM_REAL = "SYNTHETIC_AUGMENTED_FROM_REAL"
DEMO_ONLY = "DEMO_ONLY"
NOT_AVAILABLE = "NOT_AVAILABLE"
NEEDS_OFFICIAL_SOURCE = "NEEDS_OFFICIAL_SOURCE"

ALL_SOURCE_LABELS = {
    REAL_LOCAL,
    REAL_BENGALURU,
    REAL_KARNATAKA,
    REAL_INDIA,
    REAL_COORDINATE_BASED,
    REAL_NON_LOCAL,
    PRETRAINING_ONLY,
    ESTIMATED_FROM_REAL,
    SYNTHETIC_AUGMENTED_FROM_REAL,
    DEMO_ONLY,
    NOT_AVAILABLE,
    NEEDS_OFFICIAL_SOURCE,
}

# Labels that are honestly usable as production truth for a Bengaluru target.
PRODUCTION_TRUTH_LABELS = {
    REAL_LOCAL,
    REAL_BENGALURU,
    REAL_KARNATAKA,
    REAL_INDIA,
    REAL_COORDINATE_BASED,
}

DATA_MODE_REAL = "real"
DATA_MODE_DEMO = "demo"


# --------------------------------------------------------------------------- #
# Region config
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Region:
    key: str
    display_name: str
    latitude: float
    longitude: float
    timezone: str
    state: str
    country: str


BENGALURU = Region(
    key="bengaluru",
    display_name="Bengaluru (Bangalore)",
    latitude=12.9716,
    longitude=77.5946,
    timezone="Asia/Kolkata",
    state="Karnataka",
    country="India",
)

REGIONS: dict[str, Region] = {"bengaluru": BENGALURU}


def get_region(key: str) -> Region:
    region = REGIONS.get((key or "").lower())
    if region is None:
        raise ValueError(f"Unknown region '{key}'. Supported: {sorted(REGIONS)}")
    return region


# --------------------------------------------------------------------------- #
# Paths (Phase 1.7 layout). backend/ is parents[2] of app/ml/provenance.py.
# --------------------------------------------------------------------------- #
def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    override = os.environ.get("SURYAGRID_DATA_DIR")
    return Path(override) if override else _backend_dir() / "data"


def ml_data_dir() -> Path:
    return data_dir() / "ml"


def raw_data_dir() -> Path:
    return data_dir() / "raw"


def _models_dir() -> Path:
    override = os.environ.get("SURYAGRID_MODELS_DIR")
    return Path(override) if override else _backend_dir() / "models"


def trained_models_dir() -> Path:
    return _models_dir() / "trained"


def model_metadata_dir() -> Path:
    return _models_dir() / "metadata"


def docs_dir() -> Path:
    return _backend_dir().parent / "docs"


def ensure_dirs() -> None:
    for d in (ml_data_dir(), raw_data_dir(), trained_models_dir(), model_metadata_dir()):
        d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Parquet IO
# --------------------------------------------------------------------------- #
def write_parquet(df, filename: str) -> Path:
    """Write a DataFrame to backend/data/ml/<filename> as parquet. Returns path."""
    ml_data_dir().mkdir(parents=True, exist_ok=True)
    path = ml_data_dir() / filename
    df.to_parquet(path, index=False)
    return path


def read_parquet(filename: str):
    import pandas as pd

    path = ml_data_dir() / filename
    if not path.exists():
        return None
    return pd.read_parquet(path)


def ml_file_exists(filename: str) -> bool:
    return (ml_data_dir() / filename).exists()


# --------------------------------------------------------------------------- #
# Real-mode guard
# --------------------------------------------------------------------------- #
class SyntheticFallbackError(RuntimeError):
    """Raised when synthetic/demo data would be used in APP_DATA_MODE=real."""


def assert_real_mode_allows(source_label: str, *, data_mode: str, context: str) -> None:
    """In real mode, forbid synthetic/demo source labels. No silent fallback."""
    if data_mode == DATA_MODE_REAL and source_label in {
        SYNTHETIC_AUGMENTED_FROM_REAL,
        DEMO_ONLY,
    }:
        raise SyntheticFallbackError(
            f"{context}: source label '{source_label}' is not permitted in "
            f"APP_DATA_MODE=real. Real mode must not fall back to synthetic/demo data."
        )


# --------------------------------------------------------------------------- #
# Model cards
# --------------------------------------------------------------------------- #
# Every required key a Phase 1.7 model card MUST contain.
REQUIRED_MODEL_CARD_FIELDS = [
    "model_name",
    "model_version",
    "training_data_files",
    "training_data_sources",
    "training_geography",
    "target_geography",
    "local_data_available",
    "domain_shift_risk",
    "features",
    "target",
    "train_rows",
    "test_rows",
    "train_test_split_method",
    "metrics",
    "limitations",
    "production_ready",
    "reason_if_not_production_ready",
    "uses_synthetic_data",
    "synthetic_percentage",
    "uses_non_local_data",
    "non_local_data_percentage",
    "data_mode",
    "source_status",
]


@dataclass
class ModelCard:
    model_name: str
    model_version: str = field(default_factory=lambda: datetime.now(UTC).strftime("%Y%m%d%H%M%S"))
    training_data_files: list[str] = field(default_factory=list)
    training_data_sources: list[dict] = field(default_factory=list)
    training_geography: str = "Bengaluru, Karnataka, India"
    target_geography: str = "Bengaluru, Karnataka, India"
    local_data_available: bool = False
    domain_shift_risk: str = "UNKNOWN"  # NONE | LOW | MEDIUM | HIGH
    features: list[str] = field(default_factory=list)
    target: str | None = None
    train_rows: int = 0
    test_rows: int = 0
    train_test_split_method: str = "chronological_80_20"
    metrics: dict = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    production_ready: bool = False
    reason_if_not_production_ready: str | None = None
    uses_synthetic_data: bool = False
    synthetic_percentage: float = 0.0
    uses_non_local_data: bool = False
    non_local_data_percentage: float = 0.0
    data_mode: str = DATA_MODE_REAL
    # source_status: distinct provenance labels across training_data_sources.
    # Auto-derived in __post_init__ if left empty.
    source_status: list = field(default_factory=list)
    # Extra, non-required context (kept but not enforced)
    prediction_type: str | None = None
    model_type: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    notes: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.source_status:
            seen: list[str] = []
            for s in self.training_data_sources:
                label = s.get("label") if isinstance(s, dict) else None
                if label and label not in seen:
                    seen.append(label)
            self.source_status = seen

    def to_dict(self) -> dict:
        d = {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "training_data_files": self.training_data_files,
            "training_data_sources": self.training_data_sources,
            "training_geography": self.training_geography,
            "target_geography": self.target_geography,
            "local_data_available": self.local_data_available,
            "domain_shift_risk": self.domain_shift_risk,
            "features": self.features,
            "target": self.target,
            "train_rows": self.train_rows,
            "test_rows": self.test_rows,
            "train_test_split_method": self.train_test_split_method,
            "metrics": self.metrics,
            "limitations": self.limitations,
            "production_ready": self.production_ready,
            "reason_if_not_production_ready": self.reason_if_not_production_ready,
            "uses_synthetic_data": self.uses_synthetic_data,
            "synthetic_percentage": self.synthetic_percentage,
            "uses_non_local_data": self.uses_non_local_data,
            "non_local_data_percentage": self.non_local_data_percentage,
            "data_mode": self.data_mode,
            "source_status": self.source_status,
            "prediction_type": self.prediction_type,
            "model_type": self.model_type,
            "created_at": self.created_at,
            "notes": self.notes,
        }
        return d

    def validate(self) -> None:
        d = self.to_dict()
        missing = [k for k in REQUIRED_MODEL_CARD_FIELDS if k not in d or d[k] is None]
        # target/reason legitimately may be null; only reason_if_not_production_ready
        # may be null WHEN production_ready is True.
        hard_missing = []
        for k in missing:
            if k == "reason_if_not_production_ready" and self.production_ready:
                continue
            if k == "target" and self.target is None:
                continue
            hard_missing.append(k)
        if hard_missing:
            raise ValueError(f"Model card '{self.model_name}' missing required fields: {hard_missing}")
        if not self.production_ready and not self.reason_if_not_production_ready:
            raise ValueError(
                f"Model card '{self.model_name}': production_ready=false requires "
                "reason_if_not_production_ready."
            )

    def save(self, filename: str) -> Path:
        self.validate()
        model_metadata_dir().mkdir(parents=True, exist_ok=True)
        path = model_metadata_dir() / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        return path


def save_json(obj: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
    return path
