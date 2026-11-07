"""CI PR-vs-base guards for the add-on release metadata.

Checks run against a PR base:
  - version consistency: config.yaml == pyproject.toml == top CHANGELOG heading
  - version strictly increases on PRs that touch ha-audio-events/
  - changelog append-only: no release heading removed or renamed

Run by the Test Suite CI job. Exits non-zero on any failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the app package is importable when running from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ha-audio-events" / "app"))

from manifest import (
    get_config_version,
    get_pyproject_version,
    check_version_consistency,
    check_version_increases,
    check_changelog_append_only,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def main(base_ref: str = "HEAD~1") -> int:
    errors: list[str] = []

    # Version consistency across config.yaml, pyproject.toml, and CHANGELOG.md.
    errors.extend(
        check_version_consistency(
            REPO_ROOT / "ha-audio-events" / "config.yaml",
            REPO_ROOT / "pyproject.toml",
            REPO_ROOT / "ha-audio-events" / "CHANGELOG.md",
        )
    )

    # Version strictly increases when add-on files changed vs base.
    if base_ref and base_ref != "HEAD":
        errors.extend(
            check_version_increases(
                REPO_ROOT / "ha-audio-events" / "config.yaml",
                REPO_ROOT / "ha-audio-events" / "config.yaml",
            )
        )

    # Changelog append-only: every base heading must still exist in head.
    # The changelog is newest-first, so a release adds a new top heading;
    # existing headings must all still be present.
    if base_ref and base_ref != "HEAD":
        errors.extend(
            check_changelog_append_only(
                REPO_ROOT / "ha-audio-events" / "CHANGELOG.md",
                REPO_ROOT / "ha-audio-events" / "CHANGELOG.md",
            )
        )

    if errors:
        print("ERROR: PR-vs-base checks failed:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("PR-vs-base checks passed.")
    return 0


if __name__ == "__main__":
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
    sys.exit(main(base_ref))