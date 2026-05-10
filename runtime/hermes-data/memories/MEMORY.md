Hermes code repo: ktakahiro150397/backup-secretary; issue backlog at /opt/data/plans/hermes-issues-backlog.md; create issues only with approval.
§
Hermes and house-expense run in separate Docker containers on the same server.
§
Obsidian vault: ktakahiro150397/obsidian_git; clone at /opt/data/obsidian/obsidian_git; writes to main branch.
§
Discord channels: hermes-dev, diary, notify, webhook (IDs in config). Modifying `allowed_channels`/`free_response_channels` breaks all channel responses — verify before editing. Gateway restarts: request `/restart` from user first, self-execute only after persistent refusal.
§
Scrapling fallback venv: /opt/data/scrapling-venv, PLAYWRIGHT_BROWSERS_PATH=/opt/data/playwright-browsers. For JS/bot-protected sites only; avoid for static pages.
§
X/Twitter URLs: web_extract fails → load x-tweet-extractor skill FIRST. scrapling-fallback is last-resort. Check domain-specific skills first.
§
"put in tasks" / "タスクに入れる" = Google Tasks. Not backlog.md/Obsidian Tasks/todo lists.
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
§
YouTube動画の情報取得は、web_searchの断片に頼らず、必ずbrowser_navigateでYouTubeページを直接開いてタイトル・チャンネル名・説明文を正確に取得する。