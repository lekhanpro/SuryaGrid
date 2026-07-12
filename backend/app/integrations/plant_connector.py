"""Read-only plant connector + replay (Phase 4).

A DELIBERATELY read-only interface to plant telemetry: it can read historical or
replayed readings but exposes NO control surface. There is intentionally no
``write`` / ``set_point`` / ``command`` method - the platform is advisory only and
must never actuate equipment.

``ReplayPlantConnector`` replays a captured CSV/rows sequence for shadow testing.
Real connectors (Modbus/OPC-UA/vendor API) would implement the same read-only
protocol and validate rows through ``local_pv_schema``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.data_pipeline.local_pv_schema import validate_reading


@runtime_checkable
class ReadOnlyPlantConnector(Protocol):
    """Read-only telemetry source. No control methods exist by design."""

    plant_id: str
    mode: str  # "replay" | "live-readonly"

    def read_next(self) -> dict | None:
        """Next validated reading, or None when the stream is exhausted."""
        ...

    def snapshot(self) -> dict | None:
        """Most recent validated reading without advancing."""
        ...


class ReplayPlantConnector:
    """Replays captured readings for shadow/replay testing. Read-only."""

    mode = "replay"

    def __init__(self, plant_id: str, rows: list[dict]):
        self.plant_id = plant_id
        self._rows = list(rows)
        self._i = 0
        self._last: dict | None = None
        self.rejected: list[dict] = []

    def read_next(self) -> dict | None:
        while self._i < len(self._rows):
            raw = self._rows[self._i]
            self._i += 1
            reading, reason = validate_reading(raw)
            if reading is None:
                self.rejected.append({"index": self._i, "reason": reason, "raw": raw})
                continue
            from dataclasses import asdict

            self._last = asdict(reading)
            return self._last
        return None

    def snapshot(self) -> dict | None:
        return self._last

    def reset(self) -> None:
        self._i = 0
        self._last = None
        self.rejected.clear()

    # NOTE: no write/command/set_point method exists - advisory platform only.
