from __future__ import annotations

from typing import Dict, List

from app.config import HomeAssistantConfig
from app.detection.models import EventMessage


def build_entity_ids(config: HomeAssistantConfig) -> Dict[str, str]:
    prefix = config.entity_prefix
    return {
        "last_audio_event": f"sensor.{prefix}_last_audio_event",
        "last_audio_confidence": f"sensor.{prefix}_last_audio_confidence",
        "audio_model": f"sensor.{prefix}_audio_model",
        "audio_event_duration": f"sensor.{prefix}_audio_event_duration",
        "audio_active": f"binary_sensor.{prefix}_audio_active",
    }


def build_label_sensor_entity_ids(config: HomeAssistantConfig, labels: List[str]) -> Dict[str, str]:
    prefix = config.entity_prefix
    return {
        label: f"binary_sensor.{prefix}_{label.replace(' ', '_').lower()}"
        for label in labels
    }


def build_attributes(event: EventMessage) -> dict[str, str]:
    return {
        "label": event.label,
        "confidence": str(event.confidence),
        "duration": str(event.duration),
        "state": event.state,
        "model": event.model,
    }
