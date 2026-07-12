"""Regional/Karnataka load report ingestion (Phase 2, fixture-driven).

No official NPP/Grid India/SLDC file has been inspected yet, so this parser is
built against a DOCUMENTED FIXTURE format and clearly says so
(``FORMAT_STATUS``). When the real report format is obtained the column map is
the single place to adapt; the validation rules (strict rejection, no silent
zero-fill, provenance on every batch) stay.

Fixture CSV format (one row per interval):
    timestamp,region,demand_mw
    2026-07-01T00:00:00+05:30,Karnataka,8250.5
"""

from __future__ import annotations

import csv
import io
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

FORMAT_STATUS = "FIXTURE_DEFINED_PENDING_OFFICIAL_FILE"  # honest: real file not yet inspected

_REQUIRED_COLUMNS = ("timestamp", "region", "demand_mw")


@dataclass(slots=True)
class RegionalLoadRow:
    timestamp: str  # ISO-8601, timezone-aware
    region: str
    demand_mw: float


def parse_regional_load_csv(csv_text: str, *, source_name: str, source_url: str) -> dict:
    """Parse a regional load CSV. Bad rows are REJECTED with reasons, never coerced.

    Returns {rows, rejected, provenance}; raises ValueError when the header is
    not the documented fixture format (a format change must be reviewed by a
    human, not silently absorbed).
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    fields = tuple(reader.fieldnames or ())
    missing = [c for c in _REQUIRED_COLUMNS if c not in fields]
    if missing:
        raise ValueError(
            f"Unexpected load report format: missing columns {missing}; "
            f"got {list(fields)}. Inspect the official file and update the column map."
        )

    rows: list[RegionalLoadRow] = []
    rejected: list[dict] = []
    for i, raw in enumerate(reader, start=2):  # 2 = first data line in the file
        reason = None
        ts = (raw.get("timestamp") or "").strip()
        region = (raw.get("region") or "").strip()
        try:
            parsed_ts = datetime.fromisoformat(ts)
            if parsed_ts.tzinfo is None:
                reason = "timestamp is not timezone-aware"
        except ValueError:
            reason = f"unparseable timestamp: {ts!r}"
        demand: float | None = None
        if reason is None:
            try:
                demand = float(raw.get("demand_mw", ""))
                if demand < 0:
                    reason = f"negative demand_mw: {demand}"
            except (TypeError, ValueError):
                reason = f"unparseable demand_mw: {raw.get('demand_mw')!r}"
        if reason is None and not region:
            reason = "empty region"

        if reason is not None or demand is None:
            rejected.append({"line": i, "reason": reason or "missing demand_mw", "raw": dict(raw)})
        else:
            rows.append(RegionalLoadRow(timestamp=ts, region=region, demand_mw=demand))

    return {
        "rows": [asdict(r) for r in rows],
        "accepted": len(rows),
        "rejected": rejected,
        "provenance": {
            "source_name": source_name,
            "source_url": source_url,
            "format_status": FORMAT_STATUS,
            "ingested_at": datetime.now(UTC).isoformat(),
        },
    }
