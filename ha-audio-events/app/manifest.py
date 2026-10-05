"""Validation helpers for the Home Assistant add-on manifest (config.yaml).

These checks mirror the rules enforced by the Home Assistant Supervisor when it
parses an add-on repository (see supervisor/apps/validate.py):

- ``map`` entries must be a ``type`` that the Supervisor recognises (the
  ``MappingType`` enum), optionally with a boolean ``read_only`` and a ``path``.
  A dict entry that omits ``type`` is dropped, but an entry whose ``type`` is
  not a recognised value causes the whole manifest to be rejected -- which
  breaks the add-on in the store.
- The legacy shorthand form (e.g. ``ssl``, ``media:ro``) is still accepted.

Keeping these checks in CI means a malformed manifest can never silently break
the add-on store again.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Recognised map types (Mirrors supervisor MappingType plus the legacy
# enumeration the Supervisor's RE_VOLUME regex accepts). Sorted for clarity.
VALID_MAP_TYPES: frozenset[str] = frozenset(
    {
        "backup",
        "share",
        "ssl",
        "media",
        "local_apps",
        "addons",
        "all_app_configs",
        "all_addon_configs",
        "app_config",
        "addon_config",
        "homeassistant_config",
        "config",
        "data",
    }
)

MAP_FIELDS: frozenset[str] = frozenset({"type", "read_only", "path"})


class ManifestValidationError(ValueError):
    """Raised when the add-on manifest is invalid."""


def load_manifest(path: Path | str) -> dict[str, Any]:
    """Load and parse an add-on config.yaml manifest."""
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise ManifestValidationError(f"manifest not found: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ManifestValidationError(
            f"{manifest_path} does not contain a YAML mapping"
        )
    return data


def _invalid_map_entry(entry: Any, index: int) -> str | None:
    """Return an error message if a map entry is invalid, else None."""
    # Legacy shorthand string form, e.g. "ssl" or "media:ro".
    if isinstance(entry, str):
        raw = entry.split(":", 1)[0]
        if raw in VALID_MAP_TYPES:
            return None
        return f"map[{index}]: unrecognised map type {entry!r}"

    if not isinstance(entry, dict):
        return f"map[{index}]: expected a string or dict, got {type(entry).__name__}"

    # Check the type first: like the Supervisor, an unrecognised map type
    # (e.g. the historical `type: read`) is a hard error, whereas a stray
    # metadata field is merely reported.
    map_type = entry.get("type")
    if not isinstance(map_type, str):
        return f"map[{index}]: missing required 'type' field in {entry!r}"

    if map_type not in VALID_MAP_TYPES:
        # e.g. the historical bug: `type: read` -- not a valid map type.
        return f"map[{index}]: unrecognised map type 'type: {map_type}' in {entry!r}"

    unknown = sorted(set(entry) - MAP_FIELDS)
    if unknown:
        return f"map[{index}]: unknown field(s) {unknown} in {entry!r}"

    read_only = entry.get("read_only")
    if read_only is not None and not isinstance(read_only, bool):
        return (
            f"map[{index}]: 'read_only' must be a bool, "
            f"got {type(read_only).__name__} in {entry!r}"
        )

    return None


def validate_map(manifest: dict[str, Any]) -> list[str]:
    """Validate the ``map`` section of a manifest.

    Returns a list of error messages (empty if valid).
    """
    errors: list[str] = []
    raw_map = manifest.get("map", [])
    if not isinstance(raw_map, list):
        return [f"'map' must be a list, got {type(raw_map).__name__}"]

    for index, entry in enumerate(raw_map):
        error = _invalid_map_entry(entry, index)
        if error:
            errors.append(error)
    return errors


def validate_manifest(path: Path | str) -> list[str]:
    """Validate an add-on manifest file, returning a list of error messages."""
    manifest = load_manifest(path)
    errors: list[str] = validate_map(manifest)

    if "name" not in manifest:
        errors.append("missing required 'name' field")
    if "version" not in manifest:
        errors.append("missing required 'version' field")
    if "slug" not in manifest:
        errors.append("missing required 'slug' field")

    return errors
