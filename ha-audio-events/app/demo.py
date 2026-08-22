from __future__ import annotations

import asyncio
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.audio.activity import ActivityDetector
from app.audio.buffer import CircularAudioBuffer
from app.audio.stream import AudioStreamSource
from app.classifiers.registry import build_classifier
from app.config import (
    ActivityConfig,
    AggregationConfig,
    AppConfig,
    AudioSourceConfig,
    ClassifierConfig,
    HomeAssistantConfig,
    MQTTConfig,
    load_config,
)
from app.detection.aggregate import EventAggregator
from app.detection.filter import filter_detections
from app.detection.models import EventMessage


def format_file_result(path: str, label: str, duration: float) -> str:
    return f"file {path} - {label} - {duration:.1f}s"


def _prepare_audio_for_demo(audio_path: str) -> str:
    source = Path(audio_path)
    if source.suffix.lower() == ".wav":
        return str(source)

    output = Path("/tmp") / f"{source.stem}.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-f",
            "wav",
            str(output),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return str(output)


async def run_demo(audio_path: str) -> list[str]:
    base_config = load_config(Path("config.yaml"))
    converted_path = _prepare_audio_for_demo(audio_path)
    config = AppConfig(
        model=base_config.model,
        buffer_seconds=base_config.buffer_seconds,
        audio=AudioSourceConfig(
            sample_rate=16000,
            channels=1,
            format="pcm_s16le",
            source_path=converted_path,
        ),
        activity=ActivityConfig(
            rms_threshold=0.001, peak_threshold=0.001, hold_time=0.5
        ),
        classifier=ClassifierConfig(
            threshold=0.05, max_results=5, include=[], exclude=["music", "silence"]
        ),
        aggregation=AggregationConfig(start_confidence=0.05, end_timeout=2.0),
        homeassistant=HomeAssistantConfig(
            enabled=False,
            url=base_config.homeassistant.url,
            token=base_config.homeassistant.token,
            entity_prefix=base_config.homeassistant.entity_prefix,
        ),
        mqtt=MQTTConfig(
            enabled=False,
            host=base_config.mqtt.host,
            port=base_config.mqtt.port,
            topic=base_config.mqtt.topic,
            discovery_prefix=base_config.mqtt.discovery_prefix,
        ),
        log_level=base_config.log_level,
    )

    buffer = CircularAudioBuffer(
        sample_rate=config.audio.sample_rate,
        channels=config.audio.channels,
        buffer_seconds=config.buffer_seconds,
    )
    detector = ActivityDetector(config.activity)
    classifier = build_classifier(config)
    source = AudioStreamSource(config.audio)
    aggregator = EventAggregator(config.aggregation)

    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    stream_time = 0.0
    last_seen_event: dict[str, EventMessage] = {}

    async for chunk in source.stream():
        chunk_seconds = len(chunk) / config.audio.sample_rate
        stream_time += chunk_seconds
        current_dt = base_time + timedelta(seconds=stream_time)
        buffer.append(chunk)
        window = buffer.get_window(config.buffer_seconds)
        if not detector.should_analyze(window):
            continue

        detections = await classifier.classify(window)
        filtered = filter_detections(detections, config.classifier)
        events = aggregator.update(filtered, timestamp=current_dt)
        for event in events:
            last_seen_event[event.label] = event

    if not last_seen_event:
        return [format_file_result(Path(audio_path).name, "unknown", 0.0)]

    results: list[str] = []
    sorted_events = sorted(
        last_seen_event.values(),
        key=lambda e: e.duration,
        reverse=True,
    )
    for event in sorted_events:
        results.append(
            format_file_result(Path(audio_path).name, event.label, event.duration)
        )

    return results


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m app.demo <audio-file> [audio-file ...]")
        raise SystemExit(1)

    results: list[str] = []
    for audio_path in sys.argv[1:]:
        results.extend(asyncio.run(run_demo(audio_path)))

    for item in results:
        print(item)


if __name__ == "__main__":
    main()
