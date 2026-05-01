---
name: write-and-forget-capture
description: Capture casual private notes into a local SQLite + FTS5 inbox instead of polluting long-term memory. Use when the user wants something remembered loosely, searched later, or collected before deciding whether to create Tasks/Calendar/GitHub/Obsidian entries.
version: 0.1.0
author: backup-secretary
license: MIT
metadata:
  hermes:
    tags: [capture, memory, personal-knowledge, sqlite, fts]
    related_skills: [personal-task-routing, google-workspace, obsidian]
---

# Write-And-Forget capture

## Purpose

Save messy user fragments into a retrievable local inbox without mixing them into Hermes' standard `MEMORY.md` / `USER.md`.

Use this for:

- “あとで見たい” style notes
- rough ideas that may become tasks/issues later
- private diary-ish fragments that should be searchable
- snippets that are too noisy for durable prompt-injected memory

Do **not** use this for:

- stable user preferences that should affect every future session → use memory
- procedural workflows learned from a complex task → create/update a skill
- immediate external side effects → ask/confirm, then use the relevant tool

## Storage

Default database:

```text
/opt/data/waf/waf.db
```

This DB is runtime/private data. Do not commit it.

The script is stored with this skill:

```text
scripts/waf.py
```

## Commands

From the skill directory:

```bash
python3 scripts/waf.py capture "HermesのメインLLM候補を比較する" --source discord --tags hermes,llm
python3 scripts/waf.py search "Hermes"
python3 scripts/waf.py search "Hermes" --include-closed
python3 scripts/waf.py status 1 closed
```

Use `--db` or `WAF_DB` for tests/smoke checks:

```bash
python3 scripts/waf.py --db /tmp/waf.db capture "あとで読む"
WAF_DB=/tmp/waf.db python3 scripts/waf.py search "あとで"
```

## Status model

`notes.status` values:

- `open`: unprocessed
- `suggested`: has an organization/action suggestion
- `actioned`: approved external action was completed
- `dismissed`: explicitly ignored
- `closed`: done/archived

Search returns only `open` and `suggested` by default. Use `--include-closed` to include `actioned`, `dismissed`, and `closed`.

## Output

All commands print compact JSON.

`capture`:

```json
{"status":"captured","note":{"id":1,"body":"...","source":"discord","status":"open","created_at":"...","updated_at":"...","tags":["hermes"]}}
```

`search`:

```json
{"status":"ok","results":[{"id":1,"body":"...","source":"discord","status":"open","created_at":"...","updated_at":"...","tags":["hermes"]}]}
```

## Safety rules

- Never write directly to Google Tasks, Calendar, GitHub, or Obsidian from this Phase 1 script.
- External writes must follow: propose → user approves → execute via the dedicated integration.
- Do not store OAuth codes, API keys, tokens, or authorization URLs in the WAF DB.
- Do not commit `/opt/data/waf/waf.db` or any exported private archive.
- Keep standard Hermes memory small and durable; use WAF for noisy/private fragments.
- **Execution Policy:** This skill currently passes capture body through CLI arguments (`python3 scripts/waf.py capture "..."`), which violates the Skill Execution Policy for Japanese/newline/quote-heavy input. See `docs/skill-execution-policy.md` and Issue #30. Migration to a Hermes native tool is planned.

## Implementation notes

- SQLite database with a `notes` table.
- FTS5 `notes_fts` virtual table uses `tokenize='trigram'` so mixed Japanese/English snippets are searchable.
- `suggestions` table exists as Phase 2 groundwork; Phase 1 does not execute actions.
- SQL uses parameterized queries.

## Tests

From the repository root:

```bash
uv run --with pytest python -m pytest tests/test_waf.py -q
```
