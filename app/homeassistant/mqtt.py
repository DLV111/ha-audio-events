from __future__ import annotations

import json
import logging
from typing import Iterable

import paho.mqtt.client as mqtt

from app.config import MQTTConfig
from app.detection.models import EventMessage
from app.homeassistant.discovery import build_mqtt_discovery_payload

_LOGGER = logging.getLogger(__name__)


class MQTTClient:
    def __init__(self, config: MQTTConfig) -> None:
        self.config = config
        self.client = mqtt.Client()
        self.client.loop_start()
        self.client.connect(self.config.host, self.config.port)

    def publish_discovery(self, entity_prefix: str, supported_labels: list[str]) -> None:
        payloads = build_mqtt_discovery_payload(self.config, entity_prefix, supported_labels)
        for topic, payload, entity_id in payloads:
            _LOGGER.info("Publishing MQTT discovery for %s to %s", entity_id, topic)
            self.client.publish(topic, payload, retain=True)

    def publish(self, event: EventMessage) -> None:
        payload = json.dumps(
            {
                "label": event.label,
                "confidence": event.confidence,
                "duration": event.duration,
                "state": event.state,
                "model": event.model,
            }
        )
        topic = self.config.topic
        _LOGGER.info("Publishing MQTT event %s to %s", event.label, topic)
        self.client.publish(topic, payload)

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
