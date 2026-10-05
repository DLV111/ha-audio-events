from __future__ import annotations

from pathlib import Path

from app.classifiers.base import AudioClassifier
from app.classifiers.yamnet import YAMNetClassifier
from app.config import AppConfig


def build_classifier(config: AppConfig) -> AudioClassifier:
    if config.model == "yamnet":
        model_path = Path("models/yamnet.tflite")
        return YAMNetClassifier(model_path=model_path)
    raise ValueError(f"Unsupported audio model: {config.model}")
