Hermes code repo: ktakahiro150397/backup-secretary; issue backlog at /opt/data/plans/hermes-issues-backlog.md; create issues only with approval.
§
Hermes and house-expense run in separate Docker containers on the same server.
§
Obsidian vault: ktakahiro150397/obsidian_git; clone at /opt/data/obsidian/obsidian_git; writes to main branch.
§
Discord: hermes-dev/diary/notify/webhook. Changing allowed_channels breaks responses — verify before editing. Gateway restart requires user `/restart` first. Use discord-table-image skill for table images.
§
Scrapling fallback venv: /opt/data/scrapling-venv, PLAYWRIGHT_BROWSERS_PATH=/opt/data/playwright-browsers. For JS/bot-protected sites only; avoid for static pages.
§
X/Twitter: use x-tweet-extractor skill first, scrapling-fallback last. Pixiv API: `illust_detail` gives `total_view`/`total_bookmarks`/`total_comments`; `user_detail` gives `total_follow_users`. Follower count and follow date are NOT exposed by Pixiv APIs.
§
"put in tasks" / "タスクに入れる" = Google Tasks. Not backlog.md/Obsidian Tasks/todo lists.
§
Confirm before installing software. Creative outputs must be self-explanatory to first-time viewers.
§
Google Workspace OAuth redirect URI customized to `https://yanelmo.net/hermes-auth` in setup.py for mobile auth. Must also be registered in Google Cloud Console authorized redirect URIs.
§
Terminal requires approval. GitHub: use gh CLI or MCP APIs only, never curl/browser.
§
/tmp noexec; venvs in /opt/data. uv at /usr/local/bin/uv. Python 3.13.5, PEP 668. No pip/sudo. Docker client only (no daemon).
§
Research vault: /opt/data/obsidian/obsidian_git/research-vault/. JP docs preferred. Model: kimi-k2.6.
§
YouTube: always browser_navigate to the page directly; never rely on web_search snippets for title/channel/description.
§
§
CRITICAL: Discord table rule. When generating any table-like data for Discord, ALWAYS use the `discord-table-image` skill to produce an image. Never output raw Markdown tables. User explicitly gets angry when this is ignored.