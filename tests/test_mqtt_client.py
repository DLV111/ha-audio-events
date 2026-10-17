"""Tests for MQTT client."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from app.config import MQTTConfig
from app.detection.models import EventMessage
from app.homeassistant.mqtt import MQTTClient


def _connected(is_failure: bool = False) -> SimpleNamespace:
    """Stand-in for paho's ReasonCode/connack code (v3 int or v5 object)."""
    return SimpleNamespace(is_failure=is_failure)


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
    """Test MQTTClient initialization.

    connect_async (not blocking connect) must be used so a temporarily
    unavailable broker doesn't crash the add-on at startup; paho's network
    thread retries in the background.
    """
    config = _config()
    _ = MQTTClient(config)

    mock_mqtt_client.connect_async.assert_called_once_with("localhost", 1883)
    mock_mqtt_client.loop_start.assert_called_once()
    mock_mqtt_client.reconnect_delay_set.assert_called_once()


def test_mqtt_client_init_with_credentials(mock_mqtt_client):
    """Username/password and TLS options are applied to the paho client."""
    config = MQTTConfig(
        enabled=True,
        host="broker.local",
        port=8883,
        username="audio",
        password="secret",
        tls=True,
    )
    _ = MQTTClient(config)

    mock_mqtt_client.username_pw_set.assert_called_once_with("audio", "secret")
    mock_mqtt_client.tls_set.assert_called_once()
    mock_mqtt_client.connect_async.assert_called_once_with("broker.local", 8883)


def test_mqtt_client_init_without_credentials(mock_mqtt_client):
    """No username -> no credential call, no TLS call."""
    _ = MQTTClient(_config())

    mock_mqtt_client.username_pw_set.assert_not_called()
    mock_mqtt_client.tls_set.assert_not_called()


def test_mqtt_client_publish_discovery(mock_mqtt_client):
    """Test MQTT discovery publishing.

    The two scalar entities are always published (also with an empty include
    list), so the retained discovery configs exist even before any filter is
    configured; per-label sensors are added on top of them.
    """
    config = _config()
    client = MQTTClient(config)

    client.publish_discovery("audio", [])
    assert mock_mqtt_client.publish.call_count == 2
    topics = [call.args[0] for call in mock_mqtt_client.publish.call_args_list]
    assert "homeassistant/sensor/audio_last_audio_event/config" in topics
    # Node id == unique_id == "<prefix>_audio_active", so the entity keeps the
    # id it had before (binary_sensor.audio_audio_active for prefix "audio").
    assert "homeassistant/binary_sensor/audio_audio_active/config" in topics

    mock_mqtt_client.publish.reset_mock()

    client.publish_discovery("audio", ["dog", "train"])
    assert mock_mqtt_client.publish.call_count == 4
    for call in mock_mqtt_client.publish.call_args_list:
        assert call.kwargs.get("retain") is True


def test_mqtt_client_republishes_discovery_on_connect(mock_mqtt_client):
    """Discovery must be published from the connect callback, not just startup.

    connect_async + loop_start do not queue QoS-0 publishes while the client
    is still connecting, so a startup publish issued before the CONNACK can
    be dropped silently when the broker is slow or briefly absent. The
    callback paho fires after every (re)connection is where discovery is made
    durable, so it must republish the cached payloads.
    """
    client = MQTTClient(_config())

    # paho is handed the client's own callback: that wiring is the fix.
    assert mock_mqtt_client.on_connect == client._on_connect

    client.publish_discovery("audio", ["dog"])
    mock_mqtt_client.publish.reset_mock()

    # A successful CONNACK.
    mock_mqtt_client.on_connect(mock_mqtt_client, None, MagicMock(), _connected())

    topics = [call.args[0] for call in mock_mqtt_client.publish.call_args_list]
    assert topics == [
        "homeassistant/sensor/audio_last_audio_event/config",
        "homeassistant/binary_sensor/audio_audio_active/config",
        # Pre-existing quirk: the per-label discovery payload keys off the
        # entity id (which carries its domain) rather than the bare object id.
        "homeassistant/binary_sensor/binary_sensor.audio_dog/config",
    ]
    # Retained, so a broker restart keeps the discovered entities alive.
    for call in mock_mqtt_client.publish.call_args_list:
        assert call.kwargs.get("retain") is True


def test_mqtt_client_connect_before_discovery_publishes_nothing(
    mock_mqtt_client,
):
    """The startup race must be safe: a CONNACK arriving before
    publish_discovery() has cached anything logs nothing and publishes
    nothing -- the caller's own publish then runs against a connected client.
    """
    client = MQTTClient(_config())
    assert client._discovery_payloads == []

    mock_mqtt_client.on_connect(mock_mqtt_client, None, MagicMock(), _connected())

    mock_mqtt_client.publish.assert_not_called()


def test_mqtt_client_rejected_connection_skips_discovery(mock_mqtt_client, caplog):
    """A refused connection (bad credentials, broker down) must not pretend
    discovery was published -- it warns instead.
    """
    client = MQTTClient(_config())
    client.publish_discovery("audio", [])
    mock_mqtt_client.publish.reset_mock()

    with caplog.at_level(logging.WARNING, logger="app.homeassistant.mqtt"):
        mock_mqtt_client.on_connect(
            mock_mqtt_client, None, MagicMock(), _connected(is_failure=True)
        )

    mock_mqtt_client.publish.assert_not_called()
    assert any(
        "discovery not published" in record.getMessage() for record in caplog.records
    )


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

    # First call: main topic, retained -- this is the payload backing the two
    # scalar entities, so retaining it keeps them off "unknown" after a broker
    # or Home Assistant restart.
    assert calls[0].args[0] == "audio/events"
    assert calls[0].kwargs.get("retain") is True
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
