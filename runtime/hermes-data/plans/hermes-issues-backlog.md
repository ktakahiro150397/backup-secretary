# Hermes / backup-secretary issue backlog

Purpose: durable scratch backlog for Hermes-related GitHub issue candidates discussed with the user. Do not create GitHub issues from this file without explicit user approval.

## Count

- Solid issue candidates: 14
- Including softer candidates: 17

## Solid issue candidates

1. GitHub authentication setup for Hermes
   - Set up `gh auth login` or inject `GH_TOKEN` into the Hermes container.
   - Required before automated backup-secretary issue creation/management.

2. Google Workspace / Calendar / Tasks integration
   - Enable Hermes to use Google Workspace tools.
   - Current blocker observed earlier: Google token was not authenticated.

3. Store stock market reports in Google Sheets
   - Keep Discord summaries, but also append/update structured rows in Sheets.
   - Preferred shape: one row per day, with morning / midday / close report columns.

4. Gateway attachment ingestion for Discord/Telegram
   - Save incoming attachments locally from the gateway.
   - Pass agent-visible metadata/path: local path, filename, MIME, size, sha256, source platform/message.

5. Async voice chat over messaging platforms
   - Voice message -> STT -> LLM -> TTS voice reply.
   - Prefer async Telegram/Discord-style voice messages before realtime calls.

6. Obsidian Markdown + Git diary storage
   - Store diary entries as Markdown with YAML frontmatter.
   - Use existing Obsidian diary repo if mounted/cloned.
   - Pull/write/commit/push flow; do not store full diary text in Hermes memory.

7. Inject recent cron deliveries into next conversation context
   - Cron responses delivered to a chat should be visible as recent contextual metadata in subsequent user turns for the same destination.
   - Fixes cases like user replying "ごめん寝てた" after a reminder while assistant cannot see the reminder.

8. Write-And-Forget capture
   - Let the user casually dump notes/tasks/ideas.
   - Route to retrievable storage, diary, task list, issue draft, etc.

9. house-expense MCP integration
   - Wrap existing Gemini function-calling tools as MCP tools.
   - Expose aggregated household expense data to Hermes, not raw private data by default.

10. Useful/fun proactive Hermes notifications
    - Market, AI news, household ops, dev/repo watch, spending anomalies.
    - Feedback loop via lightweight reactions/natural comments.

11. Add local Gemma delegate target
    - Add a local Gemma model as a cheaper/private delegate target.
    - Use for suitable subagent tasks.

12. Whitelist Git backup for Hermes state
    - Track config, SOUL.md, selected memories, custom skills, cron definitions, plans.
    - Exclude secrets, auth, state.db, sessions, logs, cache, cron outputs.

13. Codex CLI usage/rate-limit tool
    - Surface usage/rate-limit information from Codex/OpenAI internal usage endpoints when authenticated.
    - Never log or expose bearer tokens.

14. Hermes character / SOUL.md design
    - Design Hermes' character/persona as a first-class configurable concept.
    - Include name candidates, response quirks, tone, teasing/banter boundaries, Japanese style, and per-profile personality switching.
    - Review how much belongs in `SOUL.md` versus profile config, memory, or skills.
    - Goal: make Hermes feel consistent and useful without becoming a corporate drone or unstable roleplay blob.

## Softer candidates

15. Private/local-only Hermes instance separation
    - Separate container/profile/instance for sensitive personal data.
    - Treat profile as convenience separation, not a hard security boundary.

16. MemOS / MemTensor integration investigation
    - Evaluate whether external memory OS/backend is useful for Hermes long-term memory.

17. Hermes self-evolution / DSPy + GEPA investigation
    - Evaluate NousResearch/hermes-agent-self-evolution ideas.
    - Especially skill optimization and prompt/tool-description evolution.

## Created on GitHub

Created with explicit user approval on 2026-04-28. Titles/bodies were translated to Japanese after creation.

- Skipped: `GitHub authentication setup for Hermes` — already handled separately via `GH_CONFIG_DIR=/opt/data/.config/gh`.
- #4 Google Workspace / Calendar / Tasks 連携 — https://github.com/ktakahiro150397/backup-secretary/issues/4
- #5 株式市場レポートをGoogle Sheetsへ保存する — https://github.com/ktakahiro150397/backup-secretary/issues/5
- #6 Discord / Telegram添付ファイルをGatewayで取り込む — https://github.com/ktakahiro150397/backup-secretary/issues/6
- #7 Messaging Platformで非同期ボイスチャットする — https://github.com/ktakahiro150397/backup-secretary/issues/7
- #8 Obsidian Markdown + Gitで日記を保存する — https://github.com/ktakahiro150397/backup-secretary/issues/8
- #9 直近のcron配信を次の会話コンテキストに注入する — https://github.com/ktakahiro150397/backup-secretary/issues/9
- #10 Write-And-Forget capture — https://github.com/ktakahiro150397/backup-secretary/issues/10
    - **ステータス:** 実装済み・テスト済み、PRマージ済み。スキル `write-and-forget-capture` として利用可能。Backlog コメント: 2026-04-29 解決を確認。
- #11 house-expense MCP連携 — https://github.com/ktakahiro150397/backup-secretary/issues/11
- #12 便利で楽しいHermesの能動通知 — https://github.com/ktakahiro150397/backup-secretary/issues/12
- #13 ローカルGemmaをdelegate targetに追加する — https://github.com/ktakahiro150397/backup-secretary/issues/13
- #14 Hermes stateをGitで安全にバックアップするwhitelist運用 — https://github.com/ktakahiro150397/backup-secretary/issues/14
- #15 Codex CLIの使用量 / rate limit確認ツール — https://github.com/ktakahiro150397/backup-secretary/issues/15
- #16 Hermes character / SOUL.md設計 — https://github.com/ktakahiro150397/backup-secretary/issues/16
- #17 private / local-only Hermes instance分離 — https://github.com/ktakahiro150397/backup-secretary/issues/17
- #18 MemOS / MemTensor連携調査 — https://github.com/ktakahiro150397/backup-secretary/issues/18
- #19 Hermes self-evolution / DSPy + GEPA調査 — https://github.com/ktakahiro150397/backup-secretary/issues/19

## Next actions

- **2026-05-04**: Update Hermes Docker base image (`nousresearch/hermes-agent:latest`) and rebuild container to get the `openai-codex` image_gen plugin.
  - `docker compose pull` → `docker compose build --no-cache` → `docker compose up -d`
  - Codex OAuth already configured; no extra auth needed after rebuild.

## Notes

- GitHub issue creation must not happen automatically. Ask the user first.
- If the user says ambiguous phrases like "issueね", clarify whether they want a draft or actual GitHub issue creation.
- Long-running or side-effecting operations should be confirmed before execution.
