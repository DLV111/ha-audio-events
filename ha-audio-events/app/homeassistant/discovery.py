from __future__ import annotations

import json
import logging

from app.config import MQTTConfig
from app.homeassistant.entities import slugify_label

_LOGGER = logging.getLogger(__name__)


def build_label_state_topic(config: MQTTConfig, label: str) -> str:
    """Per-label state topic, so each discovered sensor only reacts to its own label."""
    return f"{config.topic}/{slugify_label(label)}"


def build_mqtt_discovery_payload(
    config: MQTTConfig, entity_prefix: str, supported_labels: list[str]
) -> list[tuple[str, str, str]]:
    entity_ids = build_entity_ids_for_labels(entity_prefix, supported_labels)
    payloads: list[tuple[str, str, str]] = []

    for label, entity_id in entity_ids.items():
        discovery_topic = f"{config.discovery_prefix}/binary_sensor/{entity_id}/config"
        label_topic = build_label_state_topic(config, label)
        payload = {
            "name": f"{entity_prefix} {label}",
            "device_class": "sound",
            "state_topic": label_topic,
            "value_template": "{{ value_json.state }}",
            "json_attributes_topic": label_topic,
            "unique_id": f"{entity_id}_discovery",
            "device": {
                "identifiers": [entity_prefix],
                "name": f"Audio Events ({entity_prefix})",
                "manufacturer": "HA Audio Events",
            },
            "payload_on": "on",
            "payload_off": "off",
        }
        payloads.append((discovery_topic, json.dumps(payload), entity_id))

    return payloads


def build_scalar_entity_discovery_payloads(
    config: MQTTConfig, entity_prefix: str
) -> list[tuple[str, str, str]]:
    """Discovery payloads for the two always-on scalar entities.

    ``sensor.<prefix>_last_audio_event`` and
    ``binary_sensor.<prefix>_audio_active`` used to be created by POSTing
    states to Home Assistant's REST API, which auto-creates entities without
    a registry ``unique_id`` -- HA then refuses to let the user manage them
    from the UI ("does not have a unique ID"). MQTT discovery can attach a
    ``unique_id``, so these two entities are published here instead.

    Both entities read the event firehose topic (``config.topic``): every
    event carries the label, confidence, duration, model and on/off state.

    Because both the entity ids and the unique ids are derived from
    ``entity_prefix``, a second audio stream simply uses its own prefix
    (e.g. ``audio_kitchen`` -> ``sensor.audio_kitchen_last_audio_event``).
    """
    device = {
        "identifiers": [entity_prefix],
        "name": f"Audio Events ({entity_prefix})",
        "manufacturer": "HA Audio Events",
    }
    friendly_prefix = entity_prefix.replace("_", " ").title()

    last_event_id = f"{entity_prefix}_last_audio_event"
    last_event_payload = {
        "name": f"{friendly_prefix} Last Audio Event",
        "state_topic": config.topic,
        "unique_id": last_event_id,
        "value_template": "{{ value_json.label }}",
        "json_attributes_topic": config.topic,
        "json_attributes_template": (
            "{{ {'label': value_json.label, 'confidence': value_json.confidence, "
            "'duration': value_json.duration, 'model': value_json.model} | tojson }}"
        ),
        "device": device,
    }

    audio_active_id = f"{entity_prefix}_audio_active"
    audio_active_payload = {
        "name": f"{friendly_prefix} Audio Active",
        "state_topic": config.topic,
        "unique_id": audio_active_id,
        "value_template": "{{ value_json.state }}",
        "device_class": "sound",
        "payload_on": "on",
        "payload_off": "off",
        "device": device,
    }

    return [
        (
            f"{config.discovery_prefix}/sensor/{last_event_id}/config",
            json.dumps(last_event_payload),
            f"sensor.{last_event_id}",
        ),
        (
            f"{config.discovery_prefix}/binary_sensor/{audio_active_id}/config",
            json.dumps(audio_active_payload),
            f"binary_sensor.{audio_active_id}",
        ),
    ]


def build_entity_ids_for_labels(
    entity_prefix: str, supported_labels: list[str]
) -> dict[str, str]:
    return {
        label: f"binary_sensor.{entity_prefix}_{slugify_label(label)}"
        for label in supported_labels
    }
