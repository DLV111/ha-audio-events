"""Regression tests for the Home Assistant add-on manifest.

The motivation: an invalid ``map`` entry (``type: read``) was merged and broke
the add-on in the HA store. These tests ensure a malformed manifest can never
slip through CI again, and that the committed ``config.yaml`` stays valid.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.manifest import ManifestValidationError, validate_manifest, validate_map

MANIFEST_PATH = Path("ha-audio-events/config.yaml")
_REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Unit tests for the map validation rules
# ---------------------------------------------------------------------------


def test_valid_modern_map_entries() -> None:
    manifest = {
        "map": [
            {"type": "homeassistant_config", "read_only": True},
            {"type": "addons", "read_only": True},
            {"type": "ssl"},
        ]
    }
    assert validate_map(manifest) == []


def test_legacy_string_map_entries_are_valid() -> None:
    manifest = {"map": ["ssl", "media:ro", "share:rw", "homeassistant_config"]}
    assert validate_map(manifest) == []


def test_invalid_read_map_type_is_rejected() -> None:
    # Regression: this exact shape broke the app store.
    manifest = {
        "map": [
            {"homeassistant_config": "/config", "type": "read"},
            {"addons": "/addons", "type": "read"},
            {"ssl": "/ssl", "type": "read"},
        ]
    }
    errors = validate_map(manifest)
    assert len(errors) == 3
    assert all("unrecognised map type 'type: read'" in error for error in errors)


def test_unknown_extra_fields_are_rejected() -> None:
    manifest = {"map": [{"type": "ssl", "read_only": True, "bogus": 1}]}
    errors = validate_map(manifest)
    assert any("unknown field" in error for error in errors)


def test_map_must_be_a_list() -> None:
    assert validate_map({"map": "ssl"}) == ["'map' must be a list, got str"]


def test_read_only_must_be_bool() -> None:
    manifest = {"map": [{"type": "ssl", "read_only": "read"}]}
    errors = validate_map(manifest)
    assert any("'read_only' must be a bool" in error for error in errors)


def test_missing_map_type_is_rejected() -> None:
    manifest = {"map": [{"read_only": True}]}
    errors = validate_map(manifest)
    assert any("missing required 'type'" in error for error in errors)


# ---------------------------------------------------------------------------
# CI guard: the checked-in manifest must always be parseable
# ---------------------------------------------------------------------------


def test_committed_manifest_is_valid() -> None:
    path = _REPO_ROOT / "ha-audio-events" / "config.yaml"
    if not path.exists():
        pytest.skip("ha-audio-events/config.yaml not present")
    errors = validate_manifest(path)
    assert errors == [], "add-on manifest is invalid:\n" + "\n".join(errors)


def test_committed_manifest_exists() -> None:
    assert MANIFEST_PATH.exists(), "ha-audio-events/config.yaml is missing"


def test_missing_file_raises() -> None:
    with pytest.raises(ManifestValidationError):
        validate_manifest(_REPO_ROOT / "does-not-exist.yaml")
