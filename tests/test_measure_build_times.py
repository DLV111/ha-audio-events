"""Tests for scripts/measure_build_times.sh.

These tests guard the build-time benchmarking script used to validate the
optimized Dockerfile against the pre-optimization baseline (see
docs/container-build-validation.md). They only exercise static content and
--dry-run execution, so no container builds happen inside the test suite.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "measure_build_times.sh"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build.sh"


@pytest.fixture(scope="module")
def script_text() -> str:
    if not SCRIPT.exists():
        pytest.fail(f"Measurement script not found at {SCRIPT}")
    return SCRIPT.read_text()


def _run(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=120,
    )


def _fake_docker_bin(tmp_path: Path, *, shim: bool = False) -> Path:
    """Create a fake 'docker'.

    With shim=True it emulates the Podman compatibility shim (the string
    'podman' in --version output); otherwise a real Docker + buildx.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    version = "podman version 4.9.3" if shim else "Docker version 24.0.7, build afdd53b"
    docker.write_text(
        "#!/usr/bin/env bash\n"
        'case "$1 $2" in\n'
        "  ' --version'|'--version ')\n"
        f"    echo '{version}'\n"
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


def test_help_lists_scenarios(script_text: str) -> None:
    result = _run({**os.environ}, "--help")
    assert result.returncode == 0, result.stderr
    for scenario in (
        "cold",
        "warm",
        "warm-source-change",
        "warm-deps-change",
        "warm-no-layer-cache",
    ):
        assert scenario in result.stdout


def test_unknown_option_rejected() -> None:
    result = _run({**os.environ}, "--no-such-option")
    assert result.returncode != 0
    assert "unknown option" in result.stderr


def test_unknown_scenario_rejected() -> None:
    result = _run({**os.environ}, "--scenarios", "not-a-scenario")
    assert result.returncode != 0
    assert "unknown scenario" in result.stderr


def test_dry_run_builds_podman_layers() -> None:
    """A dry run with Podman must print (not run) a layered build command."""
    result = _run(
        {**os.environ, "CONTAINER_ENGINE": "podman"},
        "--dry-run",
        "--scenarios",
        "cold",
    )
    assert result.returncode == 0, result.stderr
    assert "podman build --layers" in result.stdout
    # Cold builds must bypass the layer cache.
    assert "--no-cache" in result.stdout


def test_dry_run_builds_docker_shim_layers() -> None:
    """The Podman-backed docker shim must also get --layers."""
    with tempfile.TemporaryDirectory() as tmp:
        fake_bin = _fake_docker_bin(Path(tmp), shim=True)
        result = _run(
            {
                **os.environ,
                "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
                "CONTAINER_ENGINE": "docker",
            },
            "--dry-run",
            "--scenarios",
            "cold",
        )
    assert result.returncode == 0, result.stderr
    assert "docker-shim(podman)" in result.stdout
    assert "docker build --layers" in result.stdout


def test_dry_run_cold_clears_buildah_mount_cache() -> None:
    """Cold builds must clear the persistent BuildKit cache mounts."""
    result = _run(
        {**os.environ, "CONTAINER_ENGINE": "podman"},
        "--dry-run",
        "--scenarios",
        "cold",
    )
    assert result.returncode == 0, result.stderr
    assert "buildah-cache-" in result.stdout


def test_dry_run_primes_before_warm_measurements() -> None:
    """Warm scenarios must prime the cache before the measured build."""
    result = _run(
        {**os.environ, "CONTAINER_ENGINE": "podman"},
        "--dry-run",
        "--scenarios",
        "warm,warm-source-change",
    )
    assert result.returncode == 0, result.stderr
    assert "priming build" in result.stdout
    # The measured build after a source change must NOT pass --no-cache:
    # it exists to exercise layer-cache reuse, so a --no-cache would defeat
    # its purpose.
    warm_section = result.stdout.split("==> scenario: warm-source-change")[-1]
    dry_builds = [line for line in warm_section.splitlines() if "DRY-RUN:" in line]
    assert dry_builds, "expected dry-run build commands"
    assert not any("--no-cache" in line for line in dry_builds)
    assert any("app/main.py" in line for line in warm_section.splitlines())


def test_dry_run_deps_change_marks_requirements() -> None:
    result = _run(
        {**os.environ, "CONTAINER_ENGINE": "podman"},
        "--dry-run",
        "--scenarios",
        "warm-deps-change",
    )
    assert result.returncode == 0, result.stderr
    assert "requirements.txt" in result.stdout


def test_dry_run_writes_valid_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        json_path = Path(tmp) / "out.json"
        result = _run(
            {**os.environ, "CONTAINER_ENGINE": "podman"},
            "--dry-run",
            "--scenarios",
            "cold,warm",
            "--json",
            str(json_path),
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(json_path.read_text())
    assert data["engine"] == "podman"
    assert [r["scenario"] for r in data["results"]] == ["cold", "warm"]
    assert all("seconds" in r for r in data["results"])


def test_scenarios_match_documented_set(script_text: str) -> None:
    """Every scenario handled by the script must appear in its usage text."""
    handled = {
        "cold",
        "warm",
        "warm-source-change",
        "warm-deps-change",
        "warm-no-layer-cache",
    }
    case_block = script_text.split("usage() {")[1].split("EOF\n}")[0]
    for scenario in handled:
        assert scenario in case_block, f"scenario missing from usage: {scenario}"


def test_standard_scenarios_default(script_text: str) -> None:
    assert "cold,warm,warm-source-change,warm-deps-change" in script_text


def test_script_documented_in_build_script(script_text: str) -> None:
    """The benchmark script should be referenced from the build docs."""
    readme = (REPO_ROOT / "README.md").read_text()
    assert "measure_build_times" in readme


def test_validation_results_documented(script_text: str) -> None:
    """README claims results live in docs/container-build-validation.md."""
    readme = (REPO_ROOT / "README.md").read_text()
    assert "docs/container-build-validation.md" in readme
    doc = REPO_ROOT / "docs" / "container-build-validation.md"
    assert doc.is_file(), "validation results document is missing"
    text = doc.read_text()
    # The doc must actually record measured scenario results.
    for scenario in ("cold", "warm", "warm-source-change"):
        assert scenario in text, f"scenario '{scenario}' not documented"


def test_build_script_and_measure_script_agree_on_engine_detection(
    script_text: str,
) -> None:
    """Both scripts must auto-detect the same engine order (docker first)."""
    assert "command -v docker >/dev/null 2>&1" in script_text
    assert "command -v podman >/dev/null 2>&1" in script_text
    build_text = BUILD_SCRIPT.read_text()
    docker_first = script_text.index("command -v docker") < script_text.index(
        "command -v podman"
    )
    build_docker_first = build_text.index("command -v docker") < build_text.index(
        "command -v podman"
    )
    assert docker_first == build_docker_first
    assert docker_first
