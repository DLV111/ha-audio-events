"""Tests for the Home Assistant add-on Dockerfile.

These tests verify that the container build follows the layering and caching
optimizations agreed on in the container build audit:

* multi-stage builder/runtime image
* slim base image
* BuildKit cache mounts for apt and pip
* system and Python dependencies installed before application source is copied
* runtime behavior preserved (entrypoint, root user for audio hardware access)
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOCKERFILE = Path(__file__).resolve().parents[1] / "ha-audio-events" / "Dockerfile"
REQUIREMENTS = (
    Path(__file__).resolve().parents[1] / "ha-audio-events" / "requirements.txt"
)
DOCKERIGNORE = Path(__file__).resolve().parents[1] / "ha-audio-events" / ".dockerignore"


@pytest.fixture(scope="module")
def dockerfile_text() -> str:
    if not DOCKERFILE.exists():
        pytest.fail(f"Dockerfile not found at {DOCKERFILE}")
    return DOCKERFILE.read_text()


@pytest.fixture(scope="module")
def requirements_text() -> str:
    if not REQUIREMENTS.exists():
        pytest.fail(f"requirements.txt not found at {REQUIREMENTS}")
    return REQUIREMENTS.read_text()


@pytest.fixture(scope="module")
def dockerignore_text() -> str:
    if not DOCKERIGNORE.exists():
        pytest.fail(f".dockerignore not found at {DOCKERIGNORE}")
    return DOCKERIGNORE.read_text()


def test_dockerfile_exists() -> None:
    assert DOCKERFILE.is_file()


def test_requirements_exists() -> None:
    assert REQUIREMENTS.is_file()


def test_uses_slim_base_image(dockerfile_text: str) -> None:
    assert "python:3.12-slim-bookworm" in dockerfile_text


def test_uses_multi_stage_build(dockerfile_text: str) -> None:
    assert "AS builder" in dockerfile_text
    assert "COPY --from=builder" in dockerfile_text


def test_uses_buildkit_apt_cache_mounts(dockerfile_text: str) -> None:
    assert "--mount=type=cache,target=/var/cache/apt" in dockerfile_text
    assert "--mount=type=cache,target=/var/lib/apt/lists" in dockerfile_text


def test_uses_buildkit_pip_cache_mount(dockerfile_text: str) -> None:
    assert "--mount=type=cache,target=/root/.cache/pip" in dockerfile_text


def test_dependencies_installed_before_source_copy(dockerfile_text: str) -> None:
    """Requirements must be installed before application source is copied."""
    pip_install_pos = dockerfile_text.find("pip install")
    copy_source_pos = dockerfile_text.find("COPY . /app")
    assert pip_install_pos != -1, "expected a pip install instruction"
    assert copy_source_pos != -1, "expected 'COPY . /app'"
    assert pip_install_pos < copy_source_pos


def test_requirements_in_sync_with_pyproject(requirements_text: str) -> None:
    """requirements.txt should contain the same direct runtime deps as pyproject.toml."""
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()

    expected = [
        "aiohttp>=3.9",
        "numpy>=1.26",
        "PyYAML>=6.0",
        "paho-mqtt>=2.1,<3.0",
        "ai-edge-litert>=2.1.0,<3.0.0",
    ]

    for dep in expected:
        # Accept either exact specifier or the dependency quoted in pyproject.
        assert dep in requirements_text, f"missing requirement: {dep}"
        # Strip version constraints for pyproject lookup.
        name = dep.split(">=")[0].split("<")[0].split("=")[0]
        assert name in pyproject, f"missing dependency in pyproject.toml: {name}"


def test_runtime_entrypoint_preserved(dockerfile_text: str) -> None:
    assert 'ENTRYPOINT ["/app/run.sh"]' in dockerfile_text


def test_no_healthcheck_instruction(dockerfile_text: str) -> None:
    """A failing-by-config healthcheck is worse than none; none should be present."""
    for line in dockerfile_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        assert not stripped.upper().startswith("HEALTHCHECK"), line


def test_dockerignore_exists() -> None:
    assert DOCKERIGNORE.is_file()


def test_dockerignore_excludes_build_files(dockerignore_text: str) -> None:
    assert "Dockerfile" in dockerignore_text
    assert ".dockerignore" in dockerignore_text


def test_dockerignore_excludes_python_caches(dockerignore_text: str) -> None:
    assert "__pycache__/" in dockerignore_text
    assert "*.py[cod]" in dockerignore_text


def test_dockerignore_excludes_documentation(dockerignore_text: str) -> None:
    assert "CHANGELOG.md" in dockerignore_text


def test_dockerignore_preserves_runtime_files(dockerignore_text: str) -> None:
    """Required runtime paths must not be ignored in the build context."""
    required = {"app/", "models/", "config.yaml", "run.sh", "translations/"}
    for line in dockerignore_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert stripped not in required, f"required path ignored: {stripped}"
