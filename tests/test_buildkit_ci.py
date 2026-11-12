"""Tests for BuildKit-aware container build configuration.

These tests verify that the CI workflow, Makefile, and build script are wired
together to enable BuildKit caching consistently for local and CI builds.
"""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build.sh"
MAKEFILE = REPO_ROOT / "Makefile"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
DOCKERFILE = REPO_ROOT / "ha-audio-events" / "Dockerfile"


@pytest.fixture(scope="module")
def build_script_text() -> str:
    if not BUILD_SCRIPT.exists():
        pytest.fail(f"Build script not found at {BUILD_SCRIPT}")
    return BUILD_SCRIPT.read_text()


@pytest.fixture(scope="module")
def makefile_text() -> str:
    if not MAKEFILE.exists():
        pytest.fail(f"Makefile not found at {MAKEFILE}")
    return MAKEFILE.read_text()


@pytest.fixture(scope="module")
def ci_workflow_text() -> str:
    if not CI_WORKFLOW.exists():
        pytest.fail(f"CI workflow not found at {CI_WORKFLOW}")
    return CI_WORKFLOW.read_text()


@pytest.fixture(scope="module")
def dockerfile_text() -> str:
    if not DOCKERFILE.exists():
        pytest.fail(f"Dockerfile not found at {DOCKERFILE}")
    return DOCKERFILE.read_text()


def _fake_docker_bin(tmp_path: Path) -> Path:
    """Create a minimal fake 'docker' that looks like real Docker + buildx."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(
        "#!/usr/bin/env bash\n"
        'case "$1 $2" in\n'
        "  ' --version'|'--version ')\n"
        "    echo 'Docker version 24.0.7, build afdd53b'\n"
        "    exit 0\n"
        "    ;;\n"
        "  'buildx version'|'buildx version ')\n"
        "    echo 'github.com/docker/buildx v0.12.0 1234567'\n"
        "    exit 0\n"
        "    ;;\n"
        "esac\n"
        "exit 0\n"
    )
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return bin_dir


def test_build_script_exists_and_executable() -> None:
    assert BUILD_SCRIPT.is_file()
    assert os.access(BUILD_SCRIPT, os.X_OK)


def test_build_script_uses_buildx_and_buildkit(build_script_text: str) -> None:
    assert "DOCKER_BUILDKIT=1" in build_script_text
    assert "docker buildx build" in build_script_text


def test_build_script_supports_cache_from_and_cache_to(build_script_text: str) -> None:
    assert "BUILD_CACHE_FROM" in build_script_text
    assert "BUILD_CACHE_TO" in build_script_text
    assert '"--cache-from"' in build_script_text or "--cache-from" in build_script_text
    assert '"--cache-to"' in build_script_text or "--cache-to" in build_script_text


def test_build_script_supports_inline_cache(build_script_text: str) -> None:
    assert "BUILDKIT_INLINE_CACHE" in build_script_text
    assert "BUILDKIT_INLINE_CACHE=1" in build_script_text


def test_build_script_dry_run_docker() -> None:
    """A dry run with real Docker selected must emit the expected buildx command."""
    with tempfile.TemporaryDirectory() as tmp:
        fake_bin = _fake_docker_bin(Path(tmp))
        env = {
            **os.environ,
            "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
            "CONTAINER_ENGINE": "docker",
            "DRY_RUN": "true",
            "BUILD_CACHE_FROM": "type=gha",
            "BUILD_CACHE_TO": "type=gha,mode=max",
            "BUILDKIT_INLINE_CACHE": "1",
        }
        result = subprocess.run(
            [str(BUILD_SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
    assert result.returncode == 0, result.stderr
    output = result.stdout.strip()
    assert "docker buildx build" in output
    assert "--cache-from type=gha" in output
    assert "--cache-to type=gha,mode=max" in output
    assert "BUILDKIT_INLINE_CACHE=1" in output


def test_build_script_dry_run_podman() -> None:
    """A dry run with Podman selected must emit a layered podman build command."""
    result = subprocess.run(
        [str(BUILD_SCRIPT)],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "CONTAINER_ENGINE": "podman",
            "DRY_RUN": "true",
        },
        check=False,
    )
    assert result.returncode == 0, result.stderr
    output = result.stdout.strip()
    assert "podman build" in output
    assert "--layers" in output


def test_makefile_uses_build_script(makefile_text: str) -> None:
    assert "BUILD_SCRIPT := scripts/build.sh" in makefile_text
    assert "$(BUILD_ENV) $(BUILD_SCRIPT)" in makefile_text


def test_makefile_has_cache_variables(makefile_text: str) -> None:
    required = [
        "CONTAINER_ENGINE",
        "IMAGE_NAME",
        "BUILD_CONTEXT",
        "BUILD_CACHE_FROM",
        "BUILD_CACHE_TO",
        "BUILDKIT_INLINE_CACHE",
        "BUILDKIT_PROGRESS",
        "PUSH_IMAGE",
        "VOLUME_LABEL",
    ]
    for var in required:
        assert f"{var} ?=" in makefile_text, f"missing Makefile variable: {var}"


def test_makefile_container_targets_use_build_script(makefile_text: str) -> None:
    # Each container test target should invoke the build script instead of a
    # hard-coded engine-specific build command.
    assert "podman build -t ha-audio-events-test" not in makefile_text
    assert "docker build -t ha-audio-events-test" not in makefile_text


def test_makefile_default_engine_auto_detects(makefile_text: str) -> None:
    """The Makefile must not force a default engine that diverges from CI."""
    assert "CONTAINER_ENGINE ?= podman" not in makefile_text
    # Auto-detection should prefer docker when available, matching CI and README.
    assert "command -v docker" in makefile_text
    assert "CONTAINER_ENGINE := docker" in makefile_text


def test_ci_uses_docker_with_buildkit_cache(ci_workflow_text: str) -> None:
    assert "CONTAINER_ENGINE: docker" in ci_workflow_text
    assert "BUILD_CACHE_FROM: type=gha" in ci_workflow_text
    assert "BUILD_CACHE_TO: type=gha,mode=max" in ci_workflow_text
    assert "BUILDKIT_INLINE_CACHE" in ci_workflow_text


def test_ci_sets_up_buildx(ci_workflow_text: str) -> None:
    assert "docker/setup-buildx-action" in ci_workflow_text


def test_dockerfile_uses_buildkit_syntax(dockerfile_text: str) -> None:
    assert dockerfile_text.startswith("# syntax=docker/dockerfile:1")
