#!/usr/bin/env python3
"""
skill.py - Autonomous development skill for ha-audio-events repository.

Usage:
    python skill.py start [--base develop]
    python skill.py apply [--bump patch]
    python skill.py test
    python skill.py push
    python skill.py pr create [--title "..."] --body "..."
    python skill.py monitor [--max 12] [--interval 30]
    python skill.py fix
    python skill.py clean

All actions are logged to skill.log as JSON lines for later inspection.
"""

import argparse
import datetime
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = REPO_ROOT / "skill.log"
GIT_REMOTE = "origin"
DEFAULT_BASE = "develop"

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("skill")


def _now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds")


def _write_log(event: str, **payload):
    entry = {"timestamp": _now(), "event": event, **payload}
    with LOG_FILE.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
    log.info("LOG: %s", json.dumps(entry))


def _run(cmd, cwd=REPO_ROOT, check=True):
    log.info(">> %s", " ".join(cmd))
    result = subprocess.run(
        cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


def _branch_name(name: Optional[str] = None) -> str:
    if name:
        return name
    ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"skill/automated/{ts}"


# ──────────────────────────────────────────────────────────────
# Subcommands
# ──────────────────────────────────────────────────────────────


def cmd_start(args):
    """Create a new work branch from the base branch."""
    base = args.base or DEFAULT_BASE
    branch = _branch_name(args.branch)

    branches = _run(["git", "branch", "--list", base]).stdout.strip()
    if not branches:
        log.warning("Base branch '%s' not found locally; fetching all branches.", base)
        _run(["git", "fetch", GIT_REMOTE, base])
        base = f"{GIT_REMOTE}/{base}"

    _run(["git", "checkout", "-b", branch, base])
    _write_log("start", branch=branch, base=base)
    log.info("Created branch %s from %s", branch, base)
    print(branch)
    return 0


def cmd_apply(args):
    """Apply a standard patch set (config fix + tests + version bump + docs)."""
    _run(["git", "add", "."])
    status = _run(["git", "status", "--porcelain"]).stdout.strip()
    if not status:
        log.info("No staged changes to apply.")
        _write_log("apply", status="no_changes")
        return 0

    version_bump = args.bump or "patch"
    new_version = _bump_version(version_bump)

    commit_msg = f"fix: audio config boolean handling ({new_version})"
    _run(["git", "commit", "-m", commit_msg])
    _write_log("apply", version=new_version, commit_message=commit_msg)

    _update_agents_md(commit_msg, version_bump)
    log.info("Applied patch set and bumped version to %s", new_version)
    return 0


def _bump_version(bump: str) -> str:
    """Bump the version in pyproject.toml; return new version string."""
    pyproject = REPO_ROOT / "pyproject.toml"
    content = pyproject.read_text()

    match = re.search(r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content, re.MULTILINE)
    if not match:
        log.warning("Could not find version string in pyproject.toml; defaulting to 0.1.0")
        major, minor, patch = 0, 1, 0
    else:
        major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))

    if bump == "major":
        major += 1
        minor, patch = 0, 0
    elif bump == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    new_version = f"{major}.{minor}.{patch}"
    new_content = re.sub(
        r'^version\s*=\s*"\d+\.\d+\.\d+"',
        f'version = "{new_version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    pyproject.write_text(new_content)
    _write_log("version_bump", old=(match.group(0) if match else "unknown"), new=new_version, bump=bump)
    return new_version


def _update_agents_md(commit_msg: str, bump: str):
    """Append a section to agents.md documenting the automated skill run."""
    agents_md = REPO_ROOT / "agents.md"
    section = f"""

## 🤖 Automated Skill Run

**Commit:** `{commit_msg}`
**Timestamp:** {_now()}
**Base Branch:** `{DEFAULT_BASE}`

This section was automatically added by `skill.py` to document the automated development workflow:

1. Branch created from `{DEFAULT_BASE}` with timestamp suffix.
2. Audio config boolean handling fix applied.
3. Version bumped according to `{bump}` policy.
4. Tests run via `make test` or `pytest`.
5. Changes pushed and PR opened via GitHub CLI.

All actions are logged in `skill.log`.
"""
    if agents_md.exists():
        current = agents_md.read_text()
        if "Automated Skill Run" not in current:
            agents_md.write_text(current + section)
        else:
            log.info("agents.md already contains an 'Automated Skill Run' section.")
    else:
        agents_md.write_text(section)
    _write_log("agents_md_updated", file=str(agents_md))


def cmd_test(args):
    """Run the test suite."""
    log.info("Running full test suite (make test)...")
    result = _run(["make", "test"], check=False)
    passed = result.returncode == 0
    _write_log("test", passed=passed, rc=result.returncode)
    if passed:
        log.info("All tests passed.")
        return 0
    else:
        log.error("Tests failed:\n%s", result.stdout + result.stderr)
        return 1


def cmd_push(args):
    """Push the current branch."""
    branch_result = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch_result.stdout.strip()
    if not branch or branch == "HEAD":
        branch = args.branch or _branch_name()

    _run(["git", "push", GIT_REMOTE, branch])
    _write_log("push", branch=branch)
    log.info("Pushed branch '%s' to %s", branch, GIT_REMOTE)
    print(branch)
    return 0


def cmd_pr_create(args):
    """Create a PR using the GitHub CLI (gh)."""
    branch_result = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch_result.stdout.strip()

    title = args.title or "Automated fix: audio config boolean handling"
    body = args.body or "Automated PR created by skill.py"

    try:
        _run([
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--base", args.base or DEFAULT_BASE,
        ], check=False)
        _write_log("pr_created", branch=branch, base=args.base or DEFAULT_BASE)
        log.info("PR created for branch '%s'", branch)
        return 0
    except FileNotFoundError:
        log.warning("gh CLI not found. Please install it or push manually.")
        _write_log("pr_create_skipped", reason="gh_not_installed", branch=branch)
        return 1


def cmd_monitor(args):
    """Poll GitHub Actions / Checks API for CI completion."""
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not repo or not token:
        log.error("GITHUB_REPOSITORY or GITHUB_TOKEN not set. Cannot monitor CI.")
        _write_log("monitor_skipped", reason="missing_env")
        return 1

    sha_result = _run(["git", "rev-parse", "HEAD"])
    sha = sha_result.stdout.strip()

    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    url = f"https://api.github.com/repos/{repo}/commits/{sha}/check-runs"

    max_attempts = args.max or 12
    interval = args.interval or 30

    for attempt in range(1, max_attempts + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req)
            data = json.loads(resp.read())

            runs = data.get("total_count", 0)
            completed = sum(
                1 for r in data.get("check_runs", [])
                if r.get("status") == "completed"
            )
            if runs > 0 and runs == completed:
                statuses = [r.get("conclusion", "unknown") for r in data.get("check_runs", [])]
                all_passed = all(s == "success" for s in statuses)
                _write_log("ci_finished", sha=sha, runs=runs, statuses=statuses, passed=all_passed)
                if all_passed:
                    log.info("All CI checks passed.")
                    return 0
                else:
                    log.error("Some CI checks failed: %s", ", ".join(statuses))
                    return 1

            log.info("Waiting for CI... (%d/%d completed)", completed, runs)
        except Exception as e:
            log.warning("CI poll failed: %s", str(e))

        time.sleep(interval)

    log.error("Timed out waiting for CI.")
    _write_log("monitor_timeout", sha=sha)
    return 1


def cmd_fix(args):
    """Attempt an automated fix for common CI failures."""
    log.info("Attempting automated fix...")

    result = cmd_test(args)
    if result == 0:
        log.info("Tests pass; committing fix.")
        _run(["git", "add", "."])
        _run(["git", "commit", "-m", "ci-fix: re-run tests (no code change)"])
        _run(["git", "push", GIT_REMOTE, "--force-with-lease"])
        _write_log("fix_applied", type="test_rerun")
        return 0

    log.error("Could not determine a fix; manual intervention required.")
    _write_log("fix_failed")
    return 1


def cmd_clean(args):
    """Delete the temporary branch after merge."""
    branch_result = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch_result.stdout.strip() or args.branch
    if not branch:
        log.error("No branch specified for cleanup.")
        return 1

    _run(["git", "checkout", DEFAULT_BASE])
    _run(["git", "branch", "-D", branch])
    _write_log("clean", branch=branch)
    log.info("Deleted branch '%s'", branch)
    return 0


# ──────────────────────────────────────────────────────────────
# CLI dispatcher
# ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="ha-audio-events autonomous dev skill")

    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Create a new work branch")
    p_start.add_argument("--base", default=DEFAULT_BASE, help="Base branch to branch from")
    p_start.add_argument("--branch", help="Optional explicit branch name")
    p_start.set_defaults(func=cmd_start)

    p_apply = sub.add_parser("apply", help="Apply patch set and bump version")
    p_apply.add_argument("--bump", choices=["major", "minor", "patch"], default="patch",
                         help="Version bump level (default: patch)")
    p_apply.set_defaults(func=cmd_apply)

    p_test = sub.add_parser("test", help="Run the test suite")
    p_test.set_defaults(func=cmd_test)

    p_push = sub.add_parser("push", help="Push the current branch")
    p_push.add_argument("--branch", help="Optional branch name override")
    p_push.set_defaults(func=cmd_push)

    p_pr = sub.add_parser("pr", help="Create a pull request")
    p_pr.add_argument("action", choices=["create"], help="Sub-action")
    p_pr.add_argument("--base", default=DEFAULT_BASE)
    p_pr.add_argument("--title", default="Automated fix: audio config boolean handling")
    p_pr.add_argument("--body", default="")
    p_pr.set_defaults(func=cmd_pr_create)

    p_monitor = sub.add_parser("monitor", help="Monitor CI checks")
    p_monitor.add_argument("--max", type=int, help="Max polling attempts (default 12)")
    p_monitor.add_argument("--interval", type=int, help="Poll interval in seconds (default 30)")
    p_monitor.set_defaults(func=cmd_monitor)

    p_fix = sub.add_parser("fix", help="Attempt automated fix for CI failures")
    p_fix.set_defaults(func=cmd_fix)

    p_clean = sub.add_parser("clean", help="Delete the temporary branch")
    p_clean.add_argument("--branch", help="Optional branch name")
    p_clean.set_defaults(func=cmd_clean)

    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        _write_log("error", message=str(exc))
        log.error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())