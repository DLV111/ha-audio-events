from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from app.classifiers.base import Detection
from app.config import AggregationConfig
from app.detection.models import AggregatedEvent, EventMessage


class EventAggregator:
    def __init__(self, config: AggregationConfig) -> None:
        self.config = config
        self._active_events: dict[str, AggregatedEvent] = {}

    def update(
        self, detections: Iterable[Detection], timestamp: datetime | None = None
    ) -> list[EventMessage]:
        events: list[EventMessage] = []
        now = timestamp if timestamp is not None else datetime.now(UTC)
        detections_by_label: dict[str, Detection] = {}
        for detection in detections:
            detections_by_label[detection.label] = detection

        inactive_labels = list(self._active_events.keys())
        for label in inactive_labels:
            state = self._active_events[label]
            if (
                label not in detections_by_label
                and now - state.last_seen_at
                >= timedelta(seconds=self.config.end_timeout)
            ):
                state.duration = (state.last_seen_at - state.started_at).total_seconds()
                events.append(
                    EventMessage(
                        event_type="audio.detected",
                        label=label,
                        confidence=state.confidence,
                        duration=state.duration,
                        state="ended",
                        model=state.model,
                    )
                )
                del self._active_events[label]

        for detection in detections:
            state = self._active_events.get(detection.label)
            if state is None:
                if detection.confidence >= self.config.start_confidence:
                    self._active_events[detection.label] = AggregatedEvent(
                        label=detection.label,
                        confidence=detection.confidence,
                        started_at=now,
                        last_seen_at=now,
                        model=detection.model,
                    )
                    events.append(
                        EventMessage(
                            event_type="audio.detected",
                            label=detection.label,
                            confidence=detection.confidence,
                            duration=0.0,
                            state="started",
                            model=detection.model,
                        )
                    )
            else:
                state.last_seen_at = now
                state.confidence = max(state.confidence, detection.confidence)
                state.duration = (now - state.started_at).total_seconds()
                events.append(
                    EventMessage(
                        event_type="audio.detected",
                        label=detection.label,
                        confidence=state.confidence,
                        duration=state.duration,
                        state="active",
                        model=state.model,
                    )
                )

        return events
