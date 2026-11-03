from __future__ import annotations

import re
from collections.abc import Iterable

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


def build_rest_entity_ids(
    config: HomeAssistantConfig,
    mqtt_enabled: bool,
    labels: Iterable[str] | None = None,
) -> set[str]:
    """Entity IDs this add-on deliberately owns via the HA REST API.

    Entity ownership is config-driven and mutually exclusive: every entity id
    this add-on touches has exactly one owner, so both paths can never fight
    over the same id.

    * **MQTT enabled** -- every entity is published through MQTT discovery
      (see ``app.homeassistant.discovery``), which is the only way to attach
      a registry ``unique_id``; Home Assistant otherwise tells the user the
      entity "does not have a unique ID, therefore its settings cannot be
      managed from the UI". REST owns nothing, so this returns an empty set.
    * **MQTT disabled** -- discovery does not happen at all, so the REST API
      is the only way for the entities to exist: REST owns the two scalar
      entity ids plus the per-label sensors for ``labels`` (the caller's
      ``classifier.include`` list). These state POSTs auto-create the
      entities and keep them live, but they stay unmanaged in Home
      Assistant's registry.

    Availability beats manageability: an install that never enables MQTT
    keeps working exactly as it did before MQTT discovery existed.

    Keep this the single, explicit place that declares REST-owned entity ids.
    """
    if mqtt_enabled:
        return set()

    entity_ids = set(build_entity_ids(config).values())
    if labels:
        entity_ids.update(build_label_sensor_entity_ids(config, list(labels)).values())
    return entity_ids


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
