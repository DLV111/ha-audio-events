from __future__ import annotations

from app.config import MQTTConfig
from app.homeassistant.discovery import build_label_state_topic, build_mqtt_discovery_payload


def _config() -> MQTTConfig:
    return MQTTConfig(
        enabled=True,
        host="localhost",
        port=1883,
        topic="audio/events",
        discovery_prefix="homeassistant",
    )


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
        import json

        payload = json.loads(payload_json)
        # Each entity must have its own state topic, not the shared firehose topic,
        # otherwise every discovered sensor mirrors whichever label last fired.
        assert payload["state_topic"] != config.topic
        state_topics.add(payload["state_topic"])

    assert len(state_topics) == len(labels)
