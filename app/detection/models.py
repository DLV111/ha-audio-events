from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AggregatedEvent:
    label: str
    confidence: float
    started_at: datetime
    last_seen_at: datetime
    duration: float = 0.0


@dataclass
class EventMessage:
    event_type: str
    label: str
    confidence: float
    duration: float
    state: str
