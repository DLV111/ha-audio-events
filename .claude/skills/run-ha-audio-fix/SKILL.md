---
name: ha-audio-fix
description: Create branch, apply changes, bump version, test, push PR, monitor CI, and auto-fix failures for the ha-audio-events project
---

# Autonomous Development Skill for ha-audio-events

This skill automates the full development workflow:
1. Create a work branch from develop
2. Apply code changes, run tests, bump version
3. Push branch and open PR
4. Monitor CI and auto-fix failures
5. Update agents.md documentation

## How to Invoke

```bash
/ha-audio-fix start
/ha-audio-fix apply --bump minor
/ha-audio-fix test
/ha-audio-fix push
/ha-audio-fix pr create --title "Fix: ..." --body "..."
/ha-audio-fix monitor
/ha-audio-fix fix
/ha-audio-fix clean
```

## Prerequisites

- GitHub CLI (`gh`) must be installed and authenticated
- Python 3.12+ with virtualenv (`.venv`)
- Project dependencies installed

## Driver

The skill is implemented as a Python driver at `.claude/skills/run-ha-audio-fix/driver.py` (symlinked to `skill/skill.py`).

All actions are logged to `skill.log` as JSON lines for auditability.