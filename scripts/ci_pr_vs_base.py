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

import subprocess
import sys
import tempfile
from pathlib import Path

# Ensure the app package is importable when running from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ha-audio-events" / "app"))

from manifest import (
    check_changelog_append_only,
    check_version_consistency,
    check_version_increases,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
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


def main(base_ref: str = "origin/develop") -> int:
    errors: list[str] = []

    # Version consistency across config.yaml, pyproject.toml, and CHANGELOG.md.
    head_config = REPO_ROOT / ADDON_DIR / "config.yaml"
    head_pyproject = REPO_ROOT / "pyproject.toml"
    head_changelog = REPO_ROOT / ADDON_DIR / "CHANGELOG.md"

    base_config_content = _git_show(base_ref, f"{ADDON_DIR}/config.yaml")
    base_changelog_content = _git_show(base_ref, f"{ADDON_DIR}/CHANGELOG.md")

    base_config_path = base_config_content and _write_temp(base_config_content, ".yaml")
    base_changelog_path = base_changelog_content and _write_temp(
        base_changelog_content, ".md"
    )

    errors.extend(
        check_version_consistency(head_config, head_pyproject, head_changelog)
    )

    if base_ref and base_ref != "HEAD":
        errors.extend(
            check_version_increases(
                base_config_path or head_config,
                head_config,
            )
        )
        errors.extend(
            check_changelog_append_only(
                base_changelog_path or head_changelog,
                head_changelog,
            )
        )

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
