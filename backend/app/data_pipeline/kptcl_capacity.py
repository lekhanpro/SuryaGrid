"""KPTCL/CEA substation capacity records + station matcher (Phase 2).

Official KPTCL/CEA capacity data has not been granted yet; this module defines
the record schema and the conservative matcher that will link official capacity
rows to the OSM substation catalog when the data arrives.

Honesty rules:
  * ``status`` distinguishes COMMISSIONED from PLANNED augmentation - planned
    capacity is never treated as available.
  * Matching is conservative: a match requires normalized-name agreement plus
    voltage agreement (when both sides have voltage) plus geographic proximity
    when coordinates exist; anything ambiguous goes to ``needs_manual_review``
    instead of being auto-linked.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass

STATUS_COMMISSIONED = "COMMISSIONED"
STATUS_PLANNED = "PLANNED"  # augmentation not yet on the ground - never usable capacity


@dataclass(slots=True)
class CapacityRecord:
    station_name: str
    voltage_kv: float | None
    capacity_mva: float | None
    status: str  # COMMISSIONED | PLANNED
    source_name: str
    source_url: str
    effective_date: str | None = None
    latitude: float | None = None
    longitude: float | None = None


def normalize_name(name: str) -> str:
    """Lowercase, strip common substation words/punctuation for comparison."""
    n = name.lower()
    n = re.sub(r"\b(sub[- ]?station|substation|s/s|ss|mus|kv)\b", " ", n)
    n = re.sub(r"\d+(\.\d+)?", " ", n)  # voltage numbers compare separately
    n = re.sub(r"[^a-z]+", " ", n)
    return " ".join(n.split())


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def match_capacity_records(
    records: list[CapacityRecord],
    catalog: list[dict],
    *,
    max_distance_km: float = 5.0,
) -> dict:
    """Match official capacity records to catalog substations, conservatively.

    catalog rows: {substation_id, name, latitude, longitude, voltage_kv, ...}
    Returns {matched, needs_manual_review, unmatched} - nothing is silently linked.
    """
    matched: list[dict] = []
    review: list[dict] = []
    unmatched: list[dict] = []

    for rec in records:
        rec_name = normalize_name(rec.station_name)
        candidates = []
        for sub in catalog:
            sub_name = normalize_name(sub.get("name") or "")
            if not rec_name or not sub_name:
                continue
            if rec_name not in sub_name and sub_name not in rec_name:
                continue
            # voltage must agree when both sides know it
            if (
                rec.voltage_kv is not None
                and sub.get("voltage_kv") is not None
                and abs(rec.voltage_kv - float(sub["voltage_kv"])) > 0.5
            ):
                continue
            # distance must agree when both sides have coordinates
            if (
                rec.latitude is not None
                and rec.longitude is not None
                and sub.get("latitude") is not None
                and sub.get("longitude") is not None
            ):
                dist = _km(rec.latitude, rec.longitude, sub["latitude"], sub["longitude"])
                if dist > max_distance_km:
                    continue
                candidates.append((dist, sub))
            else:
                candidates.append((None, sub))

        if len(candidates) == 1:
            matched.append(
                {
                    "record": asdict(rec),
                    "substation_id": candidates[0][1]["substation_id"],
                    "distance_km": round(candidates[0][0], 3)
                    if candidates[0][0] is not None
                    else None,
                    "usable_capacity": rec.status == STATUS_COMMISSIONED,
                }
            )
        elif len(candidates) > 1:
            review.append(
                {
                    "record": asdict(rec),
                    "candidates": [c[1]["substation_id"] for c in candidates],
                    "reason": "multiple catalog substations match name/voltage/geo",
                }
            )
        else:
            unmatched.append({"record": asdict(rec), "reason": "no catalog candidate"})

    return {"matched": matched, "needs_manual_review": review, "unmatched": unmatched}
