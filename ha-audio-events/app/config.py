from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AudioSourceConfig:
    sample_rate: int = 16000
    channels: int = 1
    format: str = "pcm_s16le"
    source_path: str | None = None


@dataclass(frozen=True)
class ActivityConfig:
    rms_threshold: float = 0.04
    peak_threshold: float = 0.1
    hold_time: float = 2.0


@dataclass(frozen=True)
class ClassifierConfig:
    threshold: float = 0.8
    max_results: int = 5
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AggregationConfig:
    start_confidence: float = 0.85
    end_timeout: float = 5.0


@dataclass(frozen=True)
class MQTTConfig:
    enabled: bool = False
    host: str = "localhost"
    port: int = 1883
    topic: str = "audio/events"
    discovery_prefix: str = "homeassistant"


@dataclass(frozen=True)
class HomeAssistantConfig:
    enabled: bool = True
    url: str = "http://supervisor/core"
    token: str | None = None
    entity_prefix: str = "audio"


@dataclass(frozen=True)
class WebUIConfig:
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8099


@dataclass(frozen=True)
class AppConfig:
    model: str = "yamnet"
    buffer_seconds: float = 3.0
    audio: AudioSourceConfig = field(default_factory=AudioSourceConfig)
    activity: ActivityConfig = field(default_factory=ActivityConfig)
    classifier: ClassifierConfig = field(default_factory=ClassifierConfig)
    aggregation: AggregationConfig = field(default_factory=AggregationConfig)
    homeassistant: HomeAssistantConfig = field(default_factory=HomeAssistantConfig)
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    webui: WebUIConfig = field(default_factory=WebUIConfig)
    log_level: str = "INFO"


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_config(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        return _load_json(path)
    return _load_yaml(path)


def load_config(path: Path | str | None = None) -> AppConfig:
    config_path = Path(path or "/data/options.json")
    if not config_path.exists():
        config_path = Path(path or "config.yaml")
    raw = _load_config(config_path)

    audio = raw.get("audio", {})
    activity = raw.get("activity", {})
    classifier = raw.get("classifier", {})
    aggregation = raw.get("aggregation", {})
    mqtt = raw.get("mqtt", {})
    webui = raw.get("webui", {})

    return AppConfig(
        model=str(raw.get("model", "yamnet")),
        buffer_seconds=float(raw.get("buffer_seconds", 3.0)),
        audio=AudioSourceConfig(
            sample_rate=int(audio.get("sample_rate", 16000)),
            channels=int(audio.get("channels", 1)),
            format=str(audio.get("format", "pcm_s16le")),
            source_path=audio.get("source_path"),
        ),
        activity=ActivityConfig(
            rms_threshold=float(activity.get("rms_threshold", 0.04)),
            peak_threshold=float(activity.get("peak_threshold", 0.1)),
            hold_time=float(activity.get("hold_time", 2.0)),
        ),
        classifier=ClassifierConfig(
            threshold=float(classifier.get("threshold", 0.8)),
            max_results=int(classifier.get("max_results", 5)),
            include=[str(item).lower() for item in classifier.get("include", []) or []],
            exclude=[str(item).lower() for item in classifier.get("exclude", []) or []],
        ),
        aggregation=AggregationConfig(
            start_confidence=float(aggregation.get("start_confidence", 0.85)),
            end_timeout=float(aggregation.get("end_timeout", 5.0)),
        ),
        homeassistant=HomeAssistantConfig(
            enabled=bool(raw.get("homeassistant", {}).get("enabled", True)),
            url=str(raw.get("homeassistant", {}).get("url", "http://supervisor/core")),
            token=(
                raw.get("homeassistant", {}).get("token")
                or os.getenv("HASS_TOKEN")
                or os.getenv("SUPERVISOR_TOKEN")
            ),
            entity_prefix=str(
                raw.get("homeassistant", {}).get("entity_prefix", "audio")
            ),
        ),
        mqtt=MQTTConfig(
            enabled=bool(mqtt.get("enabled", False)),
            host=str(mqtt.get("host", "localhost")),
            port=int(mqtt.get("port", 1883)),
            topic=str(mqtt.get("topic", "audio/events")),
            discovery_prefix=str(mqtt.get("discovery_prefix", "homeassistant")),
        ),
        webui=WebUIConfig(
            enabled=bool(webui.get("enabled", True)),
            host=str(webui.get("host", "0.0.0.0")),
            port=int(webui.get("port", 8099)),
        ),
        log_level=str(raw.get("log_level", "INFO")),
    )
