"""In-memory recent-detections buffer shared between the detection loop and
the webui, so the ingress panel can show what's actually being detected
without needing to query Home Assistant (which may itself be misconfigured
or unreachable -- this should work regardless)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class DetectionRecord:
    label: str
    confidence: float
    state: str
    timestamp: str


class EventHistory:
    """Ring buffer of the most recent detection events."""

    def __init__(self, max_size: int = 50) -> None:
        self._events: deque[DetectionRecord] = deque(maxlen=max_size)

    def add(self, label: str, confidence: float, state: str) -> None:
        self._events.appendleft(
            DetectionRecord(
                label=label,
                confidence=confidence,
                state=state,
                timestamp=datetime.now(UTC).isoformat(),
            )
        )

    def recent(self) -> list[dict[str, str | float]]:
        return [
            {
                "label": event.label,
                "confidence": event.confidence,
                "state": event.state,
                "timestamp": event.timestamp,
            }
            for event in self._events
        ]
