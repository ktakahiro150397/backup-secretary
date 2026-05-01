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
python3 scripts/waf.py capture "Hermes\u306e\u30e1\u30a4\u30f3LLM\u5019\u88dc\u3092\u6bd4\u8f03\u3059\u308b" --source discord --tags hermes,llm
python3 scripts/waf.py search "Hermes"
python3 scripts/waf.py search "Hermes" --include-closed
python3 scripts/waf.py status 1 closed
```

Use `--db` or `WAF_DB` for tests/smoke checks:

```bash
python3 scripts/waf.py --db /tmp/waf.db capture "\u3042\u3068\u3067\u8aad\u3080"
WAF_DB=/tmp/waf.db python3 scripts/waf.py search "\u3042\u3068\u3067"
```

## Preferred: execute_code direct import (avoids CLI escaping issues)

The recommended way to use this skill from Hermes is `execute_code`, importing the module directly instead of shelling out via `terminal`. This avoids Japanese/newline/quote escaping issues and approval prompts entirely.

```python
import sys, json
sys.path.insert(0, "/workspace/backup-secretary/skills/productivity/write-and-forget-capture/scripts")
from waf import connect, capture, search, update_status

with connect("/opt/data/waf/waf.db") as con:
    # capture
    result = capture(con, body="PS5 \u306e\u4fa1\u683c\u304c\u4e0b\u304c\u3063\u305f\u3089\u6559\u3048\u3066", source="discord", tags=["ps5", "\u4fa1\u683c"])
    print(json.dumps(result, ensure_ascii=False))

    # search
    result = search(con, query="PS5", include_closed=False, limit=20)
    print(json.dumps(result, ensure_ascii=False))

    # status update
    result = update_status(con, note_id=1, status="closed")
    print(json.dumps(result, ensure_ascii=False))
```

## Fallback: --stdin JSON (when execute_code is unavailable)

If you must invoke the script via `terminal` (e.g. from a non-Python context), use `--stdin` to pass a JSON payload instead of positional CLI arguments. This keeps the shell command short and avoids Japanese/newline/quote escaping:

```bash
python3 scripts/waf.py --stdin capture <<'JSON'
{"body":"PS5 \u306e\u4fa1\u683c\u304c\u4e0b\u304c\u3063\u305f\u3089\u6559\u3048\u3066","source":"discord","tags":"ps5,\u4fa1\u683c"}
JSON

python3 scripts/waf.py --stdin search <<'JSON'
{"query":"PS5","limit":20}
JSON

python3 scripts/waf.py --stdin status <<'JSON'
{"note_id":1,"status":"closed"}
JSON
```

**Do not pass Japanese text, newlines, or quotes as positional CLI arguments.** That pattern triggers Hermes command-approval scanners.

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
