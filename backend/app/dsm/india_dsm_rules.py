"""India DSM default profiles (CERC national + KERC/Karnataka).

Framework references are OFFICIAL; the exact numeric rates ('X' multiplier, slab
rates) are marked USER_CONFIGURABLE_PENDING_OFFICIAL_SOURCE - the system does NOT
claim regulatory accuracy for a specific figure. Operators must load the current
official order before treating any charge as authoritative.

SOURCE: docs/DSM_RULE_SOURCES.md, docs/SOURCE_REGISTRY.md#src-cerc-dsm-2024,
        docs/SOURCE_REGISTRY.md#src-kerc-dsm
"""

from __future__ import annotations

from app.dsm.base_rules import RuleBand, RuleProfile
from app.dsm.dsm_sources import (
    DENOM_AVAILABLE_CAPACITY,
    DIR_BOTH,
    STATUS_PENDING,
)


def kerc_solar_profile() -> RuleProfile:
    """KERC/BESCOM solar: +/-5% band, escalating slab charges (representative)."""
    return RuleProfile(
        name="kerc-solar",
        region="Karnataka",
        regulator="KERC/BESCOM",
        denominator=DENOM_AVAILABLE_CAPACITY,
        tolerance_percent=5.0,
        time_block_minutes=15,
        source_name="KERC Forecasting, Scheduling & DSM (Karnataka)",
        source_url="https://karnatakaerc.gov.in",
        source_status=STATUS_PENDING,
        notes="Band +/-5% is framework-official; slab rates are representative defaults "
        "pending the exact current KERC order.",
        bands=[
            RuleBand(5.0, 10.0, 2.0, "INR/kWh", DIR_BOTH, source_reference="SRC-KERC-DSM"),
            RuleBand(10.0, 15.0, 4.0, "INR/kWh", DIR_BOTH, source_reference="SRC-KERC-DSM"),
            RuleBand(15.0, 100000.0, 6.0, "INR/kWh", DIR_BOTH, source_reference="SRC-KERC-DSM"),
        ],
    )


def cerc_ws_generic_profile() -> RuleProfile:
    """CERC national WS-seller framework. Denominator = available capacity (Reg 6(2)(a)).

    Tolerance and slab rates depend on the CERC 'X' value and normal-rate order and are
    therefore PENDING (configurable). Defaults below are placeholders, clearly labelled.
    """
    return RuleProfile(
        name="cerc-2024-ws-generic",
        region="India",
        regulator="CERC",
        denominator=DENOM_AVAILABLE_CAPACITY,
        tolerance_percent=10.0,  # placeholder; actual depends on CERC 'X'
        time_block_minutes=15,
        source_name="CERC (DSM & Related Matters) Regulations, 2024",
        source_url="https://cercind.gov.in",
        source_status=STATUS_PENDING,
        notes="Framework OFFICIAL (deviation vs available capacity). 'X' multiplier and "
        "normal charge rates are PENDING official order - placeholders only, not authoritative.",
        bands=[
            RuleBand(
                10.0,
                20.0,
                3.0,
                "INR/kWh",
                DIR_BOTH,
                source_reference="SRC-CERC-DSM-2024",
                notes="Placeholder rate pending CERC order.",
            ),
            RuleBand(
                20.0,
                100000.0,
                5.0,
                "INR/kWh",
                DIR_BOTH,
                source_reference="SRC-CERC-DSM-2024",
                notes="Placeholder rate pending CERC order.",
            ),
        ],
    )


def default_profiles() -> list[RuleProfile]:
    from app.dsm.configurable_rules import generic_configurable_profile

    return [kerc_solar_profile(), cerc_ws_generic_profile(), generic_configurable_profile()]
