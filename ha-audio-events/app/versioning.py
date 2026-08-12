from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def bump_version(new_version: str, root: Path | None = None) -> list[Path]:
    """Update version references in the add-on manifests and python package metadata."""
    # Find the repository root (where pyproject.toml lives)
    # Script is at ha-audio-events/app/versioning.py, so parents[2] = repo root
    if root is None:
        script_path = Path(__file__).resolve()
        # Go up to find pyproject.toml (repo root)
        project_root = script_path.parents[2]
        # Verify we found the right place
        if not (project_root / "pyproject.toml").exists():
            # Fallback: try parents[1] in case structure is different
            project_root = script_path.parents[1]
    else:
        project_root = Path(root)

    targets = [
        project_root / "pyproject.toml",
        project_root / "ha-audio-events" / "config.yaml",
        project_root / "ha-audio-events" / "config.json",
    ]

    updated_files: list[Path] = []

    for target in targets:
        if not target.exists():
            continue

        content = target.read_text(encoding="utf-8")

        if target.suffix == ".json":
            data = json.loads(content)
            data["version"] = new_version
            target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        else:
            if target.name == "pyproject.toml":
                pattern = re.compile(
                    r'(^version\s*=\s*)(["\'][^"\']+["\'])', re.MULTILINE
                )
                updated = pattern.sub(rf'\g<1>"{new_version}"', content)
            else:
                pattern = re.compile(r"(^version:\s*)(.+)$", re.MULTILINE)
                updated = pattern.sub(rf"\g<1>{new_version}", content)
            target.write_text(updated, encoding="utf-8")

        updated_files.append(target)

    return updated_files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bump the add-on version in all release manifests"
    )
    parser.add_argument("version", help="New version string, e.g. 0.2.0")
    args = parser.parse_args()

    updated = bump_version(args.version)
    for path in updated:
        print(path)


if __name__ == "__main__":
    main()
