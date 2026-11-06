"""CI PR-vs-base guards for the add-on release metadata.

Checks run against a PR base:
  - version consistency: config.yaml == pyproject.toml == top CHANGELOG heading
  - version strictly increases on PRs that touch ha-audio-events/
  - changelog append-only: no release heading removed or renamed

Run by the Test Suite CI job. Exits non-zero on any failure.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CONFIG_PATH = REPO_ROOT / "ha-audio-events" / "config.yaml"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
CHANGELOG_PATH = REPO_ROOT / "ha-audio-events" / "CHANGELOG.md"

VERSION_HEADING_RE = re.compile(r"^## \[([^\]]+)\]", re.MULTILINE)


def get_version_from_config(path: Path) -> str | None:
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return str(data.get("version")) if data.get("version") is not None else None
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None


def get_version_from_toml(path: Path) -> str | None:
    content = path.read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
    return match.group(1) if match else None


def get_changelog_headings(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    return [m.group(1) for m in VERSION_HEADING_RE.finditer(content)]


def changed_addon_paths(base_sha: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", base_sha, "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip().startswith("ha-audio-events/")
    ]


def main(base_ref: str = "HEAD~1") -> int:

    errors: list[str] = []
    head_config_ver = get_version_from_config(CONFIG_PATH)
    head_toml_ver = get_version_from_toml(PYPROJECT_PATH)
    head_headings = get_changelog_headings(CHANGELOG_PATH)
    head_changelog_ver = head_headings[0] if head_headings else None

    versions: dict[str, str | None] = {
        "config.yaml": head_config_ver,
        "pyproject.toml": head_toml_ver,
        "CHANGELOG.md": head_changelog_ver,
    }
    for label, ver in versions.items():
        if ver is None:
            errors.append(f"{label}: version not found")

    non_none = {v for v in versions.values() if v is not None}
    if len(non_none) > 1:
        errors.append(
            "Version mismatch: " + ", ".join(f"{k}={v}" for k, v in versions.items())
        )

    # Version strictly increases when add-on files changed vs base.
    if base_ref and base_ref != "HEAD":
        try:
            base_sha = subprocess.run(
                ["git", "rev-parse", base_ref],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except subprocess.CalledProcessError:
            # Base ref not available (e.g. shallow checkout); skip base comparison.
            base_sha = None
        if base_sha and changed_addon_paths(base_sha):
            # Compare with base version; base files may not be checked out, so
            # compare via git show.
            base_config_text = subprocess.run(
                ["git", "show", f"{base_sha}:ha-audio-events/config.yaml"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            import yaml as _yaml

            base_data = _yaml.safe_load(base_config_text) or {}
            base_ver = (
                str(base_data.get("version"))
                if base_data.get("version") is not None
                else None
            )
            if base_ver and head_config_ver:
                try:
                    from packaging.version import Version

                    if Version(str(head_config_ver)) <= Version(base_ver):
                        errors.append(
                            f"Version must strictly increase: {base_ver} -> {head_config_ver}"
                        )
                except (ValueError, TypeError):
                    errors.append("Invalid version format for version increase check")

    # Changelog append-only: base headings must be prefix of head headings.
    if base_ref and base_ref != "HEAD":
        try:
            base_sha = subprocess.run(
                ["git", "rev-parse", base_ref],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except subprocess.CalledProcessError:
            # Base ref not available (e.g. shallow checkout); skip changelog comparison.
            base_sha = None
        if base_sha:
            base_headings = subprocess.run(
                ["git", "show", f"{base_sha}:ha-audio-events/CHANGELOG.md"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            import re as _re

            base_versions = [
                m.group(1)
                for m in _re.finditer(r"^## \[([^\]]+)\]", base_headings, _re.MULTILINE)
            ]
            for i, base_ver in enumerate(base_versions):
                if i >= len(head_headings) or head_headings[i] != base_ver:
                    errors.append(
                        f"Changelog heading removed or changed at index {i}: {base_ver} -> {head_headings[i] if i < len(head_headings) else '<missing>'}"
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
