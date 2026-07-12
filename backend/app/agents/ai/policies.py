"""Hard policies for the AI reasoning layer.

The reasoning layer is READ-ONLY and narrative-only. It can never mutate state,
issue control commands, or introduce numbers that are not in the deterministic
result. Any action outside the read-only tool list requires human approval -
and since no approval flow exists yet, such actions are refused outright.
"""

from __future__ import annotations

# Tools the reasoning layer may use. All are pure functions over the
# deterministic orchestrator result.
READ_ONLY_TOOLS = ("numeric_digest", "detect_anomalies", "deterministic_explanation")

HARD_RULES = (
    "Numbers must come from the deterministic orchestrator result; never invent values.",
    "No rupee amounts: official KERC/CERC tariff is not parsed (NEEDS_OFFICIAL_SOURCE).",
    "Missing data is stated as missing, never estimated silently.",
    "Anomaly detection is rule-based and deterministic; the LLM may only narrate it.",
    "No control commands, no writes, no external side effects.",
)


def requires_approval(action: str) -> bool:
    """Anything outside the read-only tool list needs human approval."""
    return action not in READ_ONLY_TOOLS


def policy_summary() -> dict:
    return {
        "read_only": True,
        "tools": list(READ_ONLY_TOOLS),
        "hard_rules": list(HARD_RULES),
    }
