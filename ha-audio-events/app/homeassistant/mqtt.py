from __future__ import annotations

import json
import logging

import paho.mqtt.client as mqtt

from app.config import MQTTConfig
from app.detection.models import EventMessage
from app.homeassistant.discovery import (
    build_label_state_topic,
    build_mqtt_discovery_payload,
    build_scalar_entity_discovery_payloads,
)

_LOGGER = logging.getLogger(__name__)


class MQTTClient:
    def __init__(self, config: MQTTConfig) -> None:
        self.config = config
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="ha-audio-events",
        )
        if config.username:
            self.client.username_pw_set(config.username, config.password)
        if config.tls:
            self.client.tls_set()

        # The most recently published discovery configs, kept so they can be
        # republished every time the broker (re)connects.
        self._discovery_payloads: list[tuple[str, str, str]] = []

        # Republishing discovery on connect is load-bearing: connect_async +
        # loop_start do not queue QoS-0 publishes while the client is still
        # connecting, so a publish issued before the CONNACK can be dropped
        # silently (a slow or briefly absent broker at startup). Publishing
        # from on_connect fires after every (re)connection instead.
        self.client.on_connect = self._on_connect

        # connect_async + loop_start makes paho retry in its network thread
        # with exponential backoff instead of crashing at startup when the
        # broker is briefly unavailable (e.g. during HA boot ordering races).
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        scheme = "mqtts" if config.tls else "mqtt"
        auth = "with credentials" if config.username else "without credentials"
        _LOGGER.info(
            "Connecting to MQTT broker %s://%s:%s (%s), retrying in background "
            "until reachable",
            scheme,
            config.host,
            config.port,
            auth,
        )
        self.client.connect_async(config.host, config.port)
        self.client.loop_start()

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None = None,
    ) -> None:
        """(Re)publish discovery once the broker has accepted the connection."""
        if getattr(reason_code, "is_failure", reason_code != 0):
            _LOGGER.warning(
                "MQTT connection refused (reason=%s); discovery not published",
                reason_code,
            )
            return
        if not self._discovery_payloads:
            # Startup path: publish_discovery() has not run yet and will
            # publish synchronously in the caller's thread.
            return
        _LOGGER.info(
            "MQTT connected; republishing %d discovery payload(s)",
            len(self._discovery_payloads),
        )
        self._publish_discovery_payloads()

    def publish_discovery(
        self, entity_prefix: str, supported_labels: list[str]
    ) -> None:
        """Publish discovery for the scalar entities + any per-label sensors.

        The two scalar entities (last event / audio active) are always-on, so
        they are published even when no include filter is configured; only
        the per-label sensors depend on ``supported_labels``, since an empty
        include list means "report every class" and has no per-label sensors.

        The payloads are cached so ``_on_connect`` can republish them on
        every reconnect.
        """
        payloads = build_scalar_entity_discovery_payloads(self.config, entity_prefix)
        payloads += build_mqtt_discovery_payload(
            self.config, entity_prefix, supported_labels
        )
        self._discovery_payloads = payloads
        self._publish_discovery_payloads()

    def _publish_discovery_payloads(self) -> None:
        for topic, payload, entity_id in self._discovery_payloads:
            _LOGGER.info("Publishing MQTT discovery for %s to %s", entity_id, topic)
            self.client.publish(topic, payload, retain=True)

    def publish(self, event: EventMessage) -> None:
        is_on = event.state != "ended" and event.label != "silence"
        payload = json.dumps(
            {
                "label": event.label,
                "confidence": event.confidence,
                "duration": event.duration,
                "state": "on" if is_on else "off",
                "model": event.model,
            }
        )

        # Retained: the two scalar entities read this topic as their state,
        # so a retained payload keeps them at their last known value across a
        # broker or Home Assistant restart instead of sitting at "unknown"
        # until the next detection. The per-label topic below retains for the
        # same reason.
        topic = self.config.topic
        _LOGGER.info("Publishing MQTT event %s to %s", event.label, topic)
        self.client.publish(topic, payload, retain=True)

        label_topic = build_label_state_topic(self.config, event.label)
        _LOGGER.info("Publishing MQTT state %s to %s", event.label, label_topic)
        self.client.publish(label_topic, payload, retain=True)

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
