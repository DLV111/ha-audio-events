from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from app.classifiers.base import Detection
from app.config import AggregationConfig
from app.detection.models import AggregatedEvent, EventMessage


class EventAggregator:
    """Stable audio-event lifecycle and dominant-label selection.

    Implements the state machine described in ADR-45:

    * per-label activation with separate start/sustain confidence thresholds
    * minimum event hold and end-timeout expiration
    * canonical families (Thunder/Thunderstorm -> Thunder) for display
    * hysteretic dominant-label selection with switch margin, debounce and hold
    * physical-quiet global idle override
    """

    # Map raw labels to a canonical family for dominant-display purposes only.
    # Raw per-label lifetimes remain independent; see ADR-45 section 3.
    _CANONICAL_FAMILIES: ClassVar[dict[str, str]] = {
        "thunder": "Thunder",
        "thunderstorm": "Thunder",
    }

    def __init__(self, config: AggregationConfig) -> None:
        self.config = config
        self._active_events: dict[str, AggregatedEvent] = {}
        # Current display label, or "silence" when no event is dominant.
        self._display_label: str | None = None
        self._displayed_since: datetime | None = None
        # Pending challenger: (label, first_seen_at, observation_count).
        self._pending_candidate: tuple[str, datetime, int] | None = None

    @classmethod
    def _canonical_label(cls, label: str) -> str:
        return cls._CANONICAL_FAMILIES.get(label.lower(), label)

    @staticmethod
    def _stable_choice(items: Iterable[str]) -> str:
        """Locale-independent ascending sort for exact-score tie breaks."""
        return min(items)

    def _family_scores(self, detections: Iterable[Detection]) -> dict[str, float]:
        """Canonical-family scores for one observation (max member score)."""
        scores: dict[str, float] = {}
        for detection in detections:
            family = self._canonical_label(detection.label)
            scores[family] = max(scores.get(family, 0.0), detection.confidence)
        return scores

    def _active_family_scores(self) -> dict[str, float]:
        """Most recent supported score for each active canonical family."""
        scores: dict[str, float] = {}
        for label, state in self._active_events.items():
            family = self._canonical_label(label)
            scores[family] = max(scores.get(family, 0.0), state.current_confidence)
        return scores

    def _start_event(self, detection: Detection, now: datetime) -> EventMessage:
        self._active_events[detection.label] = AggregatedEvent(
            label=detection.label,
            confidence=detection.confidence,
            current_confidence=detection.confidence,
            started_at=now,
            last_seen_at=now,
            model=detection.model,
        )
        return EventMessage(
            event_type="audio.detected",
            label=detection.label,
            confidence=detection.confidence,
            duration=0.0,
            state="started",
            model=detection.model,
        )

    def _refresh_event(
        self, state: AggregatedEvent, detection: Detection, now: datetime
    ) -> EventMessage:
        state.last_seen_at = now
        state.current_confidence = detection.confidence
        state.confidence = max(state.confidence, detection.confidence)
        state.duration = (now - state.started_at).total_seconds()
        return EventMessage(
            event_type="audio.detected",
            label=state.label,
            confidence=state.confidence,
            duration=state.duration,
            state="active",
            model=state.model,
        )

    def _end_event(self, state: AggregatedEvent, now: datetime) -> EventMessage:
        state.duration = max(
            state.duration, (state.last_seen_at - state.started_at).total_seconds()
        )
        return EventMessage(
            event_type="audio.detected",
            label=state.label,
            confidence=state.confidence,
            duration=state.duration,
            state="ended",
            model=state.model,
        )

    def _display_event(self, label: str, now: datetime) -> EventMessage:
        duration = 0.0
        if self._displayed_since is not None:
            duration = (now - self._displayed_since).total_seconds()
        return EventMessage(
            event_type="audio.detected",
            label=label,
            confidence=1.0 if label == "silence" else 0.0,
            duration=duration,
            state="current",
            model="",
            is_display=True,
        )

    def _expire_old_events(self, now: datetime) -> list[EventMessage]:
        events: list[EventMessage] = []
        min_hold = timedelta(seconds=self.config.min_event_hold_seconds)
        end_timeout = timedelta(seconds=self.config.end_timeout)
        for label, state in list(self._active_events.items()):
            expire_at = max(
                state.started_at + min_hold,
                state.last_seen_at + end_timeout,
            )
            if now >= expire_at:
                events.append(self._end_event(state, now))
                del self._active_events[label]
        return events

    def _select_dominant(
        self,
        family_scores: dict[str, float],
        now: datetime,
    ) -> str | None:
        """Choose the next dominant label, or None for silence.

        This method implements the hysteresis rules from ADR-45 section C.
        It returns the label that should be displayed; it does not emit events.
        """
        # Only already-active families may be displayed. Fresh observation
        # scores have already refreshed ``current_confidence`` in update(),
        # and new qualifying events have already been started.
        active_scores = self._active_family_scores()

        if not active_scores:
            self._pending_candidate = None
            return None

        # Highest-scoring active family, using stable tie-break.
        highest = self._stable_choice(
            [f for f, s in active_scores.items() if s == max(active_scores.values())]
        )

        if self._display_label is None or self._display_label == "silence":
            self._pending_candidate = None
            return highest

        incumbent = self._display_label
        if incumbent not in active_scores:
            # Incumbent expired; fallback immediately to the highest active family.
            self._pending_candidate = None
            return highest

        incumbent_score = active_scores[incumbent]

        # Find the strongest qualifying challenger.
        challengers = {
            family: score
            for family, score in active_scores.items()
            if family != incumbent
            and score >= self.config.start_confidence
            and score - incumbent_score >= self.config.switch_margin - 1e-9
        }
        if not challengers:
            # No qualifying challenger; reset any pending switch.
            self._pending_candidate = None
            return incumbent

        challenger = self._stable_choice(
            [f for f, s in challengers.items() if s == max(challengers.values())]
        )

        # Continue or restart the pending run for this challenger.
        if self._pending_candidate is None or self._pending_candidate[0] != challenger:
            self._pending_candidate = (challenger, now, 1)
        else:
            _, first_seen, count = self._pending_candidate
            gap = (now - first_seen).total_seconds()
            max_gap = self.config.candidate_max_observation_gap_seconds
            if gap > max_gap:
                self._pending_candidate = (challenger, now, 1)
            else:
                self._pending_candidate = (challenger, first_seen, count + 1)

        _, first_seen, count = self._pending_candidate
        debounce_ok = (
            now - first_seen
        ).total_seconds() >= self.config.switch_debounce_seconds
        observations_ok = count >= self.config.switch_min_observations
        hold_ok = (
            self._displayed_since is None
            or (now - self._displayed_since).total_seconds()
            >= self.config.min_event_hold_seconds
        )

        if debounce_ok and observations_ok and hold_ok:
            self._pending_candidate = None
            return challenger

        # Challenger is accumulating evidence but has not yet earned the switch.
        return incumbent

    def _publish_display_change(
        self,
        new_label: str | None,
        now: datetime,
    ) -> EventMessage | None:
        """Emit a display event if the dominant label changed."""
        new_display = new_label if new_label is not None else "silence"
        if self._display_label == new_display:
            return None
        self._display_label = new_display
        self._displayed_since = now
        self._pending_candidate = None
        return self._display_event(new_display, now)

    def update(
        self,
        detections: Iterable[Detection] | None = None,
        *,
        quiet_override: bool = False,
        timestamp: datetime | None = None,
    ) -> list[EventMessage]:
        """Evaluate one lifecycle tick and return lifecycle and display events.

        Args:
            detections: Classifier results for this tick, or ``None``/empty if
                inference was skipped (e.g. during acoustic quiet).
            quiet_override: When ``True``, the activity detector has observed
                continuous quiet for ``silence_timeout_seconds``; all active
                events must end and the display must clear to ``silence``.
            timestamp: Optional timestamp for the tick; defaults to UTC now.
        """
        events: list[EventMessage] = []
        now = timestamp if timestamp is not None else datetime.now(UTC)
        detections = detections or []
        detections_by_label: dict[str, Detection] = {}
        for detection in detections:
            detections_by_label[detection.label] = detection

        # Global quiet override has precedence over per-event rules.
        if quiet_override:
            for label, state in list(self._active_events.items()):
                events.append(self._end_event(state, now))
                del self._active_events[label]
            display_event = self._publish_display_change(None, now)
            if display_event is not None:
                events.append(display_event)
            return events

        # Start new events and refresh existing ones. A score in the
        # [sustain, start) band can keep an active event alive but cannot
        # start a new one.
        for detection in detections:
            existing = self._active_events.get(detection.label)
            if existing is None:
                if detection.confidence >= self.config.start_confidence:
                    events.append(self._start_event(detection, now))
            else:
                if detection.confidence >= self.config.sustain_confidence:
                    events.append(self._refresh_event(existing, detection, now))

        # Expire events whose evidence has grown stale.
        events.extend(self._expire_old_events(now))

        # Dominant/current-event display selection.
        family_scores = self._family_scores(detections)
        new_dominant = self._select_dominant(family_scores, now)
        display_event = self._publish_display_change(new_dominant, now)
        if display_event is not None:
            events.append(display_event)

        return events

    def flush(self) -> list[EventMessage]:
        """End every active event immediately.

        Called on pipeline shutdown so Home Assistant binary sensors don't
        stay stuck "on" after the audio stream stops or errors out.
        """
        events: list[EventMessage] = []
        now = datetime.now(UTC)
        for label, state in list(self._active_events.items()):
            events.append(self._end_event(state, now))
            del self._active_events[label]
        display_event = self._publish_display_change(None, now)
        if display_event is not None:
            events.append(display_event)
        return events
