"""Tests for scripts/validate_container_contents.sh.

These tests verify the container content validation script that guards the
multi-stage image against regressions (build tooling leakage, missing runtime
dependencies, etc.). Only static checks and dry-run friendly execution are
performed; no actual container build is required.
"""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "validate_container_contents.sh"


@pytest.fixture(scope="module")
def script_text() -> str:
    if not SCRIPT.exists():
        pytest.fail(f"Validation script not found at {SCRIPT}")
    return SCRIPT.read_text()


def _fake_engine_bin(tmp_path: Path) -> Path:
    """Create a fake container engine that always fails (no image present)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    engine = bin_dir / "docker"
    engine.write_text("#!/usr/bin/env bash\nexit 1\n")
    engine.chmod(engine.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return bin_dir


def test_script_exists_and_executable() -> None:
    assert SCRIPT.is_file()
    assert os.access(SCRIPT, os.X_OK)


def test_script_passes_bash_syntax_check() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_script_defaults_image_name(script_text: str) -> None:
    assert 'IMAGE="${1:-ha-audio-events-test}"' in script_text


def test_script_uses_container_engine_variable(script_text: str) -> None:
    assert "CONTAINER_ENGINE" in script_text
    assert "command -v docker" in script_text
    assert "command -v podman" in script_text


def test_script_checks_image_exists_before_validation(script_text: str) -> None:
    assert '"$CONTAINER_ENGINE" image exists "$IMAGE"' in script_text
    assert '"$CONTAINER_ENGINE" image inspect "$IMAGE"' in script_text
    assert "image not found" in script_text


def test_script_has_required_check_sections(script_text: str) -> None:
    for section in (
        "runtime tooling present",
        "Python runtime and dependencies",
        "application payload",
        "build hygiene",
        "startup behaviour",
    ):
        assert section in script_text, f"missing section: {section}"


def test_script_validates_runtime_dependencies(script_text: str) -> None:
    for check in (
        "ffmpeg executable",
        "python 3.12",
        "numpy importable",
        "aiohttp importable",
        "yaml importable",
        "paho-mqtt importable",
        "ai-edge-litert importable",
    ):
        assert check in script_text, f"missing runtime dependency check: {check}"


def test_script_validates_application_payload(script_text: str) -> None:
    for check in (
        "app package present",
        "YAMNet model present",
        "class groups present",
        "translations present",
    ):
        assert check in script_text, f"missing payload check: {check}"


def test_script_validates_build_hygiene(script_text: str) -> None:
    for check in (
        "no build-essential/gcc in runtime",
        "no pip cache in image",
        "no apt lists committed to layers",
        "app bytecode precompiled",
        "no CHANGELOG.md shipped",
    ):
        assert check in script_text, f"missing hygiene check: {check}"


def test_script_validates_startup_behaviour(script_text: str) -> None:
    for check in (
        "entrypoint forwards args",
        "PYTHONDONTWRITEBYTECODE set",
        "PYTHONUNBUFFERED set",
    ):
        assert check in script_text, f"missing startup check: {check}"


def test_script_fails_when_image_missing() -> None:
    """With a fake engine that reports no images, the script exits gracefully."""
    with tempfile.TemporaryDirectory() as tmp:
        fake_bin = _fake_engine_bin(Path(tmp))
        env = {
            **os.environ,
            "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
            "CONTAINER_ENGINE": "docker",
        }
        result = subprocess.run(
            [str(SCRIPT), "definitely-not-built-12345"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=60,
        )
    assert result.returncode != 0
    assert "image not found" in result.stderr
