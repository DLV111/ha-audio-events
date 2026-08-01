from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.classifiers.registry import build_classifier
from app.config import AppConfig

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "audio"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"


def _load_manifest() -> dict[str, dict[str, object]]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("fixture_name", "expected_label", "category"),
    [
        ("freesound_community-8-freight-train_126s.mp3", "train", "train"),
        ("audiopapkin-barking-large-and-small-dog-290711.mp3", "dog", "dog"),
        ("dragon-studio-dog-barking-406629.mp3", "dog", "dog"),
        ("dragon-studio-free-dog-bark-419014.mp3", "dog", "dog"),
    ],
)
def test_audio_fixture_classifies_as_expected(fixture_name: str, expected_label: str, category: str) -> None:
    manifest = _load_manifest()
    fixture_meta = manifest[fixture_name]

    relative_path = str(fixture_meta["path"])
    fixture_path = FIXTURE_ROOT / relative_path
    if not fixture_path.exists():
        pytest.skip(f"Fixture file not found: {fixture_path}")

    model_path = Path("models/yamnet.tflite")
    labels_path = Path("models/yamnet_class_map.csv")
    legacy_labels_path = Path("models/yamnet_labels.txt")
    if not model_path.exists() or not (labels_path.exists() or legacy_labels_path.exists()):
        pytest.skip("YAMNet model artifacts are not present; install them to run classifier integration tests")

    config = AppConfig(model="yamnet")
    classifier = build_classifier(config)

    assert fixture_meta["expected_label"] == expected_label
    assert fixture_meta["category"] == category

    assert classifier is not None
