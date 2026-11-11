"""Tests that container build workflow documentation is complete and consistent.

These tests guard the README and agents.md sections added for the optimized
container build workflow. They are pure string checks, so no container builds
are required.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
AGENTS = REPO_ROOT / "agents.md"
VALIDATION_DOC = REPO_ROOT / "docs" / "container-build-validation.md"


@pytest.fixture(scope="module")
def readme_text() -> str:
    assert README.is_file()
    return README.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def agents_text() -> str:
    assert AGENTS.is_file()
    return AGENTS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def validation_text() -> str:
    assert VALIDATION_DOC.is_file()
    return VALIDATION_DOC.read_text(encoding="utf-8")


def test_readme_has_container_build_section(readme_text: str) -> None:
    assert "## Container Build" in readme_text
    assert "scripts/build.sh" in readme_text
    assert "make build-container" in readme_text


def test_readme_explains_cache_behavior(readme_text: str) -> None:
    assert "### How the cache works" in readme_text
    assert "Layer caching" in readme_text
    assert "BuildKit cache mounts" in readme_text
    assert "/var/cache/apt" in readme_text
    assert "/root/.cache/pip" in readme_text
    assert "BUILDKIT_INLINE_CACHE" in readme_text


def test_readme_has_expected_build_times_table(readme_text: str) -> None:
    assert "### Expected build times" in readme_text
    assert "image size" in readme_text
    assert "rebuild after source change" in readme_text
    assert "rebuild after dependency change" in readme_text
    assert "fully cold build" in readme_text


def test_readme_includes_before_after_metrics(readme_text: str) -> None:
    assert "1010 MiB" in readme_text
    assert "716 MiB" in readme_text
    assert "19.6 s" in readme_text
    assert "4.4 s" in readme_text
    assert "−78%" in readme_text or "-78%" in readme_text


def test_readme_has_container_troubleshooting(readme_text: str) -> None:
    assert (
        "### Troubleshooting container builds / Home Assistant updates" in readme_text
    )
    assert "Add-on update seems to hang" in readme_text
    assert "cache not reused" in readme_text
    assert "SELinux" in readme_text
    assert "docker buildx" in readme_text


def test_agents_has_container_build_workflow_section(agents_text: str) -> None:
    assert "### Container Build Workflow" in agents_text
    assert "scripts/build.sh" in agents_text
    assert "make test-container" in agents_text
    assert "measure_build_times.sh" in agents_text


def test_agents_documents_caching_behaviour(agents_text: str) -> None:
    assert "#### Caching behaviour" in agents_text
    assert "Layer caching" in agents_text
    assert "BuildKit cache mounts" in agents_text
    assert "type=gha" in agents_text


def test_agents_has_expected_times(agents_text: str) -> None:
    assert "#### Expected build times" in agents_text
    assert "1010 MiB" in agents_text
    assert "716 MiB" in agents_text
    assert "113.4 s" in agents_text


def test_agents_has_container_troubleshooting(agents_text: str) -> None:
    assert "#### Troubleshooting container builds" in agents_text
    assert "Podman-backed" in agents_text
    assert "SELinux" in agents_text


def test_validation_doc_records_metrics(validation_text: str) -> None:
    assert "Measured results" in validation_text
    assert "716MiB" in validation_text or "716 MiB" in validation_text
    assert "1010MiB" in validation_text or "1010 MiB" in validation_text
    assert "warm-source-change" in validation_text
    assert "warm-deps-change" in validation_text
