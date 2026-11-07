"""CI PR-vs-base guards for the add-on release metadata.

Checks run against a PR base:
  - version consistency: config.yaml == pyproject.toml == top CHANGELOG heading
  - version strictly increases on PRs that touch ha-audio-events/
  - changelog append-only: no release heading removed or renamed

Run by the Test Suite CI job. Exits non-zero on any failure.

The base ref is a git ref (e.g. ``origin/develop``). The head files come from
the current checkout (the PR head).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Ensure the app package is importable when running from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ha-audio-events" / "app"))

# Allow REPO_ROOT override via env var for testing.
REPO_ROOT = Path(os.environ.get(
    "CI_PR_VS_BASE_REPO_ROOT",
    str(Path(__file__).resolve().parents[1]))
)

from manifest import (
    check_changelog_append_only,
    check_version_consistency,
    check_version_increases,
)

ADDON_DIR = "ha-audio-events"


def _git_show(ref: str, path: str) -> str | None:
    """Return the file content at a git ref, or None if not present."""
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def _write_temp(content: str, suffix: str) -> str:
    import os

    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _changes_touch_ha_audio_events(base_ref: str) -> bool:
    """Check if the PR touches ha-audio-events/ files by comparing refs."""
    try:
        result = subprocess.run(
            ["git", "diff", base_ref, "HEAD", "--name-only", "ha-audio-events/"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return len(result.stdout.strip()) > 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def main(base_ref: str = "origin/develop") -> int:
    errors: list[str] = []

    # Verify the base ref can be resolved
    if base_ref and base_ref != "HEAD":
        base_config_content = _git_show(base_ref, f"{ADDON_DIR}/config.yaml")
        if base_config_content is None:
            print(f"ERROR: base ref '{base_ref}' not found; is fetch-depth 0 set?")
            return 1
        base_changelog_content = _git_show(base_ref, f"{ADDON_DIR}/CHANGELOG.md")
        if base_changelog_content is None:
            print(f"ERROR: base ref '{base_ref}' not found; is fetch-depth 0 set?")
            return 1

        base_config_path = _write_temp(base_config_content, ".yaml")
        base_changelog_path = _write_temp(base_changelog_content, ".md")
    else:
        base_config_path = None
        base_changelog_path = None

    # Version consistency across config.yaml, pyproject.toml, and CHANGELOG.md.
    head_config = REPO_ROOT / ADDON_DIR / "config.yaml"
    head_pyproject = REPO_ROOT / "pyproject.toml"
    head_changelog = REPO_ROOT / ADDON_DIR / "CHANGELOG.md"

    errors.extend(
        check_version_consistency(head_config, head_pyproject, head_changelog)
    )

    # Only check version increase if add-on files changed
    if base_ref and base_ref != "HEAD":
        if _changes_touch_ha_audio_events(base_ref):
            errors.extend(check_version_increases(base_config_path, head_config))
        errors.extend(check_changelog_append_only(base_changelog_path, head_changelog))

    # Clean up temp files.
    for p in (base_config_path, base_changelog_path):
        if p:
            try:
                import os

                os.unlink(p)
            except OSError:
                pass

    if errors:
        print("ERROR: PR-vs-base checks failed:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("PR-vs-base checks passed.")
    return 0


if __name__ == "__main__":
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "origin/develop"
    sys.exit(main(base_ref))
