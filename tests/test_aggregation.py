"""ADR-45 acceptance tests for the stable audio-event aggregator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.classifiers.base import Detection
from app.config import AggregationConfig
from app.detection.aggregate import EventAggregator


def _det(label: str, confidence: float) -> Detection:
    return Detection(label=label, confidence=confidence, timestamp=None, model="yamnet")


def _default_config(**kwargs: float) -> AggregationConfig:
    defaults: dict[str, float | int] = {
        "start_confidence": 0.85,
        "sustain_confidence": 0.70,
        "switch_margin": 0.10,
        "switch_debounce_seconds": 1.0,
        "switch_min_observations": 2,
        "min_event_hold_seconds": 2.0,
        "end_timeout": 5.0,
        "silence_timeout_seconds": 5.0,
        "activation_delay_seconds": 0.0,
        "candidate_max_observation_gap_seconds": 2.0,
    }
    defaults.update(kwargs)
    return AggregationConfig(**defaults)


def _display_event(events: list[object]) -> object | None:
    for event in events:
        if getattr(event, "is_display", False):
            return event
    return None


def _lifecycle_events(events: list[object]) -> list[object]:
    return [e for e in events if not getattr(e, "is_display", False)]


class TestConfigValidation:
    def test_sustain_must_be_below_start(self) -> None:
        with pytest.raises(ValueError):
            AggregationConfig(start_confidence=0.7, sustain_confidence=0.7)

    def test_confidence_bounds_enforced(self) -> None:
        with pytest.raises(ValueError):
            AggregationConfig(start_confidence=1.1)
        with pytest.raises(ValueError):
            AggregationConfig(sustain_confidence=-0.1)

    def test_negative_timeout_rejected(self) -> None:
        with pytest.raises(ValueError):
            AggregationConfig(end_timeout=-1.0)

    def test_switch_min_observations_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            AggregationConfig(switch_min_observations=0)


class TestStartupAndIdle:
    def test_startup_no_event_publishes_silence_display(self) -> None:
        aggregator = EventAggregator(_default_config())
        now = datetime(2026, 10, 26, tzinfo=UTC)
        events = aggregator.update([], timestamp=now)
        display = _display_event(events)
        assert display is not None
        assert display.label == "silence"
        assert display.state == "current"

    def test_repeated_idle_ticks_do_not_repeat_silence(self) -> None:
        aggregator = EventAggregator(_default_config())
        now = datetime(2026, 10, 26, tzinfo=UTC)
        aggregator.update([], timestamp=now)
        events = aggregator.update([], timestamp=now + timedelta(seconds=1))
        assert _display_event(events) is None
        assert _lifecycle_events(events) == []


class TestConfidenceBoundaries:
    def test_inactive_just_below_then_at_start(self) -> None:
        aggregator = EventAggregator(_default_config())
        now = datetime(2026, 10, 26, tzinfo=UTC)
        events = aggregator.update([_det("Thunder", 0.849)], timestamp=now)
        assert not any(e.state == "started" for e in _lifecycle_events(events))
        events = aggregator.update(
            [_det("Thunder", 0.850)], timestamp=now + timedelta(seconds=1)
        )
        assert any(e.state == "started" for e in _lifecycle_events(events))

    def test_active_sustains_at_threshold_but_not_below(self) -> None:
        aggregator = EventAggregator(_default_config(min_event_hold_seconds=0.0))
        now = datetime(2026, 10, 26, tzinfo=UTC)
        aggregator.update([_det("Thunder", 0.85)], timestamp=now)
        events = aggregator.update(
            [_det("Thunder", 0.70)], timestamp=now + timedelta(seconds=1)
        )
        assert any(e.state == "active" for e in _lifecycle_events(events))
        events = aggregator.update(
            [_det("Thunder", 0.699)], timestamp=now + timedelta(seconds=2)
        )
        assert not any(e.state == "active" for e in _lifecycle_events(events))
        # Expiration is from last refresh at t=1, so ends at t=6.
        events = aggregator.update([], timestamp=now + timedelta(seconds=6.1))
        assert any(e.state == "ended" for e in _lifecycle_events(events))


class TestQuietOverride:
    def test_global_quiet_ends_active_event(self) -> None:
        config = _default_config(min_event_hold_seconds=0.0)
        aggregator = EventAggregator(config)
        now = datetime(2026, 10, 26, tzinfo=UTC)
        aggregator.update([_det("Thunder", 0.90)], timestamp=now)
        events = aggregator.update(
            [], quiet_override=True, timestamp=now + timedelta(seconds=6)
        )
        assert any(e.state == "ended" for e in _lifecycle_events(events))
        display = _display_event(events)
        assert display is not None
        assert display.label == "silence"

    def test_quiet_override_precedes_end_timeout(self) -> None:
        config = _default_config(end_timeout=10.0, silence_timeout_seconds=5.0)
        aggregator = EventAggregator(config)
        now = datetime(2026, 10, 26, tzinfo=UTC)
        aggregator.update([_det("Thunder", 0.90)], timestamp=now)
        events = aggregator.update(
            [], quiet_override=True, timestamp=now + timedelta(seconds=5)
        )
        assert any(e.state == "ended" for e in _lifecycle_events(events))

    def test_sound_return_at_quiet_deadline_resets(self) -> None:
        """ADR-45 B.5: fresh non-quiet observation at deadline resets quiet."""
        aggregator = EventAggregator(_default_config())
        now = datetime(2026, 10, 26, tzinfo=UTC)
        aggregator.update([_det("Thunder", 0.90)], timestamp=now)
        events = aggregator.update(
            [_det("Thunder", 0.90)],
            quiet_override=False,
            timestamp=now + timedelta(seconds=5),
        )
        assert not any(e.state == "ended" for e in _lifecycle_events(events))


class TestThunderThunderstormCanonicalization:
    def test_alternating_members_keep_one_family_display(self) -> None:
        aggregator = EventAggregator(_default_config())
        now = datetime(2026, 10, 26, tzinfo=UTC)
        events = aggregator.update(
            [_det("Thunder", 0.92), _det("Thunderstorm", 0.89)], timestamp=now
        )
        lifecycle = _lifecycle_events(events)
        assert sum(1 for e in lifecycle if e.state == "started") == 2
        display = _display_event(events)
        assert display is not None
        assert display.label == "Thunder"

        events = aggregator.update(
            [_det("Thunder", 0.89), _det("Thunderstorm", 0.92)],
            timestamp=now + timedelta(seconds=1),
        )
        display = _display_event(events)
        assert display is None


class TestDominantSwitching:
    def test_challenger_without_margin_keeps_incumbent(self) -> None:
        aggregator = EventAggregator(_default_config())
        now = datetime(2026, 10, 26, tzinfo=UTC)
        aggregator.update([_det("Thunder", 0.90)], timestamp=now)
        events = aggregator.update(
            [_det("Thunder", 0.90), _det("Dog", 0.94)],
            timestamp=now + timedelta(seconds=1),
        )
        display = _display_event(events)
        assert display is None or display.label == "Thunder"

    def test_challenger_switches_after_debounce_and_two_observations(self) -> None:
        aggregator = EventAggregator(_default_config())
        now = datetime(2026, 10, 26, tzinfo=UTC)
        aggregator.update([_det("Thunder", 0.85)], timestamp=now)
        aggregator.update(
            [_det("Thunder", 0.85), _det("Dog", 0.95)],
            timestamp=now + timedelta(seconds=3),
        )
        events = aggregator.update(
            [_det("Thunder", 0.85), _det("Dog", 0.95)],
            timestamp=now + timedelta(seconds=4),
        )
        display = _display_event(events)
        assert display is not None
        assert display.label == "Dog"

    def test_failed_observation_resets_pending_candidate(self) -> None:
        aggregator = EventAggregator(_default_config())
        now = datetime(2026, 10, 26, tzinfo=UTC)
        aggregator.update([_det("Thunder", 0.85)], timestamp=now)
        aggregator.update([_det("Dog", 0.95)], timestamp=now + timedelta(seconds=3))
        aggregator.update(
            [_det("Thunder", 0.85), _det("Dog", 0.75)],
            timestamp=now + timedelta(seconds=3.5),
        )
        events = aggregator.update(
            [_det("Dog", 0.95)], timestamp=now + timedelta(seconds=4)
        )
        display = _display_event(events)
        assert display is None

    def test_display_hold_prevents_early_switch(self) -> None:
        aggregator = EventAggregator(_default_config())
        now = datetime(2026, 10, 26, tzinfo=UTC)
        aggregator.update([_det("Thunder", 0.85)], timestamp=now)
        aggregator.update([_det("Dog", 0.95)], timestamp=now + timedelta(seconds=0.5))
        events = aggregator.update(
            [_det("Dog", 0.95)], timestamp=now + timedelta(seconds=1.5)
        )
        display = _display_event(events)
        assert display is None
        events = aggregator.update(
            [_det("Dog", 0.95)], timestamp=now + timedelta(seconds=2)
        )
        display = _display_event(events)
        assert display is not None
        assert display.label == "Dog"


class TestOverlapAndFallback:
    def test_unrelated_events_can_both_be_active(self) -> None:
        aggregator = EventAggregator(_default_config())
        now = datetime(2026, 10, 26, tzinfo=UTC)
        events = aggregator.update(
            [_det("Speech", 0.90), _det("Dog", 0.85)], timestamp=now
        )
        lifecycle = _lifecycle_events(events)
        started = [e.label for e in lifecycle if e.state == "started"]
        assert "Speech" in started
        assert "Dog" in started

    def test_incumbent_expiry_falls_back_to_active_event(self) -> None:
        config = _default_config(min_event_hold_seconds=0.0)
        aggregator = EventAggregator(config)
        now = datetime(2026, 10, 26, tzinfo=UTC)
        # Thunder starts, Dog starts a bit later.
        aggregator.update([_det("Thunder", 0.90)], timestamp=now)
        aggregator.update(
            [_det("Thunder", 0.90), _det("Dog", 0.95)],
            timestamp=now + timedelta(seconds=1),
        )
        # Let Thunder expire while Dog keeps qualifying.
        events = aggregator.update(
            [_det("Dog", 0.95)], timestamp=now + timedelta(seconds=6)
        )
        ended = [e.label for e in _lifecycle_events(events) if e.state == "ended"]
        assert "Thunder" in ended
        display = _display_event(events)
        assert display is not None
        assert display.label == "Dog"

    def test_low_confidence_sound_lets_event_expire(self) -> None:
        config = _default_config(min_event_hold_seconds=0.0)
        aggregator = EventAggregator(config)
        now = datetime(2026, 10, 26, tzinfo=UTC)
        aggregator.update([_det("Thunder", 0.90)], timestamp=now)
        events = aggregator.update(
            [_det("Thunder", 0.50)], timestamp=now + timedelta(seconds=6)
        )
        assert any(e.state == "ended" for e in _lifecycle_events(events))
        display = _display_event(events)
        assert display is not None
        assert display.label == "silence"


class TestNoDuplicatePublications:
    def test_expired_event_does_not_re_end(self) -> None:
        config = _default_config(min_event_hold_seconds=0.0)
        aggregator = EventAggregator(config)
        now = datetime(2026, 10, 26, tzinfo=UTC)
        aggregator.update([_det("Thunder", 0.90)], timestamp=now)
        events = aggregator.update([], timestamp=now + timedelta(seconds=6))
        assert sum(1 for e in _lifecycle_events(events) if e.state == "ended") == 1
        events = aggregator.update([], timestamp=now + timedelta(seconds=7))
        assert not any(e.state == "ended" for e in _lifecycle_events(events))


class TestEndedDurationSustained:
    def test_ended_event_duration_includes_grace_period(self) -> None:
        config = _default_config(min_event_hold_seconds=0.0, end_timeout=5.0)
        aggregator = EventAggregator(config)
        now = datetime(2026, 10, 26, tzinfo=UTC)
        aggregator.update([_det("Thunder", 0.90)], timestamp=now)
        events = aggregator.update([], timestamp=now + timedelta(seconds=5.0))
        ended = [e for e in _lifecycle_events(events) if e.state == "ended"]
        assert len(ended) == 1
        assert ended[0].duration == pytest.approx(5.0)

    def test_ended_event_duration_includes_min_hold(self) -> None:
        config = _default_config(min_event_hold_seconds=3.0, end_timeout=0.0)
        aggregator = EventAggregator(config)
        now = datetime(2026, 10, 26, tzinfo=UTC)
        aggregator.update([_det("Thunder", 0.90)], timestamp=now)
        events = aggregator.update([], timestamp=now + timedelta(seconds=3.0))
        ended = [e for e in _lifecycle_events(events) if e.state == "ended"]
        assert len(ended) == 1
        assert ended[0].duration == pytest.approx(3.0)
