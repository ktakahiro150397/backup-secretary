Hermes repo: ktakahiro150397/backup-secretary; issue backlog at /opt/data/plans/hermes-issues-backlog.md; create issues only with approval.
§
Hermes and house-expense run in separate Docker containers on the same server.
§
Obsidian vault: ktakahiro150397/obsidian_git; clone at /opt/data/obsidian/obsidian_git; writes to main branch.
§
Discord: hermes-dev/diary/notify/webhook. Verify allowed_channels before editing — changes break responses. Gateway restart needs `/restart`. Use discord-table-image skill.
§
Scrapling fallback venv: /opt/data/scrapling-venv, PLAYWRIGHT_BROWSERS_PATH=/opt/data/playwright-browsers. For JS/bot-protected sites only; avoid for static pages.
§
X/Twitter: x-tweet-extractor first, scrapling-fallback last. Pixiv `illust_detail` has views/bookmarks/comments; `user_detail` has follow count. Pixiv lacks follower count and follow date.
§
"put in tasks" / "タスクに入れる" = Google Tasks. Not backlog.md/Obsidian Tasks/todo lists.
§
Confirm before installing. Creative outputs must be clear to first-time viewers.
§
Google Workspace OAuth redirect: `https://yanelmo.net/hermes-auth` (setup.py, mobile auth). Must register in Google Cloud Console redirect URIs.
§
Terminal requires approval. GitHub: gh CLI or MCP APIs only, never curl/browser.
§
/tmp noexec; venvs in /opt/data. uv at /usr/local/bin/uv. Python 3.13.5, PEP 668. No pip/sudo. Docker CLI installed but daemon unreachable (no /var/run/docker.sock access); `docker ps` returns "Cannot connect to Docker daemon".
§
Research vault: /opt/data/obsidian/obsidian_git/research-vault/. JP docs preferred. Model: kimi-k2.6.
§
YouTube: always browser_navigate directly; never rely on web_search snippets for title/channel/description.
§
§
CRITICAL: Discord tables must use discord-table-image skill. Raw Markdown tables break responses; user gets angry if ignored.
§
遊戯王OCGカード効果は記憶推論禁止。必ず /opt/data/yugioh_cards.db から正確なテキストを引用。一字一句の誤りが裁定破綻を生む。ユーザーは嘘・推論捏造を許容せず厳しく指摘する。