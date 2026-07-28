from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.config import AppConfig, load_config
from app.classifiers.registry import build_classifier
from app.audio.activity import ActivityDetector
from app.audio.buffer import CircularAudioBuffer
from app.audio.stream import AudioStreamSource
from app.detection.aggregate import EventAggregator
from app.detection.filter import filter_detections
from app.homeassistant.events import publish_event
from app.homeassistant.mqtt import MQTTClient
from app.utils.logging import configure_logging

_LOGGER = logging.getLogger(__name__)


async def _run_pipeline(config: AppConfig) -> None:
    buffer = CircularAudioBuffer(
        sample_rate=config.audio.sample_rate,
        channels=config.audio.channels,
        buffer_seconds=config.buffer_seconds,
    )
    detector = ActivityDetector(config.activity)
    classifier = build_classifier(config)
    aggregator = EventAggregator(config.aggregation)
    mqtt_client = MQTTClient(config.mqtt) if config.mqtt.enabled else None
    source = AudioStreamSource(config.audio)

    async for chunk in source.stream():
        buffer.append(chunk)
        window = buffer.get_window(config.buffer_seconds)
        if not detector.should_analyze(window):
            continue

        detections = await classifier.classify(window)
        filtered = filter_detections(detections, config.classifier)
        events = aggregator.update(filtered)

        for event in events:
            publish_event(event)
            if mqtt_client is not None:
                mqtt_client.publish(event)

    if mqtt_client is not None:
        mqtt_client.stop()


def main_sync() -> None:
    config = load_config(Path("addon/config.yaml"))
    configure_logging(config.log_level)
    _LOGGER.info("Starting HA Audio Events add-on")
    try:
        asyncio.run(_run_pipeline(config))
    except KeyboardInterrupt:
        _LOGGER.info("Shutting down HA Audio Events add-on")
    except Exception:
        _LOGGER.exception("Unhandled error in HA Audio Events")
