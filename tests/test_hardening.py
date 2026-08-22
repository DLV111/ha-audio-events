"""Regression tests for the codebase-hardening pass.

Covers: YAMNet full-buffer windowing, entity-ID slugification, config
strictness and new options, HA client timeouts, aggregator flush-on-shutdown,
and the ffmpeg stderr drain.
"""

from __future__ import annotations

import asyncio
import wave
from pathlib import Path

import numpy as np
import pytest
from app.classifiers.yamnet import MAX_INFERENCE_FRAMES, YAMNetClassifier
from app.config import (
    AggregationConfig,
    AppConfig,
    MQTTConfig,
    WebUIConfig,
    load_config,
)
from app.detection.aggregate import EventAggregator
from app.detection.models import EventMessage
from app.homeassistant.client import DEFAULT_REQUEST_TIMEOUT, HomeAssistantClient
from app.homeassistant.discovery import (
    build_label_state_topic,
    build_mqtt_discovery_payload,
)
from app.homeassistant.entities import build_label_sensor_entity_ids, slugify_label

# ---------------------------------------------------------------------------
# YAMNet frame windowing (Fix 5)
# ---------------------------------------------------------------------------

FRAME_LEN = 15600  # YAMNet TFLite input: 0.975s @ 16kHz


def _classifier_with_frame_len() -> YAMNetClassifier:
    classifier = YAMNetClassifier.__new__(YAMNetClassifier)
    classifier.model_path = Path("unused.tflite")
    classifier.labels_path = None
    classifier.model_name = "yamnet"
    classifier._input_details = [{"shape": [FRAME_LEN], "index": 0}]
    return classifier


def test_prepare_frames_short_audio_padded_to_single_frame() -> None:
    classifier = _classifier_with_frame_len()

    frames = classifier._prepare_frames(np.zeros(1000, dtype=np.float32))

    assert len(frames) == 1
    assert frames[0].shape == (FRAME_LEN,)


def test_prepare_frames_tiles_multi_second_buffer() -> None:
    """A 3s buffer must be classified as 3+ frames, not truncated to 0.975s."""
    classifier = _classifier_with_frame_len()
    audio = np.ones(3 * 16000, dtype=np.float32)

    frames = classifier._prepare_frames(audio)

    assert len(frames) == 4  # 48000 / 15600 -> 3 full + padded remainder
    assert all(f.shape == (FRAME_LEN,) for f in frames)
    # Last frame carries the tail samples plus zero padding.
    tail = int(3 * 16000 - 3 * FRAME_LEN)
    assert frames[-1][:tail].tolist() == np.ones(tail, dtype=np.float32).tolist()
    assert frames[-1][tail:].tolist() == [0.0] * (FRAME_LEN - tail)


def test_prepare_frames_empty_audio_returns_silent_frame() -> None:
    classifier = _classifier_with_frame_len()

    frames = classifier._prepare_frames(np.zeros(0, dtype=np.float32))

    assert len(frames) == 1
    assert not frames[0].any()


def test_prepare_frames_caps_inference_cost() -> None:
    """Very large buffers must not explode inference cost."""
    classifier = _classifier_with_frame_len()
    audio = np.zeros(60 * 16000, dtype=np.float32)  # a full minute

    frames = classifier._prepare_frames(audio)

    assert len(frames) == MAX_INFERENCE_FRAMES


def test_run_inference_averages_scores_across_frames() -> None:
    classifier = _classifier_with_frame_len()

    calls: list[np.ndarray] = []

    class _FakeInterpreter:
        def set_tensor(self, index, value):
            calls.append(value.copy())

        def invoke(self):
            pass

        def get_tensor(self, index):
            # Distinguishable score per call: first frame "sees" label 7,
            # second frame label 3.
            scores = np.zeros(521, dtype=np.float32)
            scores[7 if len(calls) == 1 else 3] = 0.8
            return scores.reshape(1, 521)

    classifier.interpreter = _FakeInterpreter()
    classifier._output_details = [{"index": 0}]

    result = classifier._run_inference(
        [np.full(FRAME_LEN, 0.1, dtype=np.float32), np.full(FRAME_LEN, 0.2)]
    )

    assert result.shape == (521,)
    assert result[7] == pytest.approx(0.4)  # (0.8 + 0) / 2
    assert result[3] == pytest.approx(0.4)
    # Both frames were actually submitted to the interpreter.
    assert len(calls) == 2


# ---------------------------------------------------------------------------
# Entity ID / topic slugification (Fix 7)
# ---------------------------------------------------------------------------


def test_slugify_label_handles_yamnet_display_names() -> None:
    assert slugify_label("Child speech, kid speaking") == "child_speech_kid_speaking"
    assert (
        slugify_label("Vehicle horn, car horn, honking")
        == "vehicle_horn_car_horn_honking"
    )
    assert slugify_label("Dog") == "dog"
    assert slugify_label("  ") == "unknown"


def test_label_sensor_entity_ids_are_valid_object_ids() -> None:
    from app.config import HomeAssistantConfig

    ids = build_label_sensor_entity_ids(
        HomeAssistantConfig(entity_prefix="audio"),
        ["Dog", "Child speech, kid speaking"],
    )

    assert ids["Dog"] == "binary_sensor.audio_dog"
    assert "," not in ids["Child speech, kid speaking"]
    assert ids["Child speech, kid speaking"].startswith("binary_sensor.audio_")


def test_discovery_topics_use_slugified_labels() -> None:
    config = MQTTConfig(enabled=True, topic="audio/events")

    topic = build_label_state_topic(config, "Child speech, kid speaking")

    assert topic == "audio/events/child_speech_kid_speaking"


def test_discovery_payload_entity_id_is_valid() -> None:
    payloads = build_mqtt_discovery_payload(
        MQTTConfig(enabled=True), "audio", ["Child speech, kid speaking"]
    )

    topic, _, entity_id = payloads[0]
    assert entity_id == "binary_sensor.audio_child_speech_kid_speaking"
    assert topic.endswith(entity_id + "/config")


# ---------------------------------------------------------------------------
# Config strictness & new options (Fixes 8, 11, 15)
# ---------------------------------------------------------------------------


def test_load_config_explicit_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "does-not-exist.yaml")


def test_load_config_parses_webui_auth_token(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "webui:\n  enabled: true\n  host: 127.0.0.1\n  port: 9000\n"
        '  auth_token: "hunter2"\n',
        encoding="utf-8",
    )

    config = load_config(cfg_file)

    assert isinstance(config.webui, WebUIConfig)
    assert config.webui.auth_token == "hunter2"
    assert config.webui.port == 9000


def test_load_config_parses_mqtt_credentials_and_tls(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "mqtt:\n  enabled: true\n  username: audio\n  password: pw\n  tls: true\n",
        encoding="utf-8",
    )

    config = load_config(cfg_file)

    assert config.mqtt.username == "audio"
    assert config.mqtt.password == "pw"
    assert config.mqtt.tls is True


def test_load_config_mtls_defaults_unset() -> None:
    config = AppConfig()

    assert config.mqtt.username is None
    assert config.mqtt.password is None
    assert config.mqtt.tls is False
    assert config.webui.auth_token is None


# ---------------------------------------------------------------------------
# HA client timeout (Fix 4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ha_client_session_has_bounded_timeout() -> None:
    """Every HA request must be bounded: aiohttp's default is 5 minutes,
    which stalls the detection pipeline when Home Assistant hangs."""
    client = HomeAssistantClient(AppConfig().homeassistant)
    try:
        assert client._session.timeout.total == pytest.approx(10.0)
        assert DEFAULT_REQUEST_TIMEOUT.total == pytest.approx(10.0)
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# Aggregator flush on shutdown (Fix 9)
# ---------------------------------------------------------------------------


def _detection(label: str, confidence: float):
    from datetime import UTC, datetime

    from app.classifiers.base import Detection

    return Detection(
        label=label, confidence=confidence, timestamp=datetime.now(UTC), model="yamnet"
    )


def test_flush_ends_active_events_and_clears_state() -> None:
    aggregator = EventAggregator(AggregationConfig(start_confidence=0.5))

    aggregator.update([_detection("dog", 0.9)])
    events = aggregator.flush()

    assert len(events) == 1
    ended = events[0]
    assert isinstance(ended, EventMessage)
    assert ended.state == "ended"
    assert ended.label == "dog"
    # State must be cleared so a later flush emits nothing.
    assert aggregator.flush() == []


def test_update_after_timeout_emits_ended_once() -> None:
    from datetime import UTC, datetime, timedelta

    aggregator = EventAggregator(AggregationConfig(start_confidence=0.5))
    t0 = datetime.now(UTC)
    aggregator.update([_detection("dog", 0.9)], timestamp=t0)
    t1 = t0 + timedelta(seconds=10)

    events = aggregator.update([], timestamp=t1)

    assert [e.state for e in events] == ["ended"]
    # A second update after the end must not re-emit anything.
    assert aggregator.update([], timestamp=t1 + timedelta(seconds=10)) == []


# ---------------------------------------------------------------------------
# WAV streaming memory behaviour (Fix 17)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_wav_reads_incrementally_without_loading_whole_file(
    tmp_path: Path,
) -> None:
    """_stream_wav yields chunks as it reads instead of materialising the
    entire file in RAM first."""
    wav_path = tmp_path / "long.wav"
    sample_rate = 16000
    total_seconds = 3
    with wave.open(str(wav_path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        frames = (
            np.sin(np.linspace(0, 440 * 2 * np.pi, sample_rate * total_seconds)) * 8000
        ).astype(np.int16)
        handle.writeframes(frames.tobytes())

    from app.audio.stream import AudioStreamSource
    from app.config import AudioSourceConfig

    source = AudioStreamSource(AudioSourceConfig(sample_rate=16000, channels=1))
    chunk_sizes: list[int] = []
    async for chunk in source._stream_wav(wav_path):
        chunk_sizes.append(len(chunk))

    # 3 seconds at 0.5s chunks => several incremental chunks, each <= chunk size
    assert len(chunk_sizes) >= 2
    assert max(chunk_sizes) <= int(16000 * 0.55)


# ---------------------------------------------------------------------------
# ffmpeg stderr drain (Fix 3)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_drain_stderr_logs_lines_until_eof(caplog) -> None:
    from app.audio.stream import AudioStreamSource

    reader = asyncio.StreamReader()
    reader.feed_data(b"[rtsp @ 0x1] connection refused\n")
    reader.feed_data(b"another warning\n")
    reader.feed_eof()

    task = asyncio.create_task(AudioStreamSource._drain_stderr(reader))
    await asyncio.wait_for(task, timeout=2)

    assert any("connection refused" in r.message for r in caplog.records)
