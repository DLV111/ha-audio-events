from __future__ import annotations

from app.config import HomeAssistantConfig
from app.homeassistant.entities import build_entity_ids


def test_build_entity_ids_prefix() -> None:
    config = HomeAssistantConfig(
        enabled=True,
        url="http://supervisor/homeassistant",
        token="test",
        entity_prefix="audio",
    )
    entity_ids = build_entity_ids(config)

    assert entity_ids["last_audio_event"] == "sensor.audio_last_audio_event"
    assert entity_ids["audio_active"] == "binary_sensor.audio_audio_active"
