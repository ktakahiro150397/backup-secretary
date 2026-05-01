# Repo-managed Hermes skills

This repository can manage custom Hermes skills and sync them into the Hermes runtime skills directory.

## Layout

```text
skills/
  productivity/
    write-and-forget-capture/
      SKILL.md
      scripts/
        waf.py
```

Runtime target:

```text
/opt/data/skills/
```

In the Docker Compose setup, `/opt/data` is backed by `runtime/hermes-data` on the host.

## Sync

Use the dedicated Compose profile:

```bash
docker compose --profile skills-sync run --rm --build skills-sync
```

This copies repo-managed skills from `/managed-skills/` into `/opt/data/skills/` with `rsync -a`.
It merges into the existing skills directory instead of replacing it.

## Why not bind mount over `/opt/data/skills`?

Do not mount `./skills` directly on `/opt/data/skills`.
That would hide the existing Hermes skills and any installed/generated skills.

The safe pattern is:

1. mount repo-managed skills read-only at `/managed-skills`
2. copy/merge into `/opt/data/skills`

## Safety

- Keep secrets out of skills.
- Keep runtime DBs out of Git.
- Track skill source and docs, not private user data.
- Run a secret scan before committing skill changes.

## Execution Policy

Custom skills in this repository follow the **Skill Execution Policy** in `docs/skill-execution-policy.md`:

> **Hermes native tools / MCP tools first; CLI only as last resort.**

When a skill needs to access an external service, prefer built-in Hermes tools or MCP servers. Avoid `terminal`-based shell wrappers that pass Japanese text, newlines, or quotes through CLI arguments, because Hermes' pre-exec security scanner flags them and stops execution with an approval prompt.

Read the full policy before authoring or refactoring repo-managed skills.
