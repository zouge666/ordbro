"""Query and ingestion traces, in the spirit of LinguaPilot's TraceContext."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any


class Trace:
    def __init__(self, kind: str = "query", **metadata: Any) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.metadata = metadata
        self.started_at = datetime.now(UTC).isoformat(timespec="seconds")
        self.stages: list[dict[str, Any]] = []
        self._start = time.perf_counter()
        self._last = self._start

    def stage(self, name: str, **details: Any) -> None:
        now = time.perf_counter()
        self.stages.append(
            {
                "stage": name,
                "ms": round((now - self._last) * 1000, 3),
                "details": details,
            }
        )
        self._last = now

    @property
    def total_ms(self) -> float:
        return round((self._last - self._start) * 1000, 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "started_at": self.started_at,
            "total_ms": self.total_ms,
            "metadata": self.metadata,
            "stages": self.stages,
        }
