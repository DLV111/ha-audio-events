"""Tests for MQTT client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from app.config import MQTTConfig
from app.detection.models import EventMessage
from app.homeassistant.mqtt import MQTTClient


def _config() -> MQTTConfig:
    return MQTTConfig(
        enabled=True,
        host="localhost",
        port=1883,
        topic="audio/events",
        discovery_prefix="homeassistant",
    )


@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client."""
    with patch("paho.mqtt.client.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        yield mock_client


def test_mqtt_client_init(mock_mqtt_client):
    """Test MQTTClient initialization."""
    config = _config()
    _ = MQTTClient(config)

    mock_mqtt_client.loop_start.assert_called_once()
    mock_mqtt_client.connect.assert_called_once_with("localhost", 1883)


def test_mqtt_client_publish_discovery(mock_mqtt_client):
    """Test MQTT discovery publishing."""
    config = _config()
    client = MQTTClient(config)

    supported_labels = ["dog", "train"]
    client.publish_discovery("audio", supported_labels)

    assert mock_mqtt_client.publish.call_count == 2
    for call in mock_mqtt_client.publish.call_args_list:
        assert call.kwargs.get("retain") is True


def test_mqtt_client_publish_event(mock_mqtt_client):
    """Test MQTT event publishing."""
    config = _config()
    client = MQTTClient(config)

    event = EventMessage(
        event_type="audio.detected",
        label="dog",
        confidence=0.95,
        duration=30.0,
        state="started",
        model="yamnet",
    )

    client.publish(event)

    # Should publish to both the main topic and the label-specific topic
    assert mock_mqtt_client.publish.call_count == 2
    calls = mock_mqtt_client.publish.call_args_list

    # First call: main topic
    assert calls[0].args[0] == "audio/events"
    import json

    payload = json.loads(calls[0].args[1])
    assert payload["label"] == "dog"
    assert payload["state"] == "on"

    # Second call: label-specific topic with retain
    assert calls[1].args[0] == "audio/events/dog"
    assert calls[1].kwargs.get("retain") is True


def test_mqtt_client_publish_event_ended(mock_mqtt_client):
    """Test MQTT event publishing with 'ended' state."""
    config = _config()
    client = MQTTClient(config)

    event = EventMessage(
        event_type="audio.detected",
        label="dog",
        confidence=0.95,
        duration=30.0,
        state="ended",
        model="yamnet",
    )

    client.publish(event)

    import json

    payload = json.loads(mock_mqtt_client.publish.call_args_list[0].args[1])
    assert payload["state"] == "off"


def test_mqtt_client_stop(mock_mqtt_client):
    """Test MQTT client stop."""
    config = _config()
    client = MQTTClient(config)

    client.stop()

    mock_mqtt_client.loop_stop.assert_called_once()
    mock_mqtt_client.disconnect.assert_called_once()
