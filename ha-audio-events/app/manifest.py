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

import re
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


def validate_manifest_dict(manifest: dict[str, Any]) -> list[str]:
    """Validate a manifest dict, returning a list of error messages."""
    errors: list[str] = validate_map(manifest)

    if "name" not in manifest:
        errors.append("missing required 'name' field")
    elif not isinstance(manifest.get("name"), str) or not manifest["name"].strip():
        errors.append("'name' must be a non-empty string")

    if "version" not in manifest:
        errors.append("missing required 'version' field")
    elif (
        not isinstance(manifest.get("version"), str) or not manifest["version"].strip()
    ):
        errors.append("'version' must be a non-empty string")

    if "slug" not in manifest:
        errors.append("missing required 'slug' field")
    elif not isinstance(manifest.get("slug"), str) or not manifest["slug"].strip():
        errors.append("'slug' must be a non-empty string")

    if "description" not in manifest:
        errors.append("missing required 'description' field")
    elif (
        not isinstance(manifest.get("description"), str)
        or not manifest["description"].strip()
    ):
        errors.append("'description' must be a non-empty string")

    if "arch" not in manifest:
        errors.append("missing required 'arch' field")
    elif not isinstance(manifest.get("arch"), list) or not manifest["arch"]:
        errors.append("'arch' must be a non-empty list")

    if "options" not in manifest:
        errors.append("missing required 'options' field")
    elif not isinstance(manifest.get("options"), dict):
        errors.append("'options' must be a mapping")

    if "schema" not in manifest:
        errors.append("missing required 'schema' field")
    elif not isinstance(manifest.get("schema"), dict):
        errors.append("'schema' must be a mapping")

    errors.extend(validate_options_schema(manifest))
    return errors


def validate_manifest(path: Path | str) -> list[str]:
    """Validate an add-on manifest file, returning a list of error messages."""
    manifest = load_manifest(path)
    return validate_manifest_dict(manifest)


def _schema_key_for_option(option_key: str) -> str:
    """Map an options key to its schema key (stripping a trailing ``?``)."""
    return option_key.rstrip("?")


def validate_options_schema(manifest: dict[str, Any]) -> list[str]:
    """Validate parity between the ``options`` and ``schema`` sections.

    Rules:
    - Every key in ``options`` must have a corresponding entry in ``schema``.
    - A schema key ending with ``?`` is nullable: it must NOT appear in ``options``
      at all (the Supervisor rejects ``null`` defaults for nullable fields).
    - Schema keys absent from ``options`` must be optional (end with ``?``).
    - Nested dicts in schema are recursed into.
    """
    errors: list[str] = []
    options = manifest.get("options")
    schema = manifest.get("schema")

    if not isinstance(options, dict):
        if options is not None:
            errors.append("'options' must be a mapping")
        return errors
    if not isinstance(schema, dict):
        if schema is not None:
            errors.append("'schema' must be a mapping")
        return errors

    return _validate_options_schema_recursive(options, schema, path="")


def _validate_options_schema_recursive(
    options: dict[str, Any],
    schema: dict[str, Any],
    path: str,
) -> list[str]:
    """Recursively validate options/schema parity."""
    errors: list[str] = []

    # Schema keys absent from options must be optional (end with '?').
    for schema_key, schema_val in schema.items():
        if schema_key not in options and not schema_key.endswith("?"):
            prefix = f"{path}." if path else ""
            errors.append(
                f"schema key '{prefix}{schema_key}' is required but missing from options"
            )

    for option_key, option_value in options.items():
        prefix = f"{path}." if path else ""
        schema_key = option_key.rstrip("?")
        if schema_key not in schema:
            errors.append(
                f"option '{prefix}{option_key}' has no corresponding schema entry"
            )
            continue

        schema_val = schema[schema_key]
        # (a) Nullable schema keys must NOT appear in options at all.
        if schema_key.endswith("?"):
            errors.append(
                f"nullable option '{prefix}{option_key}' must not appear in options"
            )
            continue

        # (b) Recurse into nested dicts.
        if isinstance(schema_val, dict) and isinstance(option_value, dict):
            errors.extend(
                _validate_options_schema_recursive(
                    option_value, schema_val, path=f"{prefix}{option_key}"
                )
            )
        elif isinstance(schema_val, dict) and not isinstance(option_value, dict):
            errors.append(
                f"option '{prefix}{option_key}' must be a mapping, got {type(option_value).__name__}"
            )

    return errors


def validate_full(path: Path | str) -> list[str]:
    """Alias for validate_manifest."""
    return validate_manifest(path)


# ---------------------------------------------------------------------------
# Release metadata validation (version consistency, changelog, version increase)
# ---------------------------------------------------------------------------


def get_config_version(path: Path | str) -> str | None:
    """Extract version from config.yaml."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return data.get("version")


def get_pyproject_version(path: Path | str) -> str | None:
    """Extract version from pyproject.toml."""
    content = Path(path).read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
    return match.group(1) if match else None


def get_changelog_heading_version(path: Path | str) -> str | None:
    """Extract the version from the first changelog heading (## [x.y.z])."""
    content = Path(path).read_text(encoding="utf-8")
    match = re.search(r"^## \[([^\]]+)\]", content, re.MULTILINE)
    return match.group(1) if match else None


def get_all_changelog_versions(path: Path | str) -> list[str]:
    """Extract all version headings from changelog in descending order."""
    content = Path(path).read_text(encoding="utf-8")
    return [m.group(1) for m in re.finditer(r"^## \[([^\]]+)\]", content, re.MULTILINE)]


def check_version_consistency(
    config_path: Path | str,
    pyproject_path: Path | str,
    changelog_path: Path | str,
) -> list[str]:
    """Verify config.yaml, pyproject.toml, and CHANGELOG.md top heading have same version."""
    errors: list[str] = []
    config_ver = get_config_version(config_path)
    pyproject_ver = get_pyproject_version(pyproject_path)
    changelog_ver = get_changelog_heading_version(changelog_path)

    if config_ver is None:
        errors.append("config.yaml: version not found")
    if pyproject_ver is None:
        errors.append("pyproject.toml: version not found")
    if changelog_ver is None:
        errors.append("CHANGELOG.md: no version heading found")

    versions = {
        "config.yaml": config_ver,
        "pyproject.toml": pyproject_ver,
        "CHANGELOG.md": changelog_ver,
    }
    non_none = [v for v in versions.values() if v is not None]
    if len(set(non_none)) > 1:
        errors.append(
            "Version mismatch: "
            + ", ".join(f"{k}={v}" for k, v in versions.items() if v is not None)
        )

    return errors


def check_version_increases(
    base_config_path: Path | str,
    head_config_path: Path | str,
) -> list[str]:
    """Verify version strictly increased in config.yaml when add-on files changed."""
    errors: list[str] = []
    base_ver = get_config_version(base_config_path)
    head_ver = get_config_version(head_config_path)

    if base_ver is None:
        errors.append("Base config.yaml: version not found")
    if head_ver is None:
        errors.append("Head config.yaml: version not found")

    if base_ver and head_ver:
        try:
            from packaging.version import Version

            if Version(head_ver) <= Version(base_ver):
                errors.append(
                    f"Version must strictly increase: {base_ver} -> {head_ver}"
                )
        except ValueError as e:
            errors.append(f"Invalid version format: {e!s}")

    return errors


def check_changelog_append_only(
    base_changelog_path: Path | str,
    head_changelog_path: Path | str,
) -> list[str]:
    """Verify changelog only appends new headings (no removed/renamed headings).

    The changelog is newest-first, so a release adds a new top heading; existing
    headings must all still be present in the head changelog.
    """
    errors: list[str] = []
    base_versions = get_all_changelog_versions(base_changelog_path)
    head_versions = get_all_changelog_versions(head_changelog_path)

    if not base_versions:
        errors.append("Base CHANGELOG.md has no version headings")
    if not head_versions:
        errors.append("Head CHANGELOG.md has no version headings")

    head_set = set(head_versions)
    for base_ver in base_versions:
        if base_ver not in head_set:
            errors.append(f"Changelog heading removed: {base_ver}")

    return errors
