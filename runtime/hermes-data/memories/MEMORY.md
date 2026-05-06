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
User expects confirmation before installing software or running setup; dislikes unrequested installations. Values content density in creative outputs — must be self-explanatory to first-time viewers.
§
Google Workspace OAuth redirect URI customized to `https://yanelmo.net/hermes-auth` in setup.py for mobile auth. Must also be registered in Google Cloud Console authorized redirect URIs.
§
Terminal commands require user approval in this environment. GitHub operations MUST use gh CLI or MCP server APIs exclusively. Never use curl/browser for GitHub releases or pages when gh/MCP alternative exists.
§
Environment: /tmp is noexec — venvs under /opt/data. uv at /usr/local/bin/uv. Python 3.13.5, PEP 668. pip/ensurepip/python3-venv/sudo absent. Docker client present, daemon not running.
§
Research vault: /opt/data/obsidian/obsidian_git/research-vault/. Japanese docs preferred; dislikes katakana loanword overload. delegation model: kimi-k2.6.