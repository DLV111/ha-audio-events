from __future__ import annotations

import re

from app.config import HomeAssistantConfig
from app.detection.models import EventMessage


def slugify_label(label: str) -> str:
    """Convert an audio label into a valid Home Assistant object_id slug.

    YAMNet display names contain spaces, commas and other characters that are
    not allowed in entity IDs (e.g. "Child speech, kid speaking"), so replace
    every invalid run with a single underscore.
    """
    slug = re.sub(r"[^a-z0-9_]+", "_", label.lower()).strip("_")
    return slug or "unknown"


def build_entity_ids(config: HomeAssistantConfig) -> dict[str, str]:
    prefix = config.entity_prefix
    return {
        "last_audio_event": f"sensor.{prefix}_last_audio_event",
        "audio_active": f"binary_sensor.{prefix}_audio_active",
    }


def build_label_sensor_entity_ids(
    config: HomeAssistantConfig, labels: list[str]
) -> dict[str, str]:
    prefix = config.entity_prefix
    return {label: f"binary_sensor.{prefix}_{slugify_label(label)}" for label in labels}


def build_rest_entity_ids(config: HomeAssistantConfig) -> set[str]:
    """Entity IDs this add-on deliberately owns via the HA REST API.

    REST state POSTs (``/api/states/<entity_id>``) auto-create entities, but
    they can never attach a registry ``unique_id`` -- Home Assistant then
    tells the user the entity "does not have a unique ID, therefore its
    settings cannot be managed from the UI". Everything this add-on owns is
    therefore published through MQTT discovery instead (see
    ``app.homeassistant.discovery``), and this set is empty.

    It is kept as the single, explicit place to declare a future entity that
    genuinely cannot be MQTT-discovered: add its entity id here and
    ``HomeAssistantClient.init_entities()`` will create it over REST.
    """
    return set()


def build_friendly_names(config: HomeAssistantConfig) -> dict[str, str]:
    prefix = config.entity_prefix.replace("_", " ").title()
    return {
        "last_audio_event": f"{prefix} Last Audio Event",
        "audio_active": f"{prefix} Audio Active",
    }


def build_label_friendly_names(
    config: HomeAssistantConfig, labels: list[str]
) -> dict[str, str]:
    prefix = config.entity_prefix.replace("_", " ").title()
    return {label: f"{prefix} {label.title()}" for label in labels}


def build_attributes(
    event: EventMessage,
    friendly_name: str | None = None,
    device_class: str | None = None,
) -> dict[str, str]:
    attributes: dict[str, str] = {
        "label": event.label,
        "confidence": str(event.confidence),
        "duration": str(event.duration),
        "state": event.state,
        "model": event.model,
    }
    if friendly_name:
        attributes["friendly_name"] = friendly_name
    if device_class:
        attributes["device_class"] = device_class
    return attributes
