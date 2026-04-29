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
python3 scripts/obsidian_diary.py save "今日はHermesの日記保存を試した" --source hermes-discord --tags diary,hermes
python3 scripts/obsidian_diary.py save "pushせずに検証" --no-push --no-pull
```

Explicit vault/repo/branch:

```bash
python3 scripts/obsidian_diary.py \
  --vault /opt/data/obsidian/obsidian_git \
  --repo https://github.com/ktakahiro150397/obsidian_git.git \
  --branch hermes \
  save "日記本文" --source hermes-discord --tags diary
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

## Tests

From the repository root:

```bash
uv run --with pytest python -m pytest tests/test_obsidian_diary.py -q
```
