"""Operator-configurable DSM profiles (no claim of regulatory accuracy).

A generic ±band profile and a factory to reproduce the legacy simple-threshold
behaviour through the engine. All values here are USER_CONFIGURABLE.
See docs/DSM_RULE_SOURCES.md.
"""

from __future__ import annotations

from app.dsm.base_rules import RuleBand, RuleProfile
from app.dsm.dsm_sources import (
    DENOM_SCHEDULED,
    DIR_BOTH,
    STATUS_USER_CONFIGURABLE,
)


def generic_configurable_profile() -> RuleProfile:
    """A neutral, operator-tunable default: ±10% band, flat charge beyond it."""
    return RuleProfile(
        name="generic-configurable",
        region=None,
        regulator="(operator)",
        denominator=DENOM_SCHEDULED,
        tolerance_percent=10.0,
        time_block_minutes=15,
        source_name="Operator-configured default",
        source_url=None,
        source_status=STATUS_USER_CONFIGURABLE,
        notes="Neutral default. Not tied to any regulator. Edit bands/tolerance per contract.",
        bands=[
            RuleBand(
                min_deviation_percent=10.0,
                max_deviation_percent=100000.0,
                charge_rate=12000.0,
                unit="INR/MWh",
                direction=DIR_BOTH,
                charge_formula="charge = chargeable_energy_mwh * rate",
                notes="Flat charge on deviation energy beyond the tolerance band.",
                source_reference="USER_CONFIGURABLE",
            )
        ],
    )


def simple_profile(
    tolerance_percent: float = 10.0,
    penalty_rate_per_mwh: float = 12000.0,
) -> RuleProfile:
    """Reproduce the legacy simple-threshold DSM as a one-band profile (denominator = scheduled)."""
    return RuleProfile(
        name="simple-threshold",
        regulator="(operator)",
        denominator=DENOM_SCHEDULED,
        tolerance_percent=tolerance_percent,
        source_name="Simple threshold (operator)",
        source_status=STATUS_USER_CONFIGURABLE,
        notes="Simple mode: charge on energy beyond the allowed band at a flat rate.",
        bands=[
            RuleBand(
                min_deviation_percent=tolerance_percent,
                max_deviation_percent=100000.0,
                charge_rate=penalty_rate_per_mwh,
                unit="INR/MWh",
                direction=DIR_BOTH,
                source_reference="USER_CONFIGURABLE",
            )
        ],
    )


def profile_from_payload(payload: dict) -> RuleProfile:
    """Build a RuleProfile from an API payload (POST /dsm/rule-profiles)."""
    bands = [
        RuleBand(
            min_deviation_percent=float(b["min_deviation_percent"]),
            max_deviation_percent=float(b["max_deviation_percent"]),
            charge_rate=float(b.get("charge_rate", 0.0)),
            unit=b.get("unit", "INR/kWh"),
            direction=b.get("direction", DIR_BOTH),
            charge_formula=b.get("charge_formula", ""),
            notes=b.get("notes", ""),
            source_reference=b.get("source_reference", "USER_CONFIGURABLE"),
        )
        for b in payload.get("bands", [])
    ]
    return RuleProfile(
        name=payload["name"],
        region=payload.get("region"),
        regulator=payload.get("regulator"),
        denominator=payload.get("denominator", DENOM_SCHEDULED),
        tolerance_percent=float(payload.get("tolerance_percent", 10.0)),
        time_block_minutes=int(payload.get("time_block_minutes", 15)),
        source_name=payload.get("source_name", "Operator-configured"),
        source_url=payload.get("source_url"),
        source_status=payload.get("source_status", STATUS_USER_CONFIGURABLE),
        effective_from=payload.get("effective_from"),
        effective_to=payload.get("effective_to"),
        notes=payload.get("notes", ""),
        bands=bands,
    )
