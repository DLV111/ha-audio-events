from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "audio"
FIXTURE_MANIFEST = FIXTURE_ROOT / "manifest.json"


def _load_manifest() -> dict[str, dict[str, object]]:
    if not FIXTURE_MANIFEST.exists():
        return {}
    return json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("fixture_name", "expected_label", "category", "relative_path"),
    [
        ("freight_train_01.wav", "train", "train", "train/freight_train_01.wav"),
        (
            "freesound_community-8-freight-train_126s.mp3",
            "train",
            "train",
            "train/freesound_community-8-freight-train_126s.mp3",
        ),
        (
            "sspsurvival-train-sleepers-train-wheels-freight-train_95s.mp3",
            "train",
            "train",
            "train/sspsurvival-train-sleepers-train-wheels-freight-train_95s.mp3",
        ),
        (
            "audiopapkin-barking-large-and-small-dog-290711.mp3",
            "dog",
            "dog",
            "dog-barking/audiopapkin-barking-large-and-small-dog-290711.mp3",
        ),
        (
            "dragon-studio-dog-barking-406629.mp3",
            "dog",
            "dog",
            "dog-barking/dragon-studio-dog-barking-406629.mp3",
        ),
        (
            "dragon-studio-free-dog-bark-419014.mp3",
            "dog",
            "dog",
            "dog-barking/dragon-studio-free-dog-bark-419014.mp3",
        ),
    ],
)
def test_fixture_manifest_contains_expected_entry(
    fixture_name: str,
    expected_label: str,
    category: str,
    relative_path: str,
) -> None:
    manifest = _load_manifest()
    assert fixture_name in manifest, (
        f"Missing fixture manifest entry for {fixture_name}"
    )

    fixture_meta = manifest[fixture_name]
    assert fixture_meta.get("expected_label") == expected_label
    assert fixture_meta.get("category") == category
    assert fixture_meta.get("path") == relative_path


@pytest.mark.parametrize(
    ("fixture_name", "relative_path"),
    [
        ("freight_train_01.wav", "train/freight_train_01.wav"),
        (
            "freesound_community-8-freight-train_126s.mp3",
            "train/freesound_community-8-freight-train_126s.mp3",
        ),
        (
            "sspsurvival-train-sleepers-train-wheels-freight-train_95s.mp3",
            "train/sspsurvival-train-sleepers-train-wheels-freight-train_95s.mp3",
        ),
        (
            "audiopapkin-barking-large-and-small-dog-290711.mp3",
            "dog-barking/audiopapkin-barking-large-and-small-dog-290711.mp3",
        ),
        (
            "dragon-studio-dog-barking-406629.mp3",
            "dog-barking/dragon-studio-dog-barking-406629.mp3",
        ),
        (
            "dragon-studio-free-dog-bark-419014.mp3",
            "dog-barking/dragon-studio-free-dog-bark-419014.mp3",
        ),
    ],
)
def test_fixture_file_exists(fixture_name: str, relative_path: str) -> None:
    fixture_path = FIXTURE_ROOT / relative_path
    assert fixture_path.exists(), f"Fixture file not found: {fixture_path}"
