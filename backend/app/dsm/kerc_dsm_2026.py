"""KERC DSM 2026 - effective-dated, officially-gated rupee DSM engine.

Execution-roadmap Phase 1 machinery for the day an official KERC DSM order is
parsed. The engine supports effective-dated orders, cumulative percentage slabs,
an annual cap, deemed-schedule applicability and per-slab source citations -
but it is HARD-GATED:

  * No order ships with this module. ``_ORDERS`` starts empty.
  * ``compute_block_charge`` refuses (``NEEDS_OFFICIAL_SOURCE``) unless an order
    that is BOTH effective on the requested date AND ``verified_official=True``
    (parsed from a cited official KERC document) has been registered.
  * An unverified order can be registered for staging but never activates.
  * ``clear_orders`` provides rollback.

Until the gate passes, every response keeps ``emits_rupee_values=False`` -
consistent with the platform-wide no-fabricated-rupee rule (see
docs/DSM_RULE_SOURCES.md and tests/test_phase0_foundation.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

NEEDS_OFFICIAL_SOURCE = "NEEDS_OFFICIAL_SOURCE"
OK = "OK"


@dataclass(slots=True)
class KercSlab:
    """One cumulative deviation slab: rate applies to the deviation energy that
    falls between ``from_percent`` and ``to_percent`` of the schedule."""

    from_percent: float
    to_percent: float
    rate_inr_per_kwh: float
    citation: str  # exact clause/page of the official order


@dataclass(slots=True)
class KercDsmOrder:
    """One effective-dated official KERC DSM order."""

    order_id: str
    title: str
    url: str  # official document URL
    effective_from: date
    effective_to: date | None  # None = open-ended
    verified_official: bool  # True ONLY after manual verification of the document
    tolerance_percent: float
    slabs: list[KercSlab] = field(default_factory=list)
    annual_cap_inr: float | None = None
    deemed_schedule_allowed: bool = False
    applicability: str = ""  # e.g. "solar generators > 5 MW connected to STU"


_ORDERS: list[KercDsmOrder] = []  # empty until an official order is parsed + verified


def register_order(order: KercDsmOrder) -> None:
    _ORDERS.append(order)


def clear_orders() -> None:
    """Rollback: forget every registered order (returns the engine to blocked)."""
    _ORDERS.clear()


def active_order(on_date: date) -> KercDsmOrder | None:
    """The VERIFIED order effective on ``on_date`` (latest effective_from wins)."""
    candidates = [
        o
        for o in _ORDERS
        if o.verified_official
        and o.effective_from <= on_date
        and (o.effective_to is None or on_date <= o.effective_to)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda o: o.effective_from)


def compute_block_charge(
    *,
    scheduled_kwh: float,
    actual_kwh: float,
    on_date: date,
    year_to_date_charge_inr: float = 0.0,
) -> dict:
    """Charge for one settlement block under the active official order.

    Blocked (``NEEDS_OFFICIAL_SOURCE``) until a verified official order is
    registered for ``on_date``. Cumulative slabs; annual cap enforced against
    ``year_to_date_charge_inr``.
    """
    order = active_order(on_date)
    if order is None:
        return {
            "status": NEEDS_OFFICIAL_SOURCE,
            "emits_rupee_values": False,
            "charge_inr": None,
            "reason": (
                "No verified official KERC DSM order is registered for this date; "
                "rupee DSM charges are blocked (never fabricated)."
            ),
            "orders_registered": len(_ORDERS),
        }
    if scheduled_kwh <= 0:
        return {
            "status": "INVALID_SCHEDULE",
            "emits_rupee_values": False,
            "charge_inr": None,
            "reason": "scheduled_kwh must be > 0 to compute a deviation percentage.",
            "order_id": order.order_id,
        }

    deviation_pct = abs(actual_kwh - scheduled_kwh) / scheduled_kwh * 100.0
    slab_charges: list[dict] = []
    charge = 0.0
    if deviation_pct > order.tolerance_percent:
        for slab in sorted(order.slabs, key=lambda s: s.from_percent):
            lo = max(slab.from_percent, order.tolerance_percent)
            hi = min(slab.to_percent, deviation_pct)
            if hi <= lo:
                continue
            slab_kwh = (hi - lo) / 100.0 * scheduled_kwh
            slab_inr = slab_kwh * slab.rate_inr_per_kwh
            charge += slab_inr
            slab_charges.append(
                {
                    "from_percent": lo,
                    "to_percent": hi,
                    "kwh": round(slab_kwh, 6),
                    "rate_inr_per_kwh": slab.rate_inr_per_kwh,
                    "charge_inr": round(slab_inr, 4),
                    "citation": slab.citation,
                }
            )

    capped = False
    if order.annual_cap_inr is not None:
        remaining = max(0.0, order.annual_cap_inr - year_to_date_charge_inr)
        if charge > remaining:
            charge = remaining
            capped = True

    return {
        "status": OK,
        "emits_rupee_values": True,  # permitted ONLY because a verified order is active
        "charge_inr": round(charge, 4),
        "deviation_percent": round(deviation_pct, 4),
        "tolerance_percent": order.tolerance_percent,
        "slab_charges": slab_charges,
        "annual_cap_applied": capped,
        "deemed_schedule_allowed": order.deemed_schedule_allowed,
        "applicability": order.applicability,
        "order": {
            "order_id": order.order_id,
            "title": order.title,
            "url": order.url,
            "effective_from": order.effective_from.isoformat(),
            "effective_to": order.effective_to.isoformat() if order.effective_to else None,
        },
    }
