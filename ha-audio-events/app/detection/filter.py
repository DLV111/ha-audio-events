from __future__ import annotations

from app.classifiers.base import Detection
from app.config import ClassifierConfig


def filter_detections(
    detections: list[Detection], config: ClassifierConfig
) -> list[Detection]:
    filtered: list[Detection] = []
    include = [item.lower() for item in config.include]
    exclude = [item.lower() for item in config.exclude]

    for detection in detections:
        label = detection.label.lower()
        if detection.confidence < config.threshold:
            continue
        if include and not any(item in label for item in include):
            continue
        if any(item in label for item in exclude):
            continue
        filtered.append(detection)
        if len(filtered) >= config.max_results:
            break

    return filtered
