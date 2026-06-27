"""BESCOM / Karnataka SLDC connector framework.

BESCOM (Bangalore Electricity Supply Company) is the Bangalore distribution
licensee; intra-state DSM settlement is administered by the Karnataka SLDC/STU
(KPTCL). Neither exposes a public real-time API — live metered injection and
schedule data require a formal data-sharing agreement / SCADA integration.

This connector defines the integration surface so that, once a feed is available
(SCADA/Modbus, OpenADR, or a CSV/SFTP drop), it slots in without changing the
settlement logic. Until then it operates in `simulated` mode, deriving "actual"
injection from the pvlib nowcast — which keeps the whole DSM pipeline functional.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FeedMode(StrEnum):
    SIMULATED = "simulated"  # actual = pvlib nowcast (no live feed)
    SCADA = "scada"  # live meter via SCADA/Modbus (requires agreement)
    FILE = "file"  # periodic CSV/SFTP drop from the utility


@dataclass(slots=True)
class TelemetryPoint:
    timestamp: str
    actual_injection_mw: float
    source: str


class BescomConnector:
    """Pluggable connector for Karnataka SLDC / BESCOM injection telemetry."""

    def __init__(self, mode: FeedMode = FeedMode.SIMULATED):
        self.mode = mode

    @property
    def is_live(self) -> bool:
        return self.mode in (FeedMode.SCADA, FeedMode.FILE)

    def status(self) -> dict:
        return {
            "operator": "Karnataka SLDC (KPTCL) / BESCOM",
            "mode": self.mode.value,
            "is_live": self.is_live,
            "note": (
                "Live metered injection requires a data-sharing agreement with the "
                "Karnataka SLDC. Running in simulated mode using the pvlib nowcast "
                "as a stand-in for actual injection."
            ),
        }

    def actual_injection(self, nowcast_mw: float, timestamp: str) -> TelemetryPoint:
        """Return actual injection for a 15-min block.

        In simulated mode this is the nowcast. A live implementation would read
        the metered value from SCADA/file here.
        """
        if self.is_live:
            raise NotImplementedError(
                "Live BESCOM/SLDC feed not configured. Provide SCADA/file credentials."
            )
        return TelemetryPoint(
            timestamp=timestamp, actual_injection_mw=nowcast_mw, source="simulated:nowcast"
        )
