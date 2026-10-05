"""Tests for add-on option usability work:

- homeassistant.url normalization (self-healing legacy values)
- manifest <-> translations coherence (every option documented inline)
- dropdown (list()) schemas that match the shipped default options
- loud failure when ffmpeg dies instead of silent zombie streams
"""

from __future__ import annotations

import asyncio
import re
from collections import deque
from pathlib import Path

import pytest
import yaml
from app.config import load_config, normalize_ha_url

REPO_ROOT = Path(__file__).resolve().parents[1]
ADDON_DIR = REPO_ROOT / "ha-audio-events"


# ---------------------------------------------------------------------------
# Legacy URL normalization (Fix: self-heal stale saved options)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://supervisor/homeassistant", "http://supervisor/core"),
        ("http://supervisor/homeassistant/", "http://supervisor/core"),
        ("http://supervisor/core/api", "http://supervisor/core"),
        ("http://supervisor/core", "http://supervisor/core"),
        ("http://homeassistant.local:8123", "http://homeassistant.local:8123"),
        ("  http://supervisor/homeassistant  ", "http://supervisor/core"),
        (None, None),
        ("", None),
        ("   ", None),
    ],
)
def test_normalize_ha_url(raw, expected):
    assert normalize_ha_url(raw) == expected


def test_load_config_normalizes_legacy_saved_url(tmp_path: Path) -> None:
    """Options saved by pre-0.1.11 installs carry the broken proxy URL;
    loading them must heal the value rather than silently failing later."""
    cfg_file = tmp_path / "options.json"
    cfg_file.write_text(
        '{"homeassistant": {"enabled": true, '
        '"url": "http://supervisor/homeassistant", "entity_prefix": "audio"}}',
        encoding="utf-8",
    )

    config = load_config(cfg_file)

    assert config.homeassistant.url == "http://supervisor/core"


def test_camera_stream_url_built_from_normalized_core_url() -> None:
    """Regression: camera streaming must build its URL from supervisor/core,
    never the legacy /homeassistant proxy path (which 401s silently)."""
    from app.audio.stream import AudioStreamSource

    # A stale saved URL is normalized before the URL is built...
    assert (
        AudioStreamSource.build_camera_stream_url(
            "http://supervisor/homeassistant", "camera.garage_camera"
        )
        == "http://supervisor/core/api/camera_proxy_stream/camera.garage_camera"
    )
    assert (
        AudioStreamSource.build_camera_stream_url(
            "http://supervisor/core/api", "camera.garage_camera"
        )
        == "http://supervisor/core/api/camera_proxy_stream/camera.garage_camera"
    )
    # External HA instances keep their address, /api appended once.
    assert (
        AudioStreamSource.build_camera_stream_url("http://ha.local:8123/", "camera.x")
        == "http://ha.local:8123/api/camera_proxy_stream/camera.x"
    )


# ---------------------------------------------------------------------------
# Manifest <-> translations coherence
# ---------------------------------------------------------------------------


def _load_manifest() -> dict:
    return yaml.safe_load((ADDON_DIR / "config.yaml").read_text(encoding="utf-8"))


def _load_translations() -> dict:
    path = ADDON_DIR / "translations" / "en.yaml"
    assert path.exists(), "add-on translations/en.yaml is required"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _iter_schema_leaves(node: dict, prefix: str = ""):
    """Yield (dotted_key, type_string) for every leaf of the schema tree."""
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            yield from _iter_schema_leaves(value, path)
        elif isinstance(value, list):
            # list-of-types (e.g. include/exclude string arrays)
            yield (path, value[0])
        else:
            yield (path, str(value))


def _translation_has_path(translations: dict, dotted_key: str) -> bool:
    node: object = translations.get("configuration", {})
    for part in dotted_key.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return isinstance(node, dict) and {"name", "description"} <= set(node)


def test_every_schema_option_is_documented_in_translations() -> None:
    manifest = _load_manifest()
    translations = _load_translations()

    undocumented = [
        key
        for key, _ in _iter_schema_leaves(manifest["schema"])
        if not _translation_has_path(translations, key)
    ]
    assert (
        undocumented == []
    ), f"Schema options missing translations/en.yaml docs: {undocumented}"


def test_dropdown_choices_match_defaults_and_lock_known_values() -> None:
    """list(...) schemas render as dropdowns; the shipped option values must
    be one of the allowed choices."""
    manifest = _load_manifest()
    schema = manifest["schema"]
    options = manifest["options"]

    def choices(type_str: str) -> list[str]:
        match = re.fullmatch(r"list\((.+)\)", type_str)
        assert match, f"not a dropdown type: {type_str}"
        return match.group(1).split("|")

    assert choices(schema["model"]) == ["yamnet"]
    assert options["model"] in choices(schema["model"])

    audio_schema = schema["audio"]
    audio_options = options["audio"]
    # YAMNet requires exactly these values -- they are locked, not free text.
    assert choices(audio_schema["sample_rate"]) == ["16000"]
    assert str(audio_options["sample_rate"]) in choices(audio_schema["sample_rate"])
    assert choices(audio_schema["channels"]) == ["1"]
    assert str(audio_options["channels"]) in choices(audio_schema["channels"])
    assert choices(audio_schema["format"]) == ["pcm_s16le"]
    assert audio_options["format"] in choices(audio_schema["format"])

    assert options["log_level"] in choices(schema["log_level"])


def test_connection_details_hidden_from_new_options_but_back_compat() -> None:
    """url/token must not appear in fresh-install defaults (they're managed
    by the Supervisor), yet older saved options carrying them must still
    validate against the schema."""
    manifest = _load_manifest()
    options_ha = manifest["options"]["homeassistant"]
    schema_ha = manifest["schema"]["homeassistant"]

    assert "url" not in options_ha
    assert "token" not in options_ha
    assert schema_ha["url"] == "str?"
    assert schema_ha["token"] == "str?"


def test_manifest_version_matches_pyproject() -> None:
    manifest = _load_manifest()
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert match
    assert manifest["version"] == match.group(1)


def _iter_option_values(node: object, prefix: str = ""):
    """Yield (dotted_key, value) for every leaf of the options tree."""
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from _iter_option_values(value, path)
    else:
        yield (prefix, node)


def test_manifest_defaults_never_use_null() -> None:
    """Supervisor rejects null values for nullable (str?) schema fields with
    'Missing required option', blocking update/start on real installs
    (observed live: username/auth_token). Defaults must use "" instead, and
    load_config coerces blanks back to None."""
    manifest = _load_manifest()
    null_options = [
        key for key, value in _iter_option_values(manifest["options"]) if value is None
    ]
    assert null_options == []


def test_blank_string_options_coerce_to_none(tmp_path: Path) -> None:
    """The app-side contract: "" behaves exactly like an unset option."""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "audio:\n"
        '  source_path: ""\n'
        "mqtt:\n"
        '  username: ""\n'
        '  password: "  "\n'
        "  tls: false\n"
        "webui:\n"
        '  auth_token: ""\n',
        encoding="utf-8",
    )

    config = load_config(cfg_file)

    assert config.audio.source_path is None
    assert config.mqtt.username is None
    assert config.mqtt.password is None  # whitespace-only counts as blank
    assert config.webui.auth_token is None


def test_nonblank_string_options_are_kept(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        'audio:\n  source_path: "camera.garage_camera"\n'
        'mqtt:\n  username: "audio"\n',
        encoding="utf-8",
    )

    config = load_config(cfg_file)

    assert config.audio.source_path == "camera.garage_camera"
    assert config.mqtt.username == "audio"


# ---------------------------------------------------------------------------
# Loud failure on dead ffmpeg streams
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ffmpeg_nonzero_exit_logs_loud_error(caplog) -> None:
    """A dead source (unreachable camera / no audio track) must produce an
    explicit error naming the exit code and recent ffmpeg output, instead of
    the pipeline ending silently."""
    from app.audio.stream import AudioStreamSource
    from app.config import AudioSourceConfig

    stderr_reader = asyncio.StreamReader()
    stderr_reader.feed_data(b"rtsp://x: Connection refused\n")
    stderr_reader.feed_eof()

    class FakeStdout:
        async def read(self, size: int) -> bytes:
            return b""  # immediate EOF: nothing ever decoded

    class FakeProc:
        def __init__(self) -> None:
            self.stdout = FakeStdout()
            self.stderr = stderr_reader
            self.returncode: int | None = None

        async def wait(self) -> int:
            self.returncode = 1
            return 1

        def terminate(self) -> None:  # pragma: no cover - must not be called
            raise AssertionError("terminate should not run after clean exit")

    async def fake_exec(*args, **kwargs):
        return FakeProc()

    from unittest.mock import patch

    source = AudioStreamSource(AudioSourceConfig(sample_rate=16000, channels=1))
    chunks = []
    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        async for chunk in source._stream_ffmpeg("rtsp://unreachable/x"):
            chunks.append(chunk)

    assert chunks == []
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert any(
        "Audio stream ended unexpectedly" in r.message and "code 1" in r.message
        for r in errors
    )


@pytest.mark.asyncio
async def test_drain_stderr_collects_tail() -> None:
    from app.audio.stream import AudioStreamSource

    reader = asyncio.StreamReader()
    reader.feed_data(b"[rtsp @ 0x1] method DESCRIBE failed: 404\n")
    reader.feed_eof()

    tail: deque[str] = deque(maxlen=10)
    task = asyncio.create_task(AudioStreamSource._drain_stderr(reader, tail))
    await asyncio.wait_for(task, timeout=2)

    assert list(tail) == ["[rtsp @ 0x1] method DESCRIBE failed: 404"]
