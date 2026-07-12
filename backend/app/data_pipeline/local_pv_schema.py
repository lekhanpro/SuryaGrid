"""Local PV generation ingestion schema (Phase 2).

Defines the contract for REAL, measured plant generation the day KPCL/BESCOM or a
willing operator shares it. Until then no such data exists; this schema exists so
that when it arrives it is validated, provenance-stamped, and clearly separated
from the ESTIMATED_FROM_IRRADIANCE values the platform produces today.

A row must carry meter provenance and a quality flag; rows failing validation are
rejected with reasons, never coerced. Nothing here fabricates generation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

# Quality flags a metering system may assert about a reading.
QUALITY_GOOD = "GOOD"
QUALITY_ESTIMATED = "ESTIMATED"  # meter-side estimate (still not our model's estimate)
QUALITY_MISSING = "MISSING"
QUALITY_SUSPECT = "SUSPECT"
_VALID_QUALITY = {QUALITY_GOOD, QUALITY_ESTIMATED, QUALITY_MISSING, QUALITY_SUSPECT}

INVERTER_STATES = {"RUNNING", "STANDBY", "FAULT", "OFF", "UNKNOWN"}


@dataclass(slots=True)
class LocalPVReading:
    timestamp: str  # ISO-8601, timezone-aware
    plant_id: str
    ac_power_kw: float | None
    dc_power_kw: float | None
    irradiance_wm2: float | None
    inverter_state: str
    quality_flag: str
    meter_id: str
    meter_source: str  # provenance: which metering system produced this
    generation_type: str = "MEASURED_LOCAL_PV"  # distinct from ESTIMATED_FROM_IRRADIANCE
    actual_generation_available: bool = True


def validate_reading(raw: dict) -> tuple[LocalPVReading | None, str | None]:
    """Return (reading, None) or (None, reason). No coercion of bad values."""
    ts = str(raw.get("timestamp", "")).strip()
    try:
        parsed = datetime.fromisoformat(ts)
        if parsed.tzinfo is None:
            return None, "timestamp is not timezone-aware"
    except ValueError:
        return None, f"unparseable timestamp: {ts!r}"

    if not str(raw.get("plant_id", "")).strip():
        return None, "missing plant_id"
    if not str(raw.get("meter_id", "")).strip() or not str(raw.get("meter_source", "")).strip():
        return None, "missing meter provenance (meter_id/meter_source)"

    quality = str(raw.get("quality_flag", "")).strip().upper()
    if quality not in _VALID_QUALITY:
        return None, f"invalid quality_flag: {raw.get('quality_flag')!r}"

    state = str(raw.get("inverter_state", "UNKNOWN")).strip().upper()
    if state not in INVERTER_STATES:
        return None, f"invalid inverter_state: {raw.get('inverter_state')!r}"

    def _opt_float(key: str) -> tuple[float | None, str | None]:
        v = raw.get(key)
        if v is None or v == "":
            return None, None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None, f"unparseable {key}: {v!r}"
        if f < 0:
            return None, f"negative {key}: {f}"
        return f, None

    ac, err = _opt_float("ac_power_kw")
    if err:
        return None, err
    dc, err = _opt_float("dc_power_kw")
    if err:
        return None, err
    irr, err = _opt_float("irradiance_wm2")
    if err:
        return None, err

    # A GOOD reading must actually carry a power value (else it is not measured).
    if quality == QUALITY_GOOD and ac is None and dc is None:
        return None, "quality_flag GOOD but no ac/dc power present"

    return (
        LocalPVReading(
            timestamp=ts,
            plant_id=str(raw["plant_id"]).strip(),
            ac_power_kw=ac,
            dc_power_kw=dc,
            irradiance_wm2=irr,
            inverter_state=state,
            quality_flag=quality,
            meter_id=str(raw["meter_id"]).strip(),
            meter_source=str(raw["meter_source"]).strip(),
        ),
        None,
    )


def validate_batch(rows: list[dict]) -> dict:
    """Validate many readings; return accepted rows + rejection reasons."""
    accepted: list[dict] = []
    rejected: list[dict] = []
    for i, raw in enumerate(rows, start=1):
        reading, reason = validate_reading(raw)
        if reading is None:
            rejected.append({"index": i, "reason": reason, "raw": raw})
        else:
            accepted.append(asdict(reading))
    return {
        "accepted": accepted,
        "accepted_count": len(accepted),
        "rejected": rejected,
        "note": (
            "MEASURED_LOCAL_PV rows are real plant truth; none exist in the repo yet. "
            "This validates external data on arrival and keeps it distinct from the "
            "platform's ESTIMATED_FROM_IRRADIANCE output."
        ),
    }
