"""Tests for ci_pr_vs_base.py script using temporary git repositories."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from ci_pr_vs_base import main


def run_git(repo_path, *args):
    """Run git command in repo."""
    result = subprocess.run(["git", *args], cwd=repo_path, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result


def write_file(repo_path, rel_path, content):
    """Write file to repo."""
    full_path = repo_path / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content)


def create_base_repo(tmp_path):
    """Create a base git repo with develop branch and a PR branch."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    run_git(repo_path, "init")
    run_git(repo_path, "config", "user.email", "test@example.com")
    run_git(repo_path, "config", "user.name", "Test User")

    addon_dir = repo_path / "ha-audio-events"
    addon_dir.mkdir()

    # pyproject.toml at repo root
    write_file(repo_path, "pyproject.toml", """[project]
name = "ha-audio-events"
version = "0.10.1"
""")

    # config.yaml and CHANGELOG.md inside ha-audio-events/
    write_file(repo_path, "ha-audio-events/config.yaml", """name: HA Audio Events
slug: ha_audio_events
version: 0.10.1
description: Home Assistant add-on for audio event detection using TensorFlow Lite.
""")

    write_file(repo_path, "ha-audio-events/CHANGELOG.md", """## [0.10.1] - 2026-11-06
### Fixed
- CI guards restored.
""")

    run_git(repo_path, "add", ".")
    run_git(repo_path, "commit", "-m", "Initial commit")

    # Create develop branch as the base ref
    run_git(repo_path, "branch", "develop")

    # Create a PR branch from develop
    run_git(repo_path, "checkout", "-b", "pr-branch", "develop")

    return repo_path


def test_docs_only_pr_passes(tmp_path):
    """Test that a docs-only PR (no add-on changes) passes."""
    repo_path = create_base_repo(tmp_path)

    # Add a documentation file only (no add-on changes)
    write_file(repo_path, "docs/README.md", "# Documentation")
    run_git(repo_path, "add", "docs/")
    run_git(repo_path, "commit", "-m", "Add documentation")

    exit_code = main('develop', repo_root=repo_path)
    assert exit_code == 0, f"Expected exit code 0, got {exit_code}"


def test_add_on_change_without_version_bump_fails(tmp_path):
    """Test that add-on changes without version bump fail."""
    repo_path = create_base_repo(tmp_path)

    # Make a change to config.yaml inside ha-audio-events/ without changing version
    write_file(repo_path, "ha-audio-events/config.yaml", """name: HA Audio Events
slug: ha_audio_events
version: 0.10.1
description: Home Assistant add-on for audio event detection using TensorFlow Lite.
# Added a comment
""")

    run_git(repo_path, "add", ".")
    run_git(repo_path, "commit", "-m", "Add comment to config.yaml")

    exit_code = main('develop', repo_root=repo_path)
    # Should fail because version didn't increase
    assert exit_code != 0, f"Expected non-zero exit code, got {exit_code}"


def test_version_bump_with_new_top_changelog_heading_passes(tmp_path):
    """Test that version bump with new top changelog heading passes."""
    repo_path = create_base_repo(tmp_path)

    # Bump version in pyproject.toml and config.yaml to 0.10.2
    write_file(repo_path, "pyproject.toml", """[project]
name = "ha-audio-events"
version = "0.10.2"
""")

    write_file(repo_path, "ha-audio-events/config.yaml", """name: HA Audio Events
slug: ha_audio_events
version: 0.10.2
description: Home Assistant add-on for audio event detection using TensorFlow Lite.
""")

    # Add new top heading in CHANGELOG.md
    write_file(repo_path, "ha-audio-events/CHANGELOG.md", """## [0.10.2] - 2026-11-07
### Added
- New feature.

## [0.10.1] - 2026-11-06
### Fixed
- CI guards restored.
""")

    run_git(repo_path, "add", ".")
    run_git(repo_path, "commit", "-m", "Bump version to 0.10.2 and add changelog entry")

    exit_code = main('develop', repo_root=repo_path)
    assert exit_code == 0, f"Expected exit code 0, got {exit_code}"


def test_deleted_changelog_heading_fails(tmp_path):
    """Test that deleted changelog heading fails."""
    repo_path = create_base_repo(tmp_path)

    # Create a second commit with version 0.10.2 (base has two headings)
    write_file(repo_path, "pyproject.toml", """[project]
name = "ha-audio-events"
version = "0.10.2"
""")

    write_file(repo_path, "ha-audio-events/config.yaml", """name: HA Audio Events
slug: ha_audio_events
version: 0.10.2
description: Home Assistant add-on for audio event detection using TensorFlow Lite.
""")

    write_file(repo_path, "ha-audio-events/CHANGELOG.md", """## [0.10.2] - 2026-11-07
### Added
- New feature.

## [0.10.1] - 2026-11-06
### Fixed
- CI guards restored.
""")

    run_git(repo_path, "add", ".")
    run_git(repo_path, "commit", "-m", "Bump to 0.10.2")

    # Now delete one heading (0.10.2) - keep only 0.10.1
    write_file(repo_path, "ha-audio-events/CHANGELOG.md", """## [0.10.1] - 2026-11-06
### Fixed
- CI guards restored.
""")

    run_git(repo_path, "add", ".")
    run_git(repo_path, "commit", "-m", "Delete 0.10.2 heading")

    exit_code = main('develop', repo_root=repo_path)
    # Should fail because changelog heading was deleted
    assert exit_code != 0, f"Expected non-zero exit code, got {exit_code}"


def test_missing_base_fails_with_clear_message(tmp_path):
    """Test that missing base ref fails with clear error message."""
    repo_path = create_base_repo(tmp_path)

    # Capture stdout to check error message
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    exit_code = main('non-existent-branch', repo_root=repo_path)

    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    # Should fail with message about missing base ref
    assert exit_code != 0, f"Expected non-zero exit code, got {exit_code}"
    assert "base ref 'non-existent-branch' not found" in output, \
        f"Expected error message not found in output: {output}"


def test_base_head_with_no_changes_passes(tmp_path):
    """Test that base == head with no changes passes."""
    repo_path = create_base_repo(tmp_path)

    # Switch back to develop (HEAD == develop)
    run_git(repo_path, "checkout", "develop")

    exit_code = main('HEAD', repo_root=repo_path)
    # Should pass because version didn't change and changelog didn't change
    assert exit_code == 0, f"Expected exit code 0, got {exit_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
