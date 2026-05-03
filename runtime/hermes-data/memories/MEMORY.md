File transfer: WSL→server via scp (yanelmoserver).
§
Hermes code repo: ktakahiro150397/backup-secretary.
§
Hermes and house-expense run in separate Docker containers on the same server.
§
Issue backlog: /opt/data/plans/hermes-issues-backlog.md; create issues only with approval.
§
Obsidian vault: ktakahiro150397/obsidian_git; clone at /opt/data/obsidian/obsidian_git; writes to main branch.
§
Discord channels: hermes-dev 1499234022725779619, diary 1499234070897365043, notify 1499234114694418674.
§
Environment: /tmp is mounted noexec — native Python extensions (lxml, numpy) fail to dlopen from venvs created there. Use /opt/data or other exec-allowed path for venvs.
§
Environment: uv available at /usr/local/bin/uv; pip, ensurepip, python3-venv, sudo are all absent. Docker client present but daemon not running.
§
Environment: Python 3.13.5 system install, externally-managed (PEP 668).
§
Web extraction fallback: Scrapling (`stealthy_fetch`/`fetch`) is used as a fallback when `web_extract` fails on JS-required or bot-protected sites (e.g. X, Cloudflare). Installed at `/opt/data/scrapling-venv` with `PLAYWRIGHT_BROWSERS_PATH=/opt/data/playwright-browsers`. Do NOT use for static lightweight pages due to browser startup overhead (~seconds, +hundreds MB RAM).
§
When user says "put in tasks" / "タスクに入れる", they mean Google Tasks. Not backlog.md, not Obsidian Tasks, not todo lists — always Google Tasks. Same correction was given before. Do not ask again.