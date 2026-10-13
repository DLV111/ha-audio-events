from __future__ import annotations

import json

from app.config import MQTTConfig
from app.homeassistant.discovery import (
    build_label_state_topic,
    build_mqtt_discovery_payload,
    build_scalar_entity_discovery_payloads,
)


def _config(topic: str = "audio/events") -> MQTTConfig:
    return MQTTConfig(
        enabled=True,
        host="localhost",
        port=1883,
        topic=topic,
        discovery_prefix="homeassistant",
    )


def _payloads(prefix: str, topic: str = "audio/events") -> dict[str, tuple[str, dict]]:
    """Map entity_id -> (discovery topic, parsed payload)."""
    return {
        entity_id: (discovery_topic, json.loads(payload))
        for discovery_topic, payload, entity_id in build_scalar_entity_discovery_payloads(
            _config(topic), prefix
        )
    }


def test_label_state_topics_are_unique_per_label() -> None:
    config = _config()
    labels = ["dog", "train", "siren"]

    topics = {label: build_label_state_topic(config, label) for label in labels}

    assert len(set(topics.values())) == len(labels)
    for label, topic in topics.items():
        assert topic == f"audio/events/{label}"


def test_discovery_payloads_use_per_label_topics_not_shared_topic() -> None:
    config = _config()
    labels = ["dog", "train"]

    payloads = build_mqtt_discovery_payload(config, "audio", labels)

    assert len(payloads) == 2
    state_topics = set()
    for _discovery_topic, payload_json, _entity_id in payloads:
        payload = json.loads(payload_json)
        # Each entity must have its own state topic, not the shared firehose topic,
        # otherwise every discovered sensor mirrors whichever label last fired.
        assert payload["state_topic"] != config.topic
        state_topics.add(payload["state_topic"])

    assert len(state_topics) == len(labels)


def test_scalar_discovery_payloads_structure() -> None:
    """The two scalar entities must be discoverable with unique_ids, templates
    and a shared device block. They used to be REST-created, which left Home
    Assistant telling the user they "does not have a unique ID" -- the exact
    warning this discovery payload set exists to remove."""
    payloads = _payloads("audio")

    assert set(payloads) == {
        "sensor.audio_last_audio_event",
        "binary_sensor.audio_audio_active",
    }

    sensor_topic, sensor = payloads["sensor.audio_last_audio_event"]
    assert sensor_topic == "homeassistant/sensor/audio_last_audio_event/config"
    assert sensor["unique_id"] == "audio_last_audio_event"
    assert sensor["state_topic"] == "audio/events"
    assert sensor["value_template"] == "{{ value_json.label }}"
    assert sensor["json_attributes_topic"] == "audio/events"
    for field in ("label", "confidence", "duration", "model"):
        assert field in sensor["json_attributes_template"]

    binary_topic, binary = payloads["binary_sensor.audio_audio_active"]
    assert binary_topic == "homeassistant/binary_sensor/audio_audio_active/config"
    assert binary["unique_id"] == "audio_audio_active"
    assert binary["state_topic"] == "audio/events"
    assert binary["value_template"] == "{{ value_json.state }}"
    assert binary["device_class"] == "sound"
    assert binary["payload_on"] == "on"
    assert binary["payload_off"] == "off"

    expected_device = {
        "identifiers": ["audio"],
        "name": "audio audio detector",
        "manufacturer": "HA Audio Events",
    }
    assert sensor["device"] == expected_device
    assert binary["device"] == expected_device


def test_scalar_entities_unique_across_prefixes() -> None:
    """Two audio streams must never collide: both the entity ids and the
    unique_ids are derived from entity_prefix."""
    first = _payloads("audio_a")
    second = _payloads("audio_b")

    assert not set(first) & set(second)

    first_unique = {payload["unique_id"] for _topic, payload in first.values()}
    second_unique = {payload["unique_id"] for _topic, payload in second.values()}
    assert not first_unique & second_unique

    for entity_id in first:
        assert "audio_a" in entity_id
    for entity_id in second:
        assert "audio_b" in entity_id
    for unique_id in first_unique:
        assert unique_id.startswith("audio_a_")
    for unique_id in second_unique:
        assert unique_id.startswith("audio_b_")

    first_topics = {topic for topic, _payload in first.values()}
    second_topics = {topic for topic, _payload in second.values()}
    assert not first_topics & second_topics


def test_scalar_discovery_topics_respect_config_topic() -> None:
    """The scalar entities read the event firehose (config.topic), not a
    per-label sub-topic: they are not label-specific sensors."""
    config = _config(topic="kitchen/audio")
    payloads = build_scalar_entity_discovery_payloads(config, "audio_kitchen")

    label_topic = build_label_state_topic(config, "dog")

    for _discovery_topic, payload_json, _entity_id in payloads:
        payload = json.loads(payload_json)
        assert payload["state_topic"] == "kitchen/audio"
        assert payload["state_topic"] != label_topic
