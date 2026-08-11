from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from app.addon_mgr import AddonManager
from app.audio.activity import ActivityDetector
from app.audio.buffer import CircularAudioBuffer
from app.audio.stream import AudioStreamSource
from app.classifiers.registry import build_classifier
from app.config import AppConfig, load_config
from app.detection.aggregate import EventAggregator
from app.detection.filter import filter_detections
from app.homeassistant.client import HomeAssistantClient
from app.homeassistant.entities import (
    build_attributes,
    build_entity_ids,
    build_friendly_names,
    build_label_friendly_names,
    build_label_sensor_entity_ids,
)
from app.homeassistant.mqtt import MQTTClient
from app.utils.logging import configure_logging
from app.webui.server import WebUI

_LOGGER = logging.getLogger(__name__)


def format_event_summary(event: object) -> str:
    label = getattr(event, "label", "unknown")
    duration = getattr(event, "duration", 0.0)
    return f"{label} - {duration:.1f}s"


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
    ha_client = (
        HomeAssistantClient(config.homeassistant)
        if config.homeassistant.enabled
        else None
    )
    entity_ids = build_entity_ids(config.homeassistant)
    label_sensor_ids = build_label_sensor_entity_ids(
        config.homeassistant, config.classifier.include
    )
    friendly_names = build_friendly_names(config.homeassistant)
    label_friendly_names = build_label_friendly_names(
        config.homeassistant, config.classifier.include
    )
    source = AudioStreamSource(config.audio, ha_config=config.homeassistant)

    if mqtt_client is not None and config.classifier.include:
        mqtt_client.publish_discovery(
            config.homeassistant.entity_prefix, config.classifier.include
        )

    async def _detect() -> None:
        async for chunk in source.stream():
            buffer.append(chunk)
            window = buffer.get_window(config.buffer_seconds)
            if not detector.should_analyze(window):
                continue

            detections = await classifier.classify(window)
            filtered = filter_detections(detections, config.classifier)
            events = aggregator.update(filtered)

            for event in events:
                _LOGGER.info("Detected event: %s", format_event_summary(event))
                if ha_client is not None:
                    await ha_client.fire_event(event)
                    await ha_client.update_state(
                        entity_ids["last_audio_event"],
                        event.label,
                        build_attributes(
                            event, friendly_name=friendly_names["last_audio_event"]
                        ),
                    )
                    await ha_client.update_state(
                        entity_ids["last_audio_confidence"],
                        f"{event.confidence:.2f}",
                        {
                            "label": event.label,
                            "friendly_name": friendly_names["last_audio_confidence"],
                        },
                    )
                    await ha_client.update_state(
                        entity_ids["audio_model"],
                        event.model,
                        {
                            "label": event.label,
                            "friendly_name": friendly_names["audio_model"],
                        },
                    )
                    await ha_client.update_state(
                        entity_ids["audio_event_duration"],
                        f"{event.duration:.2f}",
                        {
                            "label": event.label,
                            "friendly_name": friendly_names["audio_event_duration"],
                        },
                    )
                    await ha_client.update_state(
                        entity_ids["audio_active"],
                        "on" if event.state != "ended" else "off",
                        {
                            "label": event.label,
                            "friendly_name": friendly_names["audio_active"],
                            "device_class": "sound",
                        },
                    )
                    if event.label in label_sensor_ids:
                        await ha_client.update_state(
                            label_sensor_ids[event.label],
                            "on" if event.state != "ended" else "off",
                            {
                                "label": event.label,
                                "confidence": str(event.confidence),
                                "friendly_name": label_friendly_names.get(
                                    event.label, event.label
                                ),
                                "device_class": "sound",
                            },
                        )
                if mqtt_client is not None:
                    mqtt_client.publish(event)

        if ha_client is not None:
            await ha_client.close()
        if mqtt_client is not None:
            mqtt_client.stop()

    if config.webui.enabled:
        # The webui needs to query Home Assistant (to list camera entities)
        # regardless of whether homeassistant.enabled is set for event
        # publishing, so give it its own client if one wasn't already created.
        webui_ha_client = ha_client or HomeAssistantClient(config.homeassistant)
        supervisor_token = os.getenv("SUPERVISOR_TOKEN", "")
        addon_mgr = AddonManager(supervisor_token)
        webui = WebUI(webui_ha_client, addon_mgr)
        # Run the detection loop and the webui concurrently. The webui must
        # stay reachable even if the audio pipeline itself fails or exits
        # (e.g. a bad source_path) so the user can fix the source from the
        # ingress panel -- it must not be started only after pipeline
        # cleanup, and its task must actually be awaited, or the process
        # exits (and the task gets cancelled) as soon as _detect() returns.
        try:
            await asyncio.gather(
                _detect(),
                webui.start(host=config.webui.host, port=config.webui.port),
            )
        finally:
            await addon_mgr.close()
            if webui_ha_client is not ha_client:
                await webui_ha_client.close()
    else:
        await _detect()


def main_sync() -> None:
    config = load_config()
    configure_logging(config.log_level)
    _LOGGER.info("Starting HA Audio Events add-on")
    try:
        asyncio.run(_run_pipeline(config))
    except KeyboardInterrupt:
        _LOGGER.info("Shutting down HA Audio Events add-on")
    except Exception:
        _LOGGER.exception("Unhandled error in HA Audio Events")


if __name__ == "__main__":
    main_sync()
