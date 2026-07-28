from __future__ import annotations

import json
import logging

from app.config import MQTTConfig
from app.homeassistant.entities import build_entity_ids

_LOGGER = logging.getLogger(__name__)


def build_mqtt_discovery_payload(
    config: MQTTConfig, entity_prefix: str, supported_labels: list[str]
) -> list[tuple[str, str, str]]:
    entity_ids = build_entity_ids_for_labels(entity_prefix, supported_labels)
    payloads: list[tuple[str, str, str]] = []

    for label, entity_id in entity_ids.items():
        discovery_topic = f"{config.discovery_prefix}/binary_sensor/{entity_id}/config"
        payload = {
            "name": f"{entity_prefix} {label}",
            "state_topic": config.topic,
            "value_template": "{{ value_json.state }}",
            "json_attributes_topic": config.topic,
            "unique_id": f"{entity_id}_discovery",
            "device": {
                "identifiers": [entity_prefix],
                "name": f"{entity_prefix} audio detector",
                "manufacturer": "HA Audio Events",
            },
            "payload_on": "on",
            "payload_off": "off",
        }
        payloads.append((discovery_topic, json.dumps(payload), entity_id))

    return payloads


def build_entity_ids_for_labels(entity_prefix: str, supported_labels: list[str]) -> dict[str, str]:
    return {
        label: f"binary_sensor.{entity_prefix}_{label.replace(' ', '_').lower()}"
        for label in supported_labels
    }
