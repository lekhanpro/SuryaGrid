"""Alert evaluation + acknowledgment (Phase 4).

Turns the deterministic anomaly list into acknowledgeable alerts. An alert's id is
a stable hash of (substation, code, evidence) so re-running the same forecast does
not spawn duplicates and an acknowledgment sticks. In-memory store for now; the
interface is storage-agnostic.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from app.agents.ai.anomaly_detective import detect_anomalies


def _alert_id(substation_id: str, code: str, evidence: dict) -> str:
    basis = f"{substation_id}|{code}|{sorted(evidence.items())!r}"
    return hashlib.sha1(basis.encode()).hexdigest()[:16]


@dataclass(slots=True)
class Alert:
    alert_id: str
    substation_id: str
    code: str
    severity: str
    message: str
    evidence: dict
    acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class AlertStore:
    def __init__(self):
        self._alerts: dict[str, Alert] = {}

    def evaluate(self, result: dict) -> list[Alert]:
        """Create/refresh alerts from a run; preserves prior acknowledgment."""
        substation_id = result.get("substation", {}).get("substation_id", "?")
        current: list[Alert] = []
        for a in detect_anomalies(result):
            aid = _alert_id(substation_id, a["code"], a.get("evidence", {}))
            existing = self._alerts.get(aid)
            if existing is None:
                existing = Alert(
                    alert_id=aid,
                    substation_id=substation_id,
                    code=a["code"],
                    severity=a["severity"],
                    message=a["message"],
                    evidence=a.get("evidence", {}),
                )
                self._alerts[aid] = existing
            current.append(existing)
        return current

    def acknowledge(self, alert_id: str, user: str) -> Alert | None:
        alert = self._alerts.get(alert_id)
        if alert is None:
            return None
        alert.acknowledged = True
        alert.acknowledged_by = user
        alert.acknowledged_at = datetime.now(UTC).isoformat()
        return alert

    def list(self, *, only_unacked: bool = False) -> list[dict]:
        vals = self._alerts.values()
        if only_unacked:
            vals = [a for a in vals if not a.acknowledged]
        return [asdict(a) for a in vals]


_STORE = AlertStore()


def get_alert_store() -> AlertStore:
    return _STORE
