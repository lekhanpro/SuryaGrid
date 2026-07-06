"""DSM rule data structures (engine-agnostic).

RuleBand / RuleProfile are plain dataclasses the engine evaluates. They can be
built in code (defaults) or hydrated from the database. See docs/DSM_RULE_SOURCES.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.dsm.dsm_sources import (
    DENOM_AVAILABLE_CAPACITY,
    DIR_BOTH,
    STATUS_USER_CONFIGURABLE,
)


@dataclass(slots=True)
class RuleBand:
    """A charge slab applied to the portion of deviation-% falling within it."""

    min_deviation_percent: float
    max_deviation_percent: float
    charge_rate: float
    unit: str = "INR/kWh"  # "INR/kWh" or "INR/MWh"
    direction: str = DIR_BOTH  # UNDER_INJECTION | OVER_INJECTION | BOTH
    charge_formula: str = ""
    notes: str = ""
    source_reference: str = ""

    def rate_per_mwh(self) -> float:
        return self.charge_rate * 1000.0 if self.unit == "INR/kWh" else self.charge_rate


@dataclass(slots=True)
class RuleProfile:
    """A complete, configurable DSM rule profile."""

    name: str
    region: str | None = None
    regulator: str | None = None
    denominator: str = DENOM_AVAILABLE_CAPACITY
    tolerance_percent: float = 10.0  # allowed band; no charge within it
    time_block_minutes: int = 15
    source_name: str | None = None
    source_url: str | None = None
    source_status: str = STATUS_USER_CONFIGURABLE
    effective_from: str | None = None
    effective_to: str | None = None
    notes: str = ""
    bands: list[RuleBand] = field(default_factory=list)
    id: str | None = None

    def sorted_bands(self) -> list[RuleBand]:
        return sorted(self.bands, key=lambda b: b.min_deviation_percent)
