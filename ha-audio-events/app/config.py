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
    username: str | None = None
    password: str | None = None
    tls: bool = False


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
    # When set, /api endpoints require this shared token. Unnecessary behind
    # HA ingress; recommended for standalone deployments.
    auth_token: str | None = None


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
    if path is not None:
        # An explicitly provided path must exist: silently falling back to a
        # default file would mask typos and load the wrong configuration.
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
    else:
        # Default lookup order for the add-on environment.
        config_path = Path("/data/options.json")
        if not config_path.exists():
            config_path = Path("config.yaml")
    raw = _load_config(config_path)

    raw_audio = raw.get("audio")

    # Handle case where audio is a boolean (from HA add-on options file)
    if isinstance(raw_audio, bool):
        audio_cfg = AudioSourceConfig()
    else:
        audio_cfg = AudioSourceConfig(
            sample_rate=(
                int(raw_audio.get("sample_rate", 16000))
                if isinstance(raw_audio, dict)
                else 16000
            ),
            channels=(
                int(raw_audio.get("channels", 1)) if isinstance(raw_audio, dict) else 1
            ),
            format=(
                str(raw_audio.get("format", "pcm_s16le"))
                if isinstance(raw_audio, dict)
                else "pcm_s16le"
            ),
            source_path=(
                raw_audio.get("source_path") if isinstance(raw_audio, dict) else None
            ),
        )

    activity = raw.get("activity", {})
    classifier = raw.get("classifier", {})
    aggregation = raw.get("aggregation", {})
    mqtt = raw.get("mqtt", {})
    webui = raw.get("webui", {})

    return AppConfig(
        model=str(raw.get("model", "yamnet")),
        buffer_seconds=float(raw.get("buffer_seconds", 3.0)),
        audio=audio_cfg,
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
            username=(
                str(mqtt["username"]) if mqtt.get("username") is not None else None
            ),
            password=(
                str(mqtt["password"]) if mqtt.get("password") is not None else None
            ),
            tls=bool(mqtt.get("tls", False)),
        ),
        webui=WebUIConfig(
            enabled=bool(webui.get("enabled", True)),
            host=str(webui.get("host", "0.0.0.0")),
            port=int(webui.get("port", 8099)),
            auth_token=(
                str(webui["auth_token"])
                if webui.get("auth_token") is not None
                else None
            ),
        ),
        log_level=str(raw.get("log_level", "INFO")),
    )
