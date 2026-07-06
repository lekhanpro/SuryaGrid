"""DSM source classification and shared constants.

Maps regulators to source records and records the honesty status of each profile.
See docs/DSM_RULE_SOURCES.md and docs/SOURCE_REGISTRY.md.
"""

from __future__ import annotations

# Denominator options (how deviation % is computed)
DENOM_AVAILABLE_CAPACITY = "available_capacity"  # CERC Reg 6(2)(a) for WS sellers
DENOM_SCHEDULED = "scheduled"  # simple mode

# Deviation directions
DIR_UNDER = "UNDER_INJECTION"
DIR_OVER = "OVER_INJECTION"
DIR_WITHIN = "WITHIN_LIMIT"
DIR_BOTH = "BOTH"

# Penalty statuses
PENALTY_RISK = "PENALTY_RISK"
NO_PENALTY = "NO_PENALTY"
WITHIN_LIMIT = "WITHIN_LIMIT"
INVALID_SCHEDULE = "INVALID_SCHEDULE"

# Source status classifications (see docs/SOURCE_REGISTRY.md)
STATUS_OFFICIAL = "OFFICIAL_SOURCE"
STATUS_USER_CONFIGURABLE = "USER_CONFIGURABLE"
STATUS_PENDING = "USER_CONFIGURABLE_PENDING_OFFICIAL_SOURCE"

# Regulator -> source registry ID (docs/SOURCE_REGISTRY.md)
REGULATOR_SOURCE_ID = {
    "CERC": "SRC-CERC-DSM-2024",
    "KERC": "SRC-KERC-DSM",
    "KERC/BESCOM": "SRC-KERC-DSM",
}


def source_for_regulator(regulator: str | None) -> str | None:
    if not regulator:
        return None
    return REGULATOR_SOURCE_ID.get(regulator)
