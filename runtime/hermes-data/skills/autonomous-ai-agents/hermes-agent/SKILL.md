---
name: hermes-agent
description: Complete guide to using and extending Hermes Agent — CLI usage, setup, configuration, spawning additional agents, gateway platforms, skills, voice, tools, profiles, and a concise contributor reference. Load this skill when helping users configure Hermes, troubleshoot issues, spawn agent instances, or make code contributions.
version: 2.1.0
author: Hermes Agent + Teknium
license: MIT
metadata:
  hermes:
    tags: [hermes, setup, configuration, multi-agent, spawning, cli, gateway, development]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [claude-code, codex, opencode]
---

# Hermes Agent

Hermes Agent is an open-source AI agent framework by Nous Research that runs in your terminal, messaging platforms, and IDEs. It belongs to the same category as Claude Code (Anthropic), Codex (OpenAI), and OpenClaw — autonomous coding and task-execution agents that use tool calling to interact with your system. Hermes works with any LLM provider (OpenRouter, Anthropic, OpenAI, DeepSeek, local models, and 15+ others) and runs on Linux, macOS, and WSL.

What makes Hermes different:

- **Self-improving through skills** — Hermes learns from experience by saving reusable procedures as skills. When it solves a complex problem, discovers a workflow, or gets corrected, it can persist that knowledge as a skill document that loads into future sessions. Skills accumulate over time, making the agent better at your specific tasks and environment.
- **Persistent memory across sessions** — remembers who you are, your preferences, environment details, and lessons learned. Pluggable memory backends (built-in, Honcho, Mem0, and more) let you choose how memory works.
- **Multi-platform gateway** — the same agent runs on Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Email, and 10+ other platforms with full tool access, not just chat.
- **Provider-agnostic** — swap models and providers mid-workflow without changing anything else. Credential pools rotate across multiple API keys automatically.
- **Profiles** — run multiple independent Hermes instances with isolated configs, sessions, skills, and memory.
- **Extensible** — plugins, MCP servers, custom tools, webhook triggers, cron scheduling, and the full Python ecosystem.

People use Hermes for software development, research, system administration, data analysis, content creation, home automation, and anything else that benefits from an AI agent with persistent context and full system access.

**This skill helps you work with Hermes Agent effectively** — setting it up, configuring features, spawning additional agent instances, troubleshooting issues, finding the right commands and settings, and understanding how the system works when you need to extend or contribute to it.

**Docs:** https://hermes-agent.nousresearch.com/docs/

## Quick Start

```bash
# Install
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# Interactive chat (default)
hermes

# Single query
hermes chat -q "What is the capital of France?"

# Setup wizard
hermes setup

# Change model/provider
hermes model

# Check health
hermes doctor
```

---

## CLI Reference

### Global Flags

```
hermes [flags] [command]

  --version, -V             Show version
  --resume, -r SESSION      Resume session by ID or title
  --continue, -c [NAME]     Resume by name, or most recent session
  --worktree, -w            Isolated git worktree mode (parallel agents)
  --skills, -s SKILL        Preload skills (comma-separate or repeat)
  --profile, -p NAME        Use a named profile
  --yolo                    Skip dangerous command approval
  --pass-session-id         Include session ID in system prompt
```

No subcommand defaults to `chat`.

### Chat

```
hermes chat [flags]
  -q, --query TEXT          Single query, non-interactive
  -m, --model MODEL         Model (e.g. anthropic/claude-sonnet-4)
  -t, --toolsets LIST       Comma-separated toolsets
  --provider PROVIDER       Force provider (openrouter, anthropic, nous, etc.)
  -v, --verbose             Verbose output
  -Q, --quiet               Suppress banner, spinner, tool previews
  --checkpoints             Enable filesystem checkpoints (/rollback)
  --source TAG              Session source tag (default: cli)
```

### Configuration

```
hermes setup [section]      Interactive wizard (model|terminal|gateway|tools|agent)
hermes model                Interactive model/provider picker
hermes config               View current config
hermes config edit          Open config.yaml in $EDITOR
hermes config set KEY VAL   Set a config value
hermes config path          Print config.yaml path
hermes config env-path      Print .env path
hermes config check         Check for missing/outdated config
hermes config migrate       Update config with new options
hermes login [--provider P] OAuth login (nous, openai-codex)
hermes logout               Clear stored auth
hermes doctor [--fix]       Check dependencies and config
hermes status [--all]       Show component status
```

### Tools & Skills

```
hermes tools                Interactive tool enable/disable (curses UI)
hermes tools list           Show all tools and status
hermes tools enable NAME    Enable a toolset
hermes tools disable NAME   Disable a toolset

hermes skills list          List installed skills
hermes skills search QUERY  Search the skills hub
hermes skills install ID    Install a skill
hermes skills inspect ID    Preview without installing
hermes skills config        Enable/disable skills per platform
hermes skills check         Check for updates
hermes skills update        Update outdated skills
hermes skills uninstall N   Remove a hub skill
hermes skills publish PATH  Publish to registry
hermes skills browse        Browse all available skills
hermes skills tap add REPO  Add a GitHub repo as skill source
```

### MCP Servers

```
hermes mcp serve            Run Hermes as an MCP server
hermes mcp add NAME         Add an MCP server (--url or --command)
hermes mcp remove NAME      Remove an MCP server
hermes mcp list             List configured servers
hermes mcp test NAME        Test connection
hermes mcp configure NAME   Toggle tool selection
```

### Gateway (Messaging Platforms)

```
hermes gateway run          Start gateway foreground
hermes gateway install      Install as background service
hermes gateway start/stop   Control the service
hermes gateway restart      Restart the service
hermes gateway status       Check status
hermes gateway setup        Configure platforms
```

Supported platforms: Telegram, Discord, Slack, WhatsApp, Signal, Email, SMS, Matrix, Mattermost, Home Assistant, DingTalk, Feishu, WeCom, BlueBubbles (iMessage), Weixin (WeChat), API Server, Webhooks. Open WebUI connects via the API Server adapter.

Platform docs: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/

### Sessions

```
hermes sessions list        List recent sessions
hermes sessions browse      Interactive picker
hermes sessions export OUT  Export to JSONL
hermes sessions rename ID T Rename a session
hermes sessions delete ID   Delete a session
hermes sessions prune       Clean up old sessions (--older-than N days)
hermes sessions stats       Session store statistics
```

### Cron Jobs

```
hermes cron list            List jobs (--all for disabled)
hermes cron create SCHED    Create: '30m', 'every 2h', '0 9 * * *'
hermes cron edit ID         Edit schedule, prompt, delivery
hermes cron pause/resume ID Control job state
hermes cron run ID          Trigger on next tick
hermes cron remove ID       Delete a job
hermes cron status          Scheduler status
```

When creating scheduled agent reports with the `cronjob` tool:

- Make the prompt fully self-contained because future runs do not inherit the current chat context.
- Use `enabled_toolsets` narrowly, e.g. `['web']` for market/news reports, so scheduled runs are cheaper and less noisy.
- Schedules are UTC unless converted explicitly; convert user-facing local times before creating/updating the cron expression. Example: Japan time 09:00 = `0 0 * * *` UTC; Japan time 16:00 = `0 7 * * *` UTC.
- For report/verification loops, create the morning/source job first, then create the later evaluation job with `context_from: [morning_job_id]` so the latest completed source output is injected into the evaluation run.
- For forecasts that will be evaluated later, force the first job to produce checkable claims: direction, expected range, strong/weak categories, confidence, and explicit uncertainty. Force the evaluation job to compare prediction vs actual and score it rather than explain misses away.
- When pinning a scheduled job or delegation model to a cheaper provider/model for web-backed reports or tool-using subagents, remember the model does not browse the web by itself. Hermes exposes `web_search`/`web_extract` as tools; the model must support tool calling, then Hermes executes the tool and feeds results back. For OpenRouter, verify tool support against `https://openrouter.ai/api/v1/models` and check whether the model's `supported_parameters` includes `tools`/`tool_choice`. Do not trust model-family names alone; support differs by exact SKU and free/paid variant. As of the 2026-04 observed check, these Gemma OpenRouter IDs advertise `tools`: `google/gemma-4-31b-it`, `google/gemma-4-31b-it:free`, `google/gemma-4-26b-a4b-it`, `google/gemma-4-26b-a4b-it:free`, `google/gemma-3-27b-it`, and `google/gemma-3-12b-it`. The observed Gemma 3 4B / Gemma 3n 2B/4B / Gemma 2 27B entries did not advertise `tools`, and no Gemma 9B entry appeared in OpenRouter's model catalog at that time.

### Webhooks

```
hermes webhook subscribe N  Create route at /webhooks/<name>
hermes webhook list         List subscriptions
hermes webhook remove NAME  Remove a subscription
hermes webhook test NAME    Send a test POST
```

### Profiles

```
hermes profile list         List all profiles
hermes profile create NAME  Create (--clone, --clone-all, --clone-from)
hermes profile use NAME     Set sticky default
hermes profile delete NAME  Delete a profile
hermes profile show NAME    Show details
hermes profile alias NAME   Manage wrapper scripts
hermes profile rename A B   Rename a profile
hermes profile export NAME  Export to tar.gz
hermes profile import FILE  Import from archive
```

### Credential Pools

```
hermes auth add             Interactive credential wizard
hermes auth list [PROVIDER] List pooled credentials
hermes auth remove P INDEX  Remove by provider + index
hermes auth reset PROVIDER  Clear exhaustion status
```

### Other

```
hermes insights [--days N]  Usage analytics
hermes update               Update to latest version
hermes pairing list/approve/revoke  DM authorization
hermes plugins list/install/remove  Plugin management
hermes honcho setup/status  Honcho memory integration (requires honcho plugin)
hermes memory setup/status/off  Memory provider config
hermes completion bash|zsh  Shell completions
hermes acp                  ACP server (IDE integration)
```

### Evaluating External Hermes Plugins Before Install

Use this when the user finds a Hermes plugin/tool from X, GitHub, an article, or a demo and asks whether to install it. Treat it as an adoption decision, not just a docs summary.

Recommended investigation flow:

1. **Establish the real source** — find the canonical GitHub repo/docs/demo, license, release/tag status, recent commits, and whether the project is a hackathon/demo build or production-ready.
2. **Read primary files** — README, manifest (`plugin.yaml` or dashboard `manifest.json`), API/backend code, known limitations, roadmap, and install docs. Prefer raw GitHub URLs or a shallow temporary clone; do not rely only on social posts.
3. **Check capability surface** — identify whether it registers tools, hooks, slash commands, CLI commands, dashboard tabs, API routes, context engines, or memory providers. Plugins are powerful; "read-only" is a claim to verify.
4. **Static safety scan for observability/trace plugins** — list route methods and look for mutating operations (`POST`, `PUT`, `PATCH`, `DELETE`), file writes, subprocess calls, network clients (`requests`, `httpx`, `urllib`, `aiohttp`), env access, and direct reads of secret-prone paths.
5. **Redaction/privacy review** — check whether secrets are redacted before display/export, whether redaction fails open or closed, whether full tool args/results are exposed, and whether data leaves the local machine. Agent trace tools can leak prompts, OAuth redirects, API keys, tokens, and private file snippets.
6. **Docker/self-hosting fit** — install user plugins into the persistent Hermes home (`~/.hermes/plugins/<plugin>` or the profile-specific equivalent), not into ephemeral container source directories. Verify the container actually mounts that path.
7. **Enable deliberately** — Hermes plugins are generally discovered but disabled by default; use `hermes plugins list`, `hermes plugins enable <name>`, or `plugins.enabled` in config as appropriate. For dashboard plugins, also verify whether dashboard rescan/restart is required.
8. **PoC before production** — run first with dashboard bound to localhost/private network, then perform a smoke test with dummy secrets and representative sessions/tool calls. Only keep it enabled if sensitive values are not visible.
9. **Rollback path** — document `hermes plugins disable <name>`, removing `~/.hermes/plugins/<name>`, and dashboard/container restart.
10. **Record the decision trail** — if tracking in GitHub, comment on the issue with source URLs, security findings, install/rollback steps, and a clear recommendation: install, PoC only, defer, or reject.

Rule of thumb: for observability, browser/session recording, tracing, and dashboard plugins, default to **PoC-only until secret redaction and dashboard access control are verified**. A nice trace UI is not worth turning your agent history into a token piñata.

```

---

## Slash Commands (In-Session)

Type these during an interactive chat session.

### Session Control
```
/new (/reset)        Fresh session
/clear               Clear screen + new session (CLI)
/retry               Resend last message
/undo                Remove last exchange
/title [name]        Name the session
/compress            Manually compress context
/stop                Kill background processes
/rollback [N]        Restore filesystem checkpoint
/background <prompt> Run prompt in background
/queue <prompt>      Queue for next turn
/resume [name]       Resume a named session
```

### Configuration
```
/config              Show config (CLI)
/model [name]        Show or change model
/personality [name]  Set personality
/reasoning [level]   Set reasoning (none|minimal|low|medium|high|xhigh|show|hide)
/verbose             Cycle: off → new → all → verbose
/voice [on|off|tts]  Voice mode
/yolo                Toggle approval bypass
/skin [name]         Change theme (CLI)
/statusbar           Toggle status bar (CLI)
```

### Tools & Skills
```
/tools               Manage tools (CLI)
/toolsets            List toolsets (CLI)
/skills              Search/install skills (CLI)
/skill <name>        Load a skill into session
/cron                Manage cron jobs (CLI)
/reload-mcp          Reload MCP servers
/plugins             List plugins (CLI)
```

### Gateway
```
/approve             Approve a pending command (gateway)
/deny                Deny a pending command (gateway)
/restart             Restart gateway (gateway)
/sethome             Set current chat as home channel (gateway)
/update              Update Hermes to latest (gateway)
/platforms (/gateway) Show platform connection status (gateway)
```

### Utility
```
/branch (/fork)      Branch the current session
/btw                 Ephemeral side question (doesn't interrupt main task)
/fast                Toggle priority/fast processing
/browser             Open CDP browser connection
/history             Show conversation history (CLI)
/save                Save conversation to file (CLI)
/paste               Attach clipboard image (CLI)
/image               Attach local image file (CLI)
```

### Info
```
/help                Show commands
/commands [page]     Browse all commands (gateway)
/usage               Token usage
/insights [days]     Usage analytics
/status              Session info (gateway)
/profile             Active profile info
```

### Exit
```
/quit (/exit, /q)    Exit CLI
```

---

## Key Paths & Config

```
~/.hermes/config.yaml       Main configuration
~/.hermes/.env              API keys and secrets
$HERMES_HOME/skills/        Installed skills
~/.hermes/sessions/         Session transcripts
~/.hermes/logs/             Gateway and error logs
~/.hermes/auth.json         OAuth tokens and credential pools
~/.hermes/hermes-agent/     Source code (if git-installed)
```

Profiles use `~/.hermes/profiles/<name>/` with the same layout.

### Backup-Safe Git Tracking for Hermes State

Use this when helping users back up or migrate a self-hosted/containerized Hermes install, especially when `$HERMES_HOME` is bind-mounted into a project repo. Do **not** commit the whole Hermes home directory. It contains secrets, auth tokens, session logs, SQLite state, caches, locks, and platform artifacts.

Recommended whitelist-first approach for a repo-managed runtime directory such as `runtime/hermes-data`:

```gitignore
# Ignore runtime by default
runtime/*

# Allow whitelist traversal
!runtime/
!runtime/hermes-data/

# Track portable Hermes config/state only
!runtime/hermes-data/config.yaml
!runtime/hermes-data/SOUL.md
!runtime/hermes-data/memories/
!runtime/hermes-data/memories/USER.md
!runtime/hermes-data/memories/MEMORY.md
!runtime/hermes-data/cron/
!runtime/hermes-data/cron/jobs.json
!runtime/hermes-data/skills/
!runtime/hermes-data/skills/**/*.md

# Optional user-managed customization
!runtime/hermes-data/hooks/
!runtime/hermes-data/hooks/**
!runtime/hermes-data/skins/
!runtime/hermes-data/skins/**
!runtime/hermes-data/plans/
!runtime/hermes-data/plans/**/*.md
!runtime/hermes-data/platforms/
!runtime/hermes-data/platforms/**/*.yaml

# Never track secrets/runtime noise
runtime/hermes-data/.env
runtime/hermes-data/auth.json
runtime/hermes-data/auth.lock
runtime/hermes-data/state.db*
runtime/hermes-data/sessions/**
runtime/hermes-data/logs/**
runtime/hermes-data/cache/**
runtime/hermes-data/home/**
runtime/hermes-data/.local/**
runtime/hermes-data/cron/output/**
runtime/hermes-data/*.pid
runtime/hermes-data/*.lock
runtime/hermes-data/gateway_state.json
runtime/hermes-data/channel_directory.json
```

Guidelines:
- Track `config.yaml`, `SOUL.md`, `memories/*.md`, `cron/jobs.json`, and custom `skills/**/*.md` when they are text-reviewed and free of secrets.
- Do not track `.env`, `auth.json`, `state.db*`, `sessions/**`, `logs/**`, `cache/**`, `home/**`, `.local/**`, cron outputs, pid/lock files, or imported private archives.
- Treat `sessions/**` as sensitive even though it is useful for recovery; transcripts can include secrets, attachments, and private context.
- Run `git status --ignored` and a secret scan before committing. At minimum check for patterns like `DATABASE_URL=`, `DISCORD_TOKEN`, `OPENROUTER_API_KEY`, `GH_TOKEN`, `github_pat_`, `sk-`, and `Bearer `.
- If bundled skills make `skills/**/*.md` too noisy, move user-authored skills into a dedicated subtree and whitelist only that subtree.

### Automated Cron-Based Backup

Once the whitelist gitignore is in place, automate syncing from `$HERMES_HOME` to the repo with a shell script + cron job. Key design decisions:

- **Only sync on `main` branch** — prevents accidental commits from feature/experiment branches. Script exits early if `git rev-parse --abbrev-ref HEAD` != `main`.
- **Pull before sync** — `git pull --ff-only` to avoid conflicts; abort if pull fails.
- **Copy, don't move** — `cp` whitelisted files from `$HERMES_HOME` to the repo's `runtime/hermes-data/`, then `git add` only the whitelisted paths.
- **Conditional commit** — use `git diff --cached --quiet` to skip when nothing changed, avoiding empty commits.

**Script template** (`scripts/auto-backup-hermes-state.sh`):

```bash
#!/bin/bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/workspace/backup-secretary}"
DATA_DIR="${DATA_DIR:-/opt/data}"
RUNTIME_DIR="$REPO_DIR/runtime/hermes-data"

cd "$REPO_DIR"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "main" ]; then
    echo "[$(date -Iseconds)] Not on main (current: $BRANCH). Skipping."
    exit 0
fi

git pull origin main --ff-only 2>&1 || {
    echo "[$(date -Iseconds)] git pull failed, aborting."
    exit 1
}

mkdir -p "$RUNTIME_DIR/memories" "$RUNTIME_DIR/cron" "$RUNTIME_DIR/plans"

cp "$DATA_DIR/config.yaml"          "$RUNTIME_DIR/config.yaml"
cp "$DATA_DIR/SOUL.md"              "$RUNTIME_DIR/SOUL.md"
cp "$DATA_DIR/memories/USER.md"     "$RUNTIME_DIR/memories/USER.md"
cp "$DATA_DIR/memories/MEMORY.md"   "$RUNTIME_DIR/memories/MEMORY.md"
cp "$DATA_DIR/cron/jobs.json"       "$RUNTIME_DIR/cron/jobs.json"
cp "$DATA_DIR/plans/"*.md           "$RUNTIME_DIR/plans/" 2>/dev/null || true

git add \
    runtime/hermes-data/config.yaml \
    runtime/hermes-data/SOUL.md \
    runtime/hermes-data/memories/USER.md \
    runtime/hermes-data/memories/MEMORY.md \
    runtime/hermes-data/cron/jobs.json \
    runtime/hermes-data/plans/

if git diff --cached --quiet; then
    echo "[$(date -Iseconds)] No changes."
    exit 0
fi

git commit -m "chore: auto-backup Hermes state [$(date -u +'%Y-%m-%d %H:%M UTC')]"
git push origin main
echo "[$(date -Iseconds)] Backup committed and pushed."
```

**Cron job setup** — create with the `cronjob` tool, using minimal toolsets:

```
cronjob create
  name: hermes-state-backup
  schedule: "0 */6 * * *"  (every 6 hours)
  prompt: "bash /workspace/backup-secretary/scripts/auto-backup-hermes-state.sh を実行し、結果を報告してください。"
  enabled_toolsets: ["terminal"]
  deliver: origin
```

Pitfalls:
- The cron job runs in a fresh session with no prior context — the prompt must be fully self-contained. Delegating the actual logic to a script file is preferred over embedding it in the prompt.
- `enabled_toolsets` should be minimal (`['terminal']` is sufficient) to keep runs cheap.
- The script's branch guard only protects against accidental branch-state commits; it does not prevent the cron job from running — it just makes it a no-op on non-main branches.
- If the container bind-mounts `$HERMES_HOME` from the host's `./runtime/hermes-data`, the `cp` direction must go from the live mount (`/opt/data`) into the repo workspace, not the other way around.
- Cron jobs may not persist across gateway restarts depending on the Hermes version; verify with `cronjob(action='list')` after creation and re-create if missing.

### Repo-Managed Custom Skills in Containers

Once the whitelist gitignore is in place, automate syncing from `$HERMES_HOME` to the repo with a shell script + cron job. The key design decisions:

- **Only sync on `main` branch** — prevents accidental commits from feature/experiment branches. Script exits early if `git rev-parse --abbrev-ref HEAD` != `main`.
- **Pull before sync** — `git pull --ff-only` to avoid conflicts; abort if pull fails.
- **Copy, don't move** — `cp` whitelisted files from `$HERMES_HOME` to the repo's `runtime/hermes-data/`, then `git add` only the whitelisted paths.
- **Conditional commit** — use `git diff --cached --quiet` to skip when nothing changed, avoiding empty commits.

**Script template** (`scripts/auto-backup-hermes-state.sh`):

```bash
#!/bin/bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/workspace/backup-secretary}"
DATA_DIR="${DATA_DIR:-/opt/data}"
RUNTIME_DIR="$REPO_DIR/runtime/hermes-data"

cd "$REPO_DIR"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "main" ]; then
    echo "[$(date -Iseconds)] Not on main (current: $BRANCH). Skipping."
    exit 0
fi

git pull origin main --ff-only 2>&1 || {
    echo "[$(date -Iseconds)] git pull failed, aborting."
    exit 1
}

mkdir -p "$RUNTIME_DIR/memories" "$RUNTIME_DIR/cron" "$RUNTIME_DIR/plans"

cp "$DATA_DIR/config.yaml"          "$RUNTIME_DIR/config.yaml"
cp "$DATA_DIR/SOUL.md"              "$RUNTIME_DIR/SOUL.md"
cp "$DATA_DIR/memories/USER.md"     "$RUNTIME_DIR/memories/USER.md"
cp "$DATA_DIR/memories/MEMORY.md"   "$RUNTIME_DIR/memories/MEMORY.md"
cp "$DATA_DIR/cron/jobs.json"       "$RUNTIME_DIR/cron/jobs.json"
cp "$DATA_DIR/plans/"*.md           "$RUNTIME_DIR/plans/" 2>/dev/null || true

git add \
    runtime/hermes-data/config.yaml \
    runtime/hermes-data/SOUL.md \
    runtime/hermes-data/memories/USER.md \
    runtime/hermes-data/memories/MEMORY.md \
    runtime/hermes-data/cron/jobs.json \
    runtime/hermes-data/plans/

if git diff --cached --quiet; then
    echo "[$(date -Iseconds)] No changes."
    exit 0
fi

git commit -m "chore: auto-backup Hermes state [$(date -u +'%Y-%m-%d %H:%M UTC')]"
git push origin main
echo "[$(date -Iseconds)] Backup committed and pushed."
```

**Cron job setup:**

```bash
cronjob create \
  --name hermes-state-backup \
  --schedule "0 */6 * * *" \
  --prompt "bash /workspace/backup-secretary/scripts/auto-backup-hermes-state.sh を実行し、結果を報告してください。" \
  --enabled-toolsets '["terminal"]' \
  --deliver origin
```

Pitfalls:
- The cron job runs in a fresh session with no prior context — the prompt must be fully self-contained. Delegating the actual logic to a script file is preferred over embedding it in the prompt.
- `enabled_toolsets` should be minimal (`['terminal']` is sufficient) to keep runs cheap.
- The script's branch guard only protects against accidental branch-state commits; it does not prevent the cron job from running — it just makes it a no-op on non-main branches.
- If the container bind-mounts `$HERMES_HOME` from the host's `./runtime/hermes-data`, the `cp` direction must go from the live mount (`/opt/data`) into the repo workspace, not the other way around.

### Repo-Managed Custom Skills in Containers

Use this when a user wants custom Hermes skills/scripts managed in a project repo while keeping the runtime `$HERMES_HOME/skills` directory intact.

Recommended pattern:

```text
repo/
  skills/
    productivity/
      my-skill/
        SKILL.md
        scripts/tool.py
```

Mount repo-managed skills read-only at a separate path, then merge-copy into `$HERMES_HOME/skills`:

```yaml
volumes:
  - type: bind
    source: ./skills
    target: /managed-skills
    read_only: true
```

```bash
mkdir -p /opt/data/skills
rsync -a /managed-skills/ /opt/data/skills/
```

For Docker Compose, prefer a one-shot `skills-sync` profile/service or a wrapper script (`scripts/sync-skills.sh`) that runs the sync. Install `rsync` in the image if it is not present.

Do **not** bind mount `./skills` directly over `/opt/data/skills`; that hides existing installed/generated skills and can break the runtime. Merge, don't replace. Keep runtime DBs, private archives, OAuth tokens, and generated state out of the repo.

### Config Sections

Edit with `hermes config edit` or `hermes config set section.key value`.

| Section | Key options |
|---------|-------------|
| `model` | `default`, `provider`, `base_url`, `api_key`, `context_length` |
| `agent` | `max_turns` (90), `tool_use_enforcement` |
| `terminal` | `backend` (local/docker/ssh/modal), `cwd`, `timeout` (180) |
| `compression` | `enabled`, `threshold` (0.50), `target_ratio` (0.20) |
| `display` | `skin`, `tool_progress`, `show_reasoning`, `show_cost` |
| `stt` | `enabled`, `provider` (local/groq/openai/mistral) |
| `tts` | `provider` (edge/elevenlabs/openai/minimax/mistral/neutts) |
| `memory` | `memory_enabled`, `user_profile_enabled`, `provider` |
| `security` | `tirith_enabled`, `website_blocklist` |
| `delegation` | `model`, `provider`, `base_url`, `api_key`, `max_iterations` (50), `reasoning_effort` |
| `checkpoints` | `enabled`, `max_snapshots` (50) |

Full config reference: https://hermes-agent.nousresearch.com/docs/user-guide/configuration

### Providers

20+ providers supported. Set via `hermes model` or `hermes setup`.

| Provider | Auth | Key env var |
|----------|------|-------------|
| OpenRouter | API key | `OPENROUTER_API_KEY` |
| Anthropic | API key | `ANTHROPIC_API_KEY` |
| Nous Portal | OAuth | `hermes auth` |
| OpenAI Codex | OAuth | `hermes auth` |
| GitHub Copilot | Token | `COPILOT_GITHUB_TOKEN` |
| Google Gemini | API key | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| DeepSeek | API key | `DEEPSEEK_API_KEY` |
| xAI / Grok | API key | `XAI_API_KEY` |
| Hugging Face | Token | `HF_TOKEN` |
| Z.AI / GLM | API key | `GLM_API_KEY` |
| MiniMax | API key | `MINIMAX_API_KEY` |
| MiniMax CN | API key | `MINIMAX_CN_API_KEY` |
| Kimi / Moonshot | API key | `KIMI_API_KEY` |
| Alibaba / DashScope | API key | `DASHSCOPE_API_KEY` |
| Xiaomi MiMo | API key | `XIAOMI_API_KEY` |
| Kilo Code | API key | `KILOCODE_API_KEY` |
| AI Gateway (Vercel) | API key | `AI_GATEWAY_API_KEY` |
| OpenCode Zen | API key | `OPENCODE_ZEN_API_KEY` |
| OpenCode Go | API key | `OPENCODE_GO_API_KEY` |
| Qwen OAuth | OAuth | `hermes login --provider qwen-oauth` |
| Custom endpoint | Config | `model.base_url` + `model.api_key` in config.yaml |
| GitHub Copilot ACP | External | `COPILOT_CLI_PATH` or Copilot CLI |

Full provider docs: https://hermes-agent.nousresearch.com/docs/integrations/providers

### Toolsets

Enable/disable via `hermes tools` (interactive) or `hermes tools enable/disable NAME`.

| Toolset | What it provides |
|---------|-----------------|
| `web` | Web search and content extraction |
| `browser` | Browser automation (Browserbase, Camofox, or local Chromium) |
| `terminal` | Shell commands and process management |
| `file` | File read/write/search/patch |
| `code_execution` | Sandboxed Python execution |
| `vision` | Image analysis |
| `image_gen` | AI image generation |
| `tts` | Text-to-speech |
| `skills` | Skill browsing and management |
| `memory` | Persistent cross-session memory |
| `session_search` | Search past conversations |
| `delegation` | Subagent task delegation |
| `cronjob` | Scheduled task management |
| `clarify` | Ask user clarifying questions |
| `messaging` | Cross-platform message sending |
| `search` | Web search only (subset of `web`) |
| `todo` | In-session task planning and tracking |
| `rl` | Reinforcement learning tools (off by default) |
| `moa` | Mixture of Agents (off by default) |
| `homeassistant` | Smart home control (off by default) |

Tool changes take effect on `/reset` (new session). They do NOT apply mid-conversation to preserve prompt caching.

---

## Voice & Transcription

### STT (Voice → Text)

Voice messages from messaging platforms are auto-transcribed.

Provider priority (auto-detected):
1. **Local faster-whisper** — free, no API key: `pip install faster-whisper`
2. **Groq Whisper** — free tier: set `GROQ_API_KEY`
3. **OpenAI Whisper** — paid: set `VOICE_TOOLS_OPENAI_KEY`
4. **Mistral Voxtral** — set `MISTRAL_API_KEY`

Config:
```yaml
stt:
  enabled: true
  provider: local        # local, groq, openai, mistral
  local:
    model: base          # tiny, base, small, medium, large-v3
```

### TTS (Text → Voice)

| Provider | Env var | Free? |
|----------|---------|-------|
| Edge TTS | None | Yes (default) |
| ElevenLabs | `ELEVENLABS_API_KEY` | Free tier |
| OpenAI | `VOICE_TOOLS_OPENAI_KEY` | Paid |
| MiniMax | `MINIMAX_API_KEY` | Paid |
| Mistral (Voxtral) | `MISTRAL_API_KEY` | Paid |
| NeuTTS (local) | None (`pip install neutts[all]` + `espeak-ng`) | Free |

Voice commands: `/voice on` (voice-to-voice), `/voice tts` (always voice), `/voice off`.

---

## Spawning Additional Hermes Instances

Run additional Hermes processes as fully independent subprocesses — separate sessions, tools, and environments.

### When to Use This vs delegate_task

| | `delegate_task` | Spawning `hermes` process |
|-|-----------------|--------------------------|
| Isolation | Separate conversation, shared process | Fully independent process |
| Duration | Minutes (bounded by parent loop) | Hours/days |
| Tool access | Subset of parent's tools | Full tool access |
| Interactive | No | Yes (PTY mode) |
| Use case | Quick parallel subtasks | Long autonomous missions |

### One-Shot Mode

```
terminal(command="hermes chat -q 'Research GRPO papers and write summary to ~/research/grpo.md'", timeout=300)

# Background for long tasks:
terminal(command="hermes chat -q 'Set up CI/CD for ~/myapp'", background=true)
```

### Interactive PTY Mode (via tmux)

Hermes uses prompt_toolkit, which requires a real terminal. Use tmux for interactive spawning:

```
# Start
terminal(command="tmux new-session -d -s agent1 -x 120 -y 40 'hermes'", timeout=10)

# Wait for startup, then send a message
terminal(command="sleep 8 && tmux send-keys -t agent1 'Build a FastAPI auth service' Enter", timeout=15)

# Read output
terminal(command="sleep 20 && tmux capture-pane -t agent1 -p", timeout=5)

# Send follow-up
terminal(command="tmux send-keys -t agent1 'Add rate limiting middleware' Enter", timeout=5)

# Exit
terminal(command="tmux send-keys -t agent1 '/exit' Enter && sleep 2 && tmux kill-session -t agent1", timeout=10)
```

### Multi-Agent Coordination

```
# Agent A: backend
terminal(command="tmux new-session -d -s backend -x 120 -y 40 'hermes -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t backend 'Build REST API for user management' Enter", timeout=15)

# Agent B: frontend
terminal(command="tmux new-session -d -s frontend -x 120 -y 40 'hermes -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t frontend 'Build React dashboard for user management' Enter", timeout=15)

# Check progress, relay context between them
terminal(command="tmux capture-pane -t backend -p | tail -30", timeout=5)
terminal(command="tmux send-keys -t frontend 'Here is the API schema from the backend agent: ...' Enter", timeout=5)
```

### Session Resume

```
# Resume most recent session
terminal(command="tmux new-session -d -s resumed 'hermes --continue'", timeout=10)

# Resume specific session
terminal(command="tmux new-session -d -s resumed 'hermes --resume 20260225_143052_a1b2c3'", timeout=10)
```

### Tips

- **Prefer `delegate_task` for quick subtasks** — less overhead than spawning a full process
- **Use `-w` (worktree mode)** when spawning agents that edit code — prevents git conflicts
- **Set timeouts** for one-shot mode — complex tasks can take 5-10 minutes
- **Use `hermes chat -q` for fire-and-forget** — no PTY needed
- **Use tmux for interactive sessions** — raw PTY mode has `\r` vs `\n` issues with prompt_toolkit
- **For scheduled tasks**, use the `cronjob` tool instead of spawning — handles delivery and retry

---

## Troubleshooting

### Voice not working
1. Check `stt.enabled: true` in config.yaml
2. Verify provider: `pip install faster-whisper` or set API key
3. In gateway: `/restart`. In CLI: exit and relaunch.

### Tool not available
1. `hermes tools` — check if toolset is enabled for your platform
2. Some tools need env vars (check `.env`)
3. `/reset` after enabling tools

### Model/provider issues
1. `hermes doctor` — check config and dependencies
2. `hermes login` — re-authenticate OAuth providers
3. Check `.env` has the right API key
4. **Copilot 403**: `gh auth login` tokens do NOT work for Copilot API. You must use the Copilot-specific OAuth device code flow via `hermes model` → GitHub Copilot.

### Changes not taking effect
- **Tools/skills:** `/reset` starts a new session with updated toolset
- **Config changes:** In gateway: `/restart`. In CLI: exit and relaunch.
- **Code changes:** Restart the CLI or gateway process

### Skills not showing
1. `hermes skills list` — verify installed
2. `hermes skills config` — check platform enablement
3. Load explicitly: `/skill name` or `hermes -s name`

### Gateway issues
Check logs first:
```bash
grep -i "failed to send\|error" ~/.hermes/logs/gateway.log | tail -20
```

Common gateway problems:
- **Gateway dies on SSH logout**: Enable linger: `sudo loginctl enable-linger $USER`
- **Gateway dies on WSL2 close**: WSL2 requires `systemd=true` in `/etc/wsl.conf` for systemd services to work. Without it, gateway falls back to `nohup` (dies when session closes).
- **Gateway crash loop**: Reset the failed state: `systemctl --user reset-failed hermes-gateway`

### Platform-specific issues
- **Discord bot silent**: Must enable **Message Content Intent** in Bot → Privileged Gateway Intents.
- **Discord attachments not visible to tools**: A file may appear attached in Discord but not be saved into the agent workspace. Before assuming receipt, search likely locations (`/opt/data`, `/tmp`, current cwd) for the expected extension/name and inspect recent session JSON/logs for attachment URLs. If no file is present, ask the user for a smaller sample pasted in a code block, a direct download URL, or a local preprocessing script/output instead of repeatedly requesting attachments.
- **Slack bot only works in DMs**: Must subscribe to `message.channels` event. Without it, the bot ignores public channels.
- **Windows HTTP 400 "No models provided"**: Config file encoding issue (BOM). Ensure `config.yaml` is saved as UTF-8 without BOM.

### Auxiliary models not working
If `auxiliary` tasks (vision, compression, session_search) fail silently, the `auto` provider can't find a backend. Either set `OPENROUTER_API_KEY` or `GOOGLE_API_KEY`, or explicitly configure each auxiliary task's provider:
```bash
hermes config set auxiliary.vision.provider <your_provider>
hermes config set auxiliary.vision.model <model_name>
```

---

## Where to Find Things

| Looking for... | Location |
|----------------|----------|
| Config options | `hermes config edit` or [Configuration docs](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) |
| Available tools | `hermes tools list` or [Tools reference](https://hermes-agent.nousresearch.com/docs/reference/tools-reference) |
| Slash commands | `/help` in session or [Slash commands reference](https://hermes-agent.nousresearch.com/docs/reference/slash-commands) |
| Skills catalog | `hermes skills browse` or [Skills catalog](https://hermes-agent.nousresearch.com/docs/reference/skills-catalog) |
| Provider setup | `hermes model` or [Providers guide](https://hermes-agent.nousresearch.com/docs/integrations/providers) |
| Platform setup | `hermes gateway setup` or [Messaging docs](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/) |
| MCP servers | `hermes mcp list` or [MCP guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) |
| Profiles | `hermes profile list` or [Profiles docs](https://hermes-agent.nousresearch.com/docs/user-guide/profiles) |
| Cron jobs | `hermes cron list` or [Cron docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) |
| Memory | `hermes memory status` or [Memory docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) |
| Env variables | `hermes config env-path` or [Env vars reference](https://hermes-agent.nousresearch.com/docs/reference/environment-variables) |
| CLI commands | `hermes --help` or [CLI reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands) |
| Gateway logs | `~/.hermes/logs/gateway.log` |
| Session files | `~/.hermes/sessions/` or `hermes sessions browse` |
| Source code | `~/.hermes/hermes-agent/` |

---

## Contributor Quick Reference

For occasional contributors and PR authors. Full developer docs: https://hermes-agent.nousresearch.com/docs/developer-guide/

### Project Layout

```
hermes-agent/
├── run_agent.py          # AIAgent — core conversation loop
├── model_tools.py        # Tool discovery and dispatch
├── toolsets.py           # Toolset definitions
├── cli.py                # Interactive CLI (HermesCLI)
├── hermes_state.py       # SQLite session store
├── agent/                # Prompt builder, context compression, memory, model routing, credential pooling, skill dispatch
├── hermes_cli/           # CLI subcommands, config, setup, commands
│   ├── commands.py       # Slash command registry (CommandDef)
│   ├── config.py         # DEFAULT_CONFIG, env var definitions
│   └── main.py           # CLI entry point and argparse
├── tools/                # One file per tool
│   └── registry.py       # Central tool registry
├── gateway/              # Messaging gateway
│   └── platforms/        # Platform adapters (telegram, discord, etc.)
├── cron/                 # Job scheduler
├── tests/                # ~3000 pytest tests
└── website/              # Docusaurus docs site
```

Config: `~/.hermes/config.yaml` (settings), `~/.hermes/.env` (API keys).

### Adding a Tool (3 files)

**1. Create `tools/your_tool.py`:**
```python
import json, os
from tools.registry import registry

def check_requirements() -> bool:
    return bool(os.getenv("EXAMPLE_API_KEY"))

def example_tool(param: str, task_id: str = None) -> str:
    return json.dumps({"success": True, "data": "..."})

registry.register(
    name="example_tool",
    toolset="example",
    schema={"name": "example_tool", "description": "...", "parameters": {...}},
    handler=lambda args, **kw: example_tool(
        param=args.get("param", ""), task_id=kw.get("task_id")),
    check_fn=check_requirements,
    requires_env=["EXAMPLE_API_KEY"],
)
```

**2. Add to `toolsets.py`** → `_HERMES_CORE_TOOLS` list.

Auto-discovery: any `tools/*.py` file with a top-level `registry.register()` call is imported automatically — no manual list needed.

All handlers must return JSON strings. Use `get_hermes_home()` for paths, never hardcode `~/.hermes`.

### Adding a Slash Command

1. Add `CommandDef` to `COMMAND_REGISTRY` in `hermes_cli/commands.py`
2. Add handler in `cli.py` → `process_command()`
3. (Optional) Add gateway handler in `gateway/run.py`

All consumers (help text, autocomplete, Telegram menu, Slack mapping) derive from the central registry automatically.

### Agent Loop (High Level)

```
run_conversation():
  1. Build system prompt
  2. Loop while iterations < max:
     a. Call LLM (OpenAI-format messages + tool schemas)
     b. If tool_calls → dispatch each via handle_function_call() → append results → continue
     c. If text response → return
  3. Context compression triggers automatically near token limit
```

### Testing

```bash
python -m pytest tests/ -o 'addopts=' -q   # Full suite
python -m pytest tests/tools/ -q            # Specific area
```

- Tests auto-redirect `HERMES_HOME` to temp dirs — never touch real `~/.hermes/`
- Run full suite before pushing any change
- Use `-o 'addopts='` to clear any baked-in pytest flags

### Commit Conventions

```
type: concise subject line

Optional body.
```

Types: `fix:`, `feat:`, `refactor:`, `docs:`, `chore:`

### Key Rules

- **Never break prompt caching** — don't change context, tools, or system prompt mid-conversation
- **Message role alternation** — never two assistant or two user messages in a row
- Use `get_hermes_home()` from `hermes_constants` for all paths (profile-safe)
- Config values go in `config.yaml`, secrets go in `.env`
- New tools need a `check_fn` so they only appear when requirements are met
