Hermes code repo: ktakahiro150397/backup-secretary; issue backlog at /opt/data/plans/hermes-issues-backlog.md; create issues only with approval.
§
Hermes and house-expense run in separate Docker containers on the same server.
§
Obsidian vault: ktakahiro150397/obsidian_git; clone at /opt/data/obsidian/obsidian_git; writes to main branch.
§
Discord channels: hermes-dev 1499234022725779619, diary 1499234070897365043, notify 1499234114694418674.
§
Web extraction fallback: Scrapling (`stealthy_fetch`/`fetch`) is used as a fallback when `web_extract` fails on JS-required or bot-protected sites (e.g. X, Cloudflare). Installed at `/opt/data/scrapling-venv` with `PLAYWRIGHT_BROWSERS_PATH=/opt/data/playwright-browsers`. Do NOT use for static lightweight pages due to browser startup overhead (~seconds, +hundreds MB RAM).
§
When user says "put in tasks" / "タスクに入れる", they mean Google Tasks. Not backlog.md, not Obsidian Tasks, not todo lists — always Google Tasks. Same correction was given before. Do not ask again.
§
Cron job testing workflow: temporarily redirect deliver to the current DM thread, run the job, verify output, then revert deliver to the original channel.
§
Hermes Agent image generation via Codex OAuth: add `image_gen.provider: openai-codex` to `config.yaml` to use GPT Image 2 without a FAL key. Model quality can be set via `image_gen.openai-codex.model` with values `gpt-image-2-low`, `gpt-image-2-medium` (default), or `gpt-image-2-high`. Generated images are saved to `$HERMES_HOME/cache/images/`.
§
Terminal commands require user approval in this environment. GitHub operations MUST use gh CLI or MCP server APIs exclusively. Never use curl/browser for GitHub releases or pages when gh/MCP alternative exists.
§
Environment: /tmp is noexec — venvs under /opt/data. uv at /usr/local/bin/uv. Python 3.13.5, PEP 668. pip/ensurepip/python3-venv/sudo absent. Docker client present, daemon not running.
§
Research vault: /opt/data/obsidian/obsidian_git/research-vault/. Japanese docs preferred; dislikes katakana loanword overload. delegation model: kimi-k2.6.