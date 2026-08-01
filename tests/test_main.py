from __future__ import annotations

import numpy as np

from app.classifiers.registry import build_classifier
from app.config import AppConfig
from app.demo import format_file_result
from app.detection.models import EventMessage
from app.main import format_event_summary


def test_format_event_summary_uses_label_and_duration() -> None:
    event = EventMessage(
        event_type="audio.detected",
        label="train",
        confidence=0.95,
        duration=30.0,
        state="ended",
        model="yamnet",
    )

    assert format_event_summary(event) == "train - 30.0s"


def test_prepare_waveform_matches_model_input_shape() -> None:
    classifier = build_classifier(AppConfig(model="yamnet"))
    expected_len = int(classifier._input_details[0]["shape"][0])

    waveform = classifier._prepare_waveform(np.zeros(1000, dtype=np.float32))

    assert waveform.shape == (expected_len,)


def test_format_file_result() -> None:
    assert format_file_result("clip.wav", "train", 30.0) == "file clip.wav - train - 30.0s"
