---
name: obsidian-diary-git
description: Save diary entries as Obsidian-compatible Markdown in a Git-backed vault clone on a dedicated branch. Use for Hermes daily diary capture and approved diary writes.
version: 0.1.0
author: backup-secretary
license: MIT
metadata:
  hermes:
    tags: [obsidian, diary, git, markdown, personal-knowledge]
    related_skills: [obsidian, write-and-forget-capture]
---

# Obsidian Diary Git

## Purpose

Write private diary entries to an Obsidian vault repo as Markdown, without putting diary text into Hermes standard memory.

This skill intentionally uses a **Git clone under persistent Hermes data** instead of requiring an extra Docker bind mount. In the user's backup-secretary deployment, `/opt/data` is already persistent, so the default clone path survives container restarts:

```text
/opt/data/obsidian/obsidian_git
```

## Branch policy

Use a dedicated branch:

```text
hermes
```

Do **not** write diary entries to `main`. The `hermes` branch is intentionally allowed to be messy/breakable while the workflow stabilizes.

## Default repo

User-provided Obsidian repo:

```text
git@github.com:ktakahiro150397/obsidian_git.git
```

In the current container, SSH auth may be unavailable. `gh` auth works with HTTPS, so the live clone can use:

```text
https://github.com/ktakahiro150397/obsidian_git.git
```

## Commands

From the skill directory:

```bash
python3 scripts/obsidian_diary.py status
python3 scripts/obsidian_diary.py save "\u4eca\u65e5\u306fHermes\u306e\u65e5\u8a18\u4fdd\u5b58\u3092\u8a66\u3057\u305f" --source hermes-discord --tags diary,hermes
python3 scripts/obsidian_diary.py save "push\u305b\u305a\u306b\u691c\u8a3c" --no-push --no-pull
```

Explicit vault/repo/branch:

```bash
python3 scripts/obsidian_diary.py \\
  --vault /opt/data/obsidian/obsidian_git \\
  --repo https://github.com/ktakahiro150397/obsidian_git.git \\
  --branch hermes \\
  save "\u65e5\u8a18\u672c\u6587" --source hermes-discord --tags diary
```

## Preferred: execute_code direct import (avoids CLI escaping issues)

The recommended way to use this skill from Hermes is `execute_code`, importing the module directly instead of shelling out via `terminal`. This avoids Japanese/newline/quote escaping issues and approval prompts entirely.

```python
import sys, json
from pathlib import Path
sys.path.insert(0, "/workspace/backup-secretary/skills/productivity/obsidian-diary-git/scripts")
from obsidian_diary import save_diary_entry, get_status

# save diary entry
result = save_diary_entry(
    vault=Path("/opt/data/obsidian/obsidian_git"),
    repo="https://github.com/ktakahiro150397/obsidian_git.git",
    branch="hermes",
    diary_dir="10_Diary",
    body="\u4eca\u65e5\u306fHermes\u306e\u65e5\u8a18\u4fdd\u5b58\u3092\u8a66\u3057\u305f\n\u6539\u884c\u3082\u3046\u307e\u304f\u3044\u3063\u305f",
    date=None,
    source="hermes-discord",
    tags=["diary", "hermes"],
    no_pull=False,
    no_push=False,
)
print(json.dumps(result, ensure_ascii=False))

# check status
status = get_status(
    vault=Path("/opt/data/obsidian/obsidian_git"),
    repo="https://github.com/ktakahiro150397/obsidian_git.git",
    branch="hermes",
)
print(json.dumps(status, ensure_ascii=False))
```

## File layout

Diary files are created here:

```text
10_Diary/YYYY/MM/YYYY-MM-DD.md
```

New files get Obsidian/Dataview-friendly frontmatter:

```yaml
---
type: diary
date: YYYY-MM-DD
weekday: Wednesday
created: YYYY-MM-DDTHH:mm:ss+09:00
updated: YYYY-MM-DDTHH:mm:ss+09:00
tags:
  - diary
people: []
topics: []
tasks: []
private: true
source: hermes-discord
---
```

Subsequent entries append a timestamped section:

```markdown
## HH:MM Hermes

<!-- source: hermes-discord / #tag -->

本文
```

## Git behavior

On `save`:

1. Ensure the vault repo exists; clone from `--repo` if missing.
2. Ensure the current branch is `hermes`.
3. `git fetch origin --prune`.
4. If `origin/hermes` exists, `git pull --rebase --autostash origin hermes`.
5. Create/append the diary Markdown file.
6. `git add <diary-file>`.
7. `git commit -m "diary: YYYY-MM-DD"`.
8. `git push -u origin hermes` unless `--no-push` is specified.

If pull/commit/push fails, do not auto-resolve conflicts. Report the failing command and repo path.

## Safety rules

- Never write to `main` for diary entries.
- Never store diary body in Hermes `MEMORY.md` / `USER.md`.
- Keep OAuth tokens, `.env`, `.obsidian/workspace*.json`, and plugin data out of committed diary changes.
- Prefer `--no-push --no-pull` for smoke tests.
- Use `hermes` branch until the format is proven stable.
- **Execution Policy:** This skill currently passes diary body through CLI arguments (`python3 scripts/obsidian_diary.py save "..."`), which violates the Skill Execution Policy for Japanese/newline/quote-heavy input. See `docs/skill-execution-policy.md` and Issue #30. Migration to a Hermes native tool is planned.

## Tests

From the repository root:

```bash
uv run --with pytest python -m pytest tests/test_obsidian_diary.py -q
```
