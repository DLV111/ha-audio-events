from __future__ import annotations

import json
import logging

import paho.mqtt.client as mqtt

from app.config import MQTTConfig
from app.detection.models import EventMessage

_LOGGER = logging.getLogger(__name__)


class MQTTClient:
    def __init__(self, config: MQTTConfig) -> None:
        self.config = config
        self.client = mqtt.Client()
        self.client.loop_start()
        self.client.connect(self.config.host, self.config.port)

    def publish(self, event: EventMessage) -> None:
        payload = json.dumps(
            {
                "label": event.label,
                "confidence": event.confidence,
                "duration": event.duration,
                "state": event.state,
            }
        )
        topic = self.config.topic
        _LOGGER.info("Publishing MQTT event %s to %s", event.label, topic)
        self.client.publish(topic, payload)

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
