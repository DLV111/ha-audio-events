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


def _logical_instructions(dockerfile_text: str) -> list[str]:
    """Return Dockerfile instructions with backslash continuations joined.

    Comments are stripped so tests match only executable content.
    """
    instructions: list[str] = []
    current: list[str] = []
    for raw_line in dockerfile_text.splitlines():
        code = raw_line.split("#", 1)[0].rstrip()
        if not code.strip():
            continue
        if current:
            current.append(code)
        else:
            current = [code]
        if not code.endswith("\\"):
            instructions.append(" ".join(current))
            current = []
    if current:
        instructions.append(" ".join(current))
    return [instruction.replace("\\", " ") for instruction in instructions]


def test_cache_mount_targets_not_purged(dockerfile_text: str) -> None:
    """RUN steps must not delete apt paths that live under a cache mount.

    ``/var/lib/apt/lists`` and ``/var/cache/apt`` are mounted as BuildKit cache
    volumes, so ``rm -rf`` on them does not shrink the image (mount contents are
    never committed to layers) -- it only wipes the shared cache, forcing every
    subsequent build to re-download apt package lists. The classic
    ``rm -rf /var/lib/apt/lists/*`` cleanup must therefore stay out of the
    Dockerfile wherever those paths are cache-mounted.
    """
    cache_mounted = any(
        f"target={path}" in dockerfile_text
        for path in ("/var/cache/apt", "/var/lib/apt/lists", "/root/.cache/pip")
    )
    if not cache_mounted:
        pytest.skip("no cache mounts present in Dockerfile")
    code = "\n".join(_logical_instructions(dockerfile_text))
    for target in ("/var/cache/apt", "/var/lib/apt/lists", "/root/.cache/pip"):
        assert f"rm -rf {target}" not in code, (
            f"'rm -rf {target}' purges a shared cache mount; remove it so warm "
            "builds can reuse the cached apt/pip data"
        )


def _split_stages(dockerfile_text: str) -> list[list[str]]:
    """Split the Dockerfile into stages, each stage a list of instruction lines."""
    stages: list[list[str]] = [[]]
    for raw_line in dockerfile_text.splitlines():
        line = raw_line.strip()
        if line.upper().startswith("FROM") and stages[-1]:
            stages.append([])
        stages[-1].append(line)
    return stages


def test_build_tooling_confined_to_builder_stage(dockerfile_text: str) -> None:
    """Build tooling must not ship in the runtime image.

    Installing build-essential (or gcc/make) in the final stage would bloat the
    runtime image and re-introduce the size regression the multi-stage build
    removed.
    """
    stages = _split_stages(dockerfile_text)
    assert len(stages) >= 2, "expected a multi-stage Dockerfile"
    runtime_stage = stages[-1]
    for line in runtime_stage:
        instruction = line.split("#", 1)[0].strip()
        if instruction.upper().startswith(("RUN", "ENV", "ARG")):
            for tool in ("build-essential", "gcc", "g++", "make"):
                assert (
                    tool not in instruction
                ), f"build tooling '{tool}' leaked into the runtime stage: {line}"


def test_pip_cache_mount_not_bypassed(dockerfile_text: str) -> None:
    """pip must be allowed to use the BuildKit pip cache mount.

    pip's cache-disabling flags (``--no-cache-dir`` and the equivalent
    ``PIP_NO_CACHE_DIR`` env var) make pip bypass its HTTP cache entirely, so
    a ``--mount=type=cache,target=/root/.cache/pip`` would never populate and
    every build re-downloads every wheel. With the cache mount in place, pip's
    cache lives in the mount -- not the layer -- so there is no image-size
    reason to disable it.
    """
    instructions = _logical_instructions(dockerfile_text)
    pip_steps = [i for i in instructions if "pip install" in i]
    assert pip_steps, "expected a pip install instruction"
    assert any(
        "target=/root/.cache/pip" in i for i in instructions
    ), "expected a pip cache mount in the Dockerfile"
    for instruction in pip_steps:
        assert (
            "--no-cache-dir" not in instruction
        ), f"pip cache-disabling flag defeats the pip cache mount: {instruction}"
    assert not any(
        "PIP_NO_CACHE_DIR" in i for i in instructions
    ), "PIP_NO_CACHE_DIR env would make pip bypass the cache mount"


def test_apt_docker_clean_disabled(dockerfile_text: str) -> None:
    """Every apt install step must disable Debian's docker-clean apt config.

    Debian's stock /etc/apt/apt.conf.d/docker-clean deletes
    /var/cache/apt/archives/*.deb after each apt-get update/install. With the
    archives cache mount in place, those rm hooks delete the *shared cache*,
    forcing every build to re-download all .debs. Removing the config file
    keeps the archives in the mount; the mount itself keeps them out of the
    image layer.
    """
    apt_steps = [
        i for i in _logical_instructions(dockerfile_text) if "apt-get install" in i
    ]
    assert apt_steps, "expected at least one apt-get install RUN step"
    for instruction in apt_steps:
        assert (
            "rm -f /etc/apt/apt.conf.d/docker-clean" in instruction
        ), f"apt install step does not disable docker-clean: {instruction}"


def test_app_bytecode_precompiled(dockerfile_text: str) -> None:
    """Application bytecode must be compiled at build time.

    The runtime stage sets PYTHONDONTWRITEBYTECODE=1 so the container's
    filesystem stays clean at runtime; without shipped __pycache__ directories
    CPython would recompile every app module on every container start. A
    build-time ``compileall`` keeps startup fast without runtime writes.
    """
    copy_pos = dockerfile_text.find("COPY . /app")
    compile_pos = dockerfile_text.find("compileall")
    entrypoint_pos = dockerfile_text.find('ENTRYPOINT ["/app/run.sh"]')
    assert copy_pos != -1, "expected 'COPY . /app'"
    assert (
        compile_pos != -1
    ), "expected a build-time 'python -m compileall' step for app bytecode"
    assert entrypoint_pos != -1, "expected the runtime ENTRYPOINT"
    assert (
        copy_pos < compile_pos < entrypoint_pos
    ), "compileall must run after the source COPY and before the ENTRYPOINT"


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


def test_dockerignore_cache_patterns_match_nested(dockerignore_text: str) -> None:
    """Cache/bytecode patterns must be anchored with '**/' so they match
    directories nested under app/, models/, etc.

    .dockerignore patterns are rooted at the context root; a bare
    '__pycache__/' only matches a top-level directory and lets nested
    caches ship into the image via 'COPY . /app'.
    """
    for pattern in ("__pycache__/", "*.py[cod]", ".pytest_cache/", ".coverage"):
        assert f"**/{pattern}" in dockerignore_text, (
            f"pattern '{pattern}' is not '**/'-anchored; nested caches would "
            "be copied into the runtime image"
        )


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
