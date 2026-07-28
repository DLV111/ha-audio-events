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
from app.homeassistant.client import HomeAssistantClient
from app.homeassistant.entities import (
    build_entity_ids,
    build_label_sensor_entity_ids,
    build_attributes,
)
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
    ha_client = HomeAssistantClient(config.homeassistant) if config.homeassistant.enabled else None
    entity_ids = build_entity_ids(config.homeassistant)
    label_sensor_ids = build_label_sensor_entity_ids(config.homeassistant, config.classifier.include)
    source = AudioStreamSource(config.audio)

    if mqtt_client is not None and config.classifier.include:
        mqtt_client.publish_discovery(config.homeassistant.entity_prefix, config.classifier.include)

    async for chunk in source.stream():
        buffer.append(chunk)
        window = buffer.get_window(config.buffer_seconds)
        if not detector.should_analyze(window):
            continue

        detections = await classifier.classify(window)
        filtered = filter_detections(detections, config.classifier)
        events = aggregator.update(filtered)

        for event in events:
            if ha_client is not None:
                await ha_client.fire_event(event)
                await ha_client.update_state(
                    entity_ids["last_audio_event"],
                    event.label,
                    build_attributes(event),
                )
                await ha_client.update_state(
                    entity_ids["last_audio_confidence"],
                    f"{event.confidence:.2f}",
                    {"label": event.label},
                )
                await ha_client.update_state(
                    entity_ids["audio_model"],
                    event.model,
                    {"label": event.label},
                )
                await ha_client.update_state(
                    entity_ids["audio_event_duration"],
                    f"{event.duration:.2f}",
                    {"label": event.label},
                )
                await ha_client.update_state(
                    entity_ids["audio_active"],
                    "on" if event.state != "ended" else "off",
                    {"label": event.label},
                )
                if event.label in label_sensor_ids:
                    await ha_client.update_state(
                        label_sensor_ids[event.label],
                        "on" if event.state != "ended" else "off",
                        {"label": event.label, "confidence": str(event.confidence)},
                    )
            if mqtt_client is not None:
                mqtt_client.publish(event)

    if ha_client is not None:
        await ha_client.close()
    if mqtt_client is not None:
        mqtt_client.stop()


def main_sync() -> None:
    config = load_config(Path("config.yaml"))
    configure_logging(config.log_level)
    _LOGGER.info("Starting HA Audio Events add-on")
    try:
        asyncio.run(_run_pipeline(config))
    except KeyboardInterrupt:
        _LOGGER.info("Shutting down HA Audio Events add-on")
    except Exception:
        _LOGGER.exception("Unhandled error in HA Audio Events")
