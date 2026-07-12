"""Run-state checkpoints for the AI reasoning layer.

Each AI run records start/finish checkpoints (run id, stage, attempts, outcome)
in an in-process ring buffer so operators can audit what the reasoning layer did
and why it fell back. In-memory by design for now; a durable store can replace
``CheckpointStore`` without touching callers.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class AICheckpoint:
    run_id: str
    substation_id: str
    stage: str  # "start" | "llm_attempt" | "done"
    status: str  # "running" | "llm" | "deterministic_fallback" | "error"
    attempts: int = 0
    model: str | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class CheckpointStore:
    def __init__(self, maxlen: int = 100):
        self._buf: deque[AICheckpoint] = deque(maxlen=maxlen)

    def append(self, cp: AICheckpoint) -> None:
        self._buf.append(cp)

    def list(self, limit: int = 20) -> list[dict]:
        return [asdict(cp) for cp in list(self._buf)[-limit:]]


_STORE = CheckpointStore()


def get_checkpoint_store() -> CheckpointStore:
    return _STORE
