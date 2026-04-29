---
name: codex
description: Delegate coding tasks to OpenAI Codex CLI agent. Use for building features, refactoring, PR reviews, and batch issue fixing. Requires the codex CLI and a git repository.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Coding-Agent, Codex, OpenAI, Code-Review, Refactoring]
    related_skills: [claude-code, hermes-agent]
---

# Codex CLI

Delegate coding tasks to [Codex](https://github.com/openai/codex) via the Hermes terminal. Codex is OpenAI's autonomous coding agent CLI.

## Prerequisites

- Codex installed: `npm install -g @openai/codex`
- OpenAI API key configured
- **Must run inside a git repository** — Codex refuses to run outside one
- Use `pty=true` in terminal calls — Codex is an interactive terminal app

## One-Shot Tasks

```
terminal(command="codex exec 'Add dark mode toggle to settings'", workdir="~/project", pty=true)
```

For scratch work (Codex needs a git repo):
```
terminal(command="cd $(mktemp -d) && git init && codex exec 'Build a snake game in Python'", pty=true)
```

## Background Mode (Long Tasks)

```
# Start in background with PTY
terminal(command="codex exec --full-auto 'Refactor the auth module'", workdir="~/project", background=true, pty=true)
# Returns session_id

# Monitor progress
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Send input if Codex asks a question
process(action="submit", session_id="<id>", data="yes")

# Kill if needed
process(action="kill", session_id="<id>")
```

## Key Flags

| Flag | Effect |
|------|--------|
| `exec "prompt"` | One-shot execution, exits when done |
| `--full-auto` | Sandboxed but auto-approves file changes in workspace |
| `--yolo` | No sandbox, no approvals (fastest, most dangerous) |

## PR Reviews

Clone to a temp directory for safe review:

```
terminal(command="REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && gh pr checkout 42 && codex review --base origin/main", pty=true)
```

## Parallel Issue Fixing with Worktrees

```
# Create worktrees
terminal(command="git worktree add -b fix/issue-78 /tmp/issue-78 main", workdir="~/project")
terminal(command="git worktree add -b fix/issue-99 /tmp/issue-99 main", workdir="~/project")

# Launch Codex in each
terminal(command="codex --yolo exec 'Fix issue #78: <description>. Commit when done.'", workdir="/tmp/issue-78", background=true, pty=true)
terminal(command="codex --yolo exec 'Fix issue #99: <description>. Commit when done.'", workdir="/tmp/issue-99", background=true, pty=true)

# Monitor
process(action="list")

# After completion, push and create PRs
terminal(command="cd /tmp/issue-78 && git push -u origin fix/issue-78")
terminal(command="gh pr create --repo user/repo --head fix/issue-78 --title 'fix: ...' --body '...'")

# Cleanup
terminal(command="git worktree remove /tmp/issue-78", workdir="~/project")
```

## Batch PR Reviews

```
# Fetch all PR refs
terminal(command="git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'", workdir="~/project")

# Review multiple PRs in parallel
terminal(command="codex exec 'Review PR #86. git diff origin/main...origin/pr/86'", workdir="~/project", background=true, pty=true)
terminal(command="codex exec 'Review PR #87. git diff origin/main...origin/pr/87'", workdir="~/project", background=true, pty=true)

# Post results
terminal(command="gh pr comment 86 --body '<review>'", workdir="~/project")
```

## Usage Limits / Quota Inspection

Use this when the user asks about Codex usage, remaining 5-hour/weekly quota, rate limits, or whether Codex exposes an API for limits.

Codex CLI has an internal account rate-limits flow even when there is no obvious `codex usage` command:

- App-server protocol method: `account/rateLimits/read`
- Backend endpoint for ChatGPT-authenticated Codex: `GET https://chatgpt.com/backend-api/wham/usage`
- Backend endpoint for Codex API style base URLs: `GET {base_url}/api/codex/usage`

Source landmarks in the OpenAI Codex repo:

- `codex-rs/app-server-protocol/src/protocol/common.rs` defines `GetAccountRateLimits => "account/rateLimits/read"`
- `codex-rs/app-server/src/codex_message_processor.rs` handles `get_account_rate_limits()` and calls `fetch_account_rate_limits()`
- `codex-rs/backend-client/src/client.rs` implements `get_rate_limits_many()` and selects `/wham/usage` or `/api/codex/usage`

Returned payload maps into `RateLimitSnapshot`:

- `primary` / `primary_window`: usually the 5-hour rolling window (`window_minutes: 300`)
- `secondary` / `secondary_window`: usually the weekly window (`window_minutes: 10080`)
- `used_percent`: consumed percentage; remaining is `100 - used_percent`
- `resets_at`: Unix timestamp when the window resets
- `plan_type`, `credits`, and `rate_limit_reached_type` may also be present

Auth requirements and pitfalls:

1. Check `codex login status` first. If it says `Not logged in`, Hermes cannot fetch account limits from that environment.
2. The usage endpoint requires the ChatGPT/Codex bearer token from Codex auth; never print or store the raw token in chat/logs.
3. Requests may also need `ChatGPT-Account-ID` for workspace/account routing.
4. If only API-key auth is configured, account-level ChatGPT/Codex usage limits may not be readable; Codex code explicitly expects auth that `uses_codex_backend()` for rate-limit reads.
5. Prefer using Codex's app-server/test-client plumbing if available; otherwise make a minimal redacted script that reads local Codex auth and calls the endpoint without exposing secrets.

Example shape, with secrets supplied out-of-band:

```bash
curl 'https://chatgpt.com/backend-api/wham/usage' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "ChatGPT-Account-ID: $ACCOUNT_ID" \
  -H "User-Agent: codex-cli"
```

## Rules

1. **Always use `pty=true`** — Codex is an interactive terminal app and hangs without a PTY
2. **Git repo required** — Codex won't run outside a git directory. Use `mktemp -d && git init` for scratch
3. **Use `exec` for one-shots** — `codex exec "prompt"` runs and exits cleanly
4. **`--full-auto` for building** — auto-approves changes within the sandbox
5. **Background for long tasks** — use `background=true` and monitor with `process` tool
6. **Don't interfere** — monitor with `poll`/`log`, be patient with long-running tasks
7. **Parallel is fine** — run multiple Codex processes at once for batch work
