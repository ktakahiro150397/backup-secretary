---
name: obsidian
description: Read, search, and create notes in the Obsidian vault.
---

# Obsidian Vault

**Location:** Set via `OBSIDIAN_VAULT_PATH` environment variable (e.g. in `~/.hermes/.env`).

If unset, defaults to `~/Documents/Obsidian Vault`.

Note: Vault paths may contain spaces - always quote them.

## Read a note

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"
cat "$VAULT/Note Name.md"
```

## List notes

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"

# All notes
find "$VAULT" -name "*.md" -type f

# In a specific folder
ls "$VAULT/Subfolder/"
```

## Search

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"

# By filename
find "$VAULT" -name "*.md" -iname "*keyword*"

# By content
grep -rli "keyword" "$VAULT" --include="*.md"
```

## Create a note

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"
cat > "$VAULT/New Note.md" << 'ENDNOTE'
# Title

Content here.
ENDNOTE
```

## Append to a note

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"
echo "
New content here." >> "$VAULT/Existing Note.md"
```

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.

## Recurring diary capture with frontmatter

Use this pattern when the user wants recurring journal/diary prompts and later retrieval through Obsidian rather than Hermes standard memory. Standard memory is too small and globally injected for high-volume diary content; save only the durable preference/operation in memory, and store the actual diary entries as markdown files.

Recommended file layout:

```text
$OBSIDIAN_VAULT_PATH/10_Diary/YYYY/MM/YYYY-MM-DD.md
```

Recommended frontmatter:

```markdown
---
type: diary
date: YYYY-MM-DD
weekday: Monday
created: YYYY-MM-DDTHH:MM:SS+09:00
updated: YYYY-MM-DDTHH:MM:SS+09:00
mood:
energy:
sleep:
tags:
  - diary
people: []
topics: []
tasks: []
private: true
source: hermes-discord
---

# YYYY-MM-DD 日記

## 今日あったこと

-

## 感情・体調

-

## よかったこと

-

## しんどかったこと

-

## 明日に回すこと

-

## メモ

-
```

For chat capture, ask the user to start replies with `日記:` so entries are easy to detect and search. If the user already has an existing diary format, preserve that format and add only minimal frontmatter needed for Dataview/querying.

Useful Dataview index:

```dataview
TABLE date, mood, energy, sleep, topics
FROM "10_Diary"
WHERE type = "diary"
SORT date DESC
```

## Git-backed Obsidian diary vaults

If the user already has a Git-managed Obsidian diary repo, there are two sane deployment patterns:

1. **Persistent clone inside Hermes data** — best when `$HERMES_HOME` / `/opt/data` is already a durable bind mount. Clone the vault under something like `/opt/data/obsidian/<repo>` and let Hermes read/write via Git. This avoids adding another Docker mount and keeps the workflow portable inside the Hermes runtime.
2. **Host clone + bind mount** — useful when the user wants the same host checkout visible to Obsidian desktop, backup jobs, or other services.

Do not assume bind mount is required. In containerized Hermes setups where `/opt/data` persists, a Git clone under `/opt/data` is usually simpler.

For experimental assistant-written diaries, use a dedicated branch such as `hermes` and do not touch `main` until the format is proven stable:

```bash
cd "$OBSIDIAN_VAULT_PATH"
git fetch origin --prune
git checkout hermes 2>/dev/null || git checkout -b hermes origin/hermes 2>/dev/null || git checkout -b hermes
git pull --rebase --autostash origin hermes 2>/dev/null || true
# create/update diary markdown file
git add 10_Diary/
git commit -m "diary: YYYY-MM-DD"
git push -u origin hermes
```

If SSH auth fails in the container but `gh auth status` works, clone via `gh repo clone OWNER/REPO` or use the HTTPS remote that `gh` can authorize. Set repo-local `git config user.name` / `user.email` before committing if Git identity is missing.

Periodic `git pull --rebase --autostash` is fine, but periodic push is usually noisy and conflict-prone. Push immediately after successful diary writes. If `git pull`, `commit`, or `push` fails, do not auto-resolve ambiguous conflicts; notify the user with the repo path and failing command.

Recommended `.gitignore` for full Obsidian vault repos:

```gitignore
.obsidian/workspace*.json
.obsidian/cache/
.obsidian/plugins/*/data.json
.trash/
.DS_Store
```

If only a diary subdirectory is mounted or written, these Obsidian workspace files are usually irrelevant.
