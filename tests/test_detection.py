from __future__ import annotations

import numpy as np
from app.audio.activity import ActivityConfig, ActivityDetector
from app.audio.buffer import CircularAudioBuffer
from app.classifiers.base import Detection
from app.config import AggregationConfig, ClassifierConfig
from app.detection.aggregate import EventAggregator
from app.detection.filter import filter_detections


def test_circular_buffer_append_and_window() -> None:
    buffer = CircularAudioBuffer(sample_rate=10, channels=1, buffer_seconds=1.0)
    buffer.append(np.arange(5, dtype=np.float32))
    assert buffer.filled_seconds == 0.5
    assert buffer.get_window(0.2).tolist() == [3.0, 4.0]


def test_activity_detector_thresholds() -> None:
    config = ActivityConfig(rms_threshold=0.1, peak_threshold=0.2, hold_time=0.5)
    detector = ActivityDetector(config)
    audio = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    assert not detector.should_analyze(audio)
    loud_audio = np.array([0.3, 0.3, 0.3], dtype=np.float32)
    assert detector.should_analyze(loud_audio)


def test_filter_detections_respects_include_exclude() -> None:
    detections = [
        Detection(label="Train", confidence=0.9, timestamp=None, model="yamnet"),
        Detection(label="Music", confidence=0.95, timestamp=None, model="yamnet"),
        Detection(label="Dog", confidence=0.75, timestamp=None, model="yamnet"),
    ]
    config = ClassifierConfig(
        threshold=0.8, max_results=5, include=["train", "dog"], exclude=["music"]
    )
    filtered = filter_detections(detections, config)
    assert len(filtered) == 1
    assert filtered[0].label.lower() == "train"


def test_event_aggregator_starts_and_ends() -> None:
    config = AggregationConfig(start_confidence=0.8, end_timeout=0.1)
    aggregator = EventAggregator(config)
    detection = Detection(label="train", confidence=0.9, timestamp=None, model="yamnet")
    events = aggregator.update([detection])
    assert any(event.state == "started" for event in events)
    # Simulate ended state by waiting longer than end_timeout.
    import time

    time.sleep(0.2)
    events = aggregator.update([])
    assert any(event.state == "ended" for event in events)
