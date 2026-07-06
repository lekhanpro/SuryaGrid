"""Common contract for all real data providers.

Every provider (live weather, Kaggle dataset, substation, synthetic fallback)
reports a `status()` so the API can show the *real* state of each source. The
golden rule: no provider silently pretends to be another. If a real source is
unavailable or not loaded, its status says so explicitly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field

# Provider type constants
TYPE_LIVE_WEATHER = "live_weather"
TYPE_HISTORICAL_DATASET = "historical_dataset"
TYPE_SUBSTATION = "substation"
TYPE_SYNTHETIC = "synthetic"


@dataclass(slots=True)
class ProviderStatus:
    """Real, honest status of a data source."""

    name: str
    source_id: str
    provider_type: str
    available: bool  # can it be reached / used right now?
    detail: str  # human-readable state (e.g. "Kaggle dataset not loaded")
    loaded: bool | None = None  # datasets: is data present on disk?
    record_count: int | None = None
    mode: str = "real"  # "real" | "synthetic" | "manual"
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class DataProvider(ABC):
    """Base class for a real data source with a status contract."""

    name: str = "base"
    source_id: str = ""
    provider_type: str = "base"

    @abstractmethod
    def status(self) -> ProviderStatus:
        """Return the current, honest availability/loaded state of this source."""
        raise NotImplementedError
