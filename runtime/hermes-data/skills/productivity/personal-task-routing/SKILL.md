---
name: personal-task-routing
description: Capture casual user intentions from chat, classify them into Google Tasks, Google Calendar events, Hermes reminders, or GitHub issues, and add follow-up/reschedule checks. Use when the user says things like “〜したいな”, “忘れそう”, “あとでやる”, “買わないと”, or asks the assistant to manage tasks/reminders/issues on their behalf.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [tasks, reminders, calendar, github-issues, follow-up, productivity, planning]
    related_skills: [google-workspace, github-issues, hermes-agent]
---

# Personal Task Routing

Use this skill when the user casually expresses an intention, obligation, reminder, purchase, appointment, follow-up, or implementation idea and wants the assistant to manage it instead of making them open a task app.

## Trigger conditions

Load this skill when the user says or implies:

- “〜したいな” / “〜しないとな” / “忘れそう” / “あとでやる”
- They want a reminder, task, calendar entry, or follow-up check
- They want Hermes to decide whether something should be a task, calendar event, reminder, or GitHub issue
- They mention a real-world errand, purchase, appointment, household/admin task, implementation idea, or project work
- They want task follow-up such as “終わってなかったら聞いて” or “飛ばしてたらリスケ”

## Core principle

The assistant should reduce friction: capture the intent from natural chat, propose the next concrete action, classify it, and manage follow-up. Do not make the user manually maintain a task system.

## Routing rules

### Google Tasks

Use Google Tasks when the item should be visible on the user's phone or has completion state.

Good fit:

- Errands, shopping, calls, appointments to book, forms to submit
- Things the user may need to see while away from the PC
- Items with a due date but no exact time block
- Items likely to need rescheduling
- “Bring coupon”, “buy glasses”, “call clinic”, “submit document”

Recommended task shape:

```text
Title: short imperative action
Due: YYYY-MM-DD
Notes:
- Context needed at execution time
- Constraints/coupons/links/choices
- Any follow-up rule
```

### Google Calendar

Use Calendar when time is fixed or the user needs time blocked.

Good fit:

- Events, appointments, meetings, school/family schedules
- Travel/departure windows
- Tasks that require a specific time block
- Recurring scheduled obligations

Always use JST for this user unless otherwise specified. Calendar creation/deletion requires explicit approval with a preview.

### Hermes reminder / cron

Use Hermes reminders when the reminder is primarily about Hermes/Discord/PC workflow or lightweight prompting.

Good fit:

- “At 22:00 remind me to gh login in the Hermes container”
- Prompting the user to authorize, review, or continue a Hermes workflow
- AI-generated reports and Discord-native nudges
- Short-lived reminders before Google integration exists

Make cron prompts self-contained: include context, desired wording/tone, delivery target, and what to ask next.

### GitHub issue

Use GitHub issues when the item is heavy, technical, multi-step, or needs later implementation/review by the user, Codex, or another agent.

Good fit:

- Feature implementation
- Research/design decisions
- MCP integration work
- Repo/config changes
- Anything needing acceptance criteria

Issue body should include context, goal, implementation notes, acceptance criteria, and “Codex-facing” instructions if the user plans to delegate.

### Durable issue backlog capture

Use this when the user says things like “issue案まとめて覚えておいて”, “後でissue化する”, “忘れないで”, or asks to add a new idea to an issue backlog without explicitly approving GitHub issue creation.

Default behavior:

1. Do **not** create GitHub issues yet.
2. Save the detailed backlog to a durable local Markdown file, preferably under a plans/backlog path such as `plans/*issue*backlog*.md` or the active workspace's `.hermes/plans/`.
3. Save only a short index pointer in Hermes memory, e.g. “Project issue backlog is saved at <path>”. Do not store the full backlog in standard memory.
4. Include counts, categories, and enough detail to draft GitHub issues later.
5. Update the same backlog file when the user adds more candidates.
6. Ask before external side effects: GitHub issue creation, git commit/push, cron changes, or long-running commands.

Lightweight design/preference memos:

- If the user asks to “メモっといて” a compact, stable preference or design direction for a future issue — e.g. assistant persona/name constraints, product direction, naming candidates — save a concise Hermes memory entry instead of creating a backlog file.
- Keep the memory as a short factual summary with enough detail to reconstruct the later issue: goal, key constraints, leading candidates, and “details to be considered in a future issue”.
- Do not create a GitHub issue from this signal alone. Treat “詳細はissueで検討” / “あとでissue化” as capture-only unless the user explicitly says to create it now.
- If the note grows beyond a few bullets, promote it to the durable Markdown backlog pattern above and store only the pointer in Hermes memory.

This pattern is for durable capture, not execution. It bridges casual chat and later formal GitHub issue creation.

## Classification heuristic

When the user says “〜したいな”:

1. Identify whether it is an action, scheduled event, implementation project, or vague desire.
2. Suggest a concrete next action.
3. Ask or infer whether to capture it.
4. Route:
   - quick + real-world + due date/completion → Google Tasks
   - fixed time/date → Google Calendar
   - Hermes/Discord-only nudge → Hermes reminder
   - multi-step/technical/project → GitHub issue
5. Add follow-up if useful.

If unclear, make a reasonable default and state it briefly. Do not over-clarify low-stakes items.

## Follow-up pattern

For actionable tasks, create a follow-up check when the user benefits from accountability.

Typical follow-up wording:

```text
〇〇、終わってます？まだなら次いつやるかだけ決めましょう。
```

Follow-up timing:

- Same-day errand: evening of the due date
- Weekend/holiday errand: that evening or next morning
- Deadline task: halfway point and/or due date morning
- Technical issue: no follow-up unless explicitly requested, or attach to issue instead

If unfinished, ask for a new target date/time and reschedule. Avoid guilt-trippy phrasing.

## Confirmation rules

Respect user’s plan-mode preference:

- Before file creation, file editing, script execution, long-running commands, or mutating external actions, give a brief plan and get approval unless the user explicitly just asked for that exact action.
- Casual routing phrases like “issueね”, “タスク行き”, or “あとでやるやつ” are ambiguous capture signals, not permission to execute. Ask whether they want a draft/summary or actual external creation.
- For Google writes and Calendar event creation/deletion, always show a preview and ask approval.
- For harmless Hermes reminders requested directly, creation can be immediate only when the request is explicit and low-risk.
- For GitHub issues, draft the issue body or concise issue plan first; create the GitHub issue only after explicit approval such as “作って”, “作成してOK”, or “GitHubに登録して”. If auth is missing, never probe credentials with mutating commands; summarize the issue plan and wait.

## Example

User:

> メガネのつるが歪んでこめかみ痛い。JINSで10%オフクーポン使って次の休日に買いたい。忘れそう。

Classification:

- Google Tasks: because it is an errand, phone-visible, completion-based, and may need rescheduling.
- Optional Calendar: only if the user picks a concrete visit time.
- Hermes follow-up: until Google Tasks integration exists, schedule a reminder and a same-day evening follow-up.

Suggested task:

```text
Title: JINSでメガネを買う
Due: 2026-04-29
Notes:
- 10%オフクーポンを持っていく
- 候補: フレームレス or 上半分フレームの細め長方形
- フレームレスは納期10日くらい
- こめかみ痛いのでフィット調整も頼む
Follow-up: 当日夕方に未完了確認
```

## Write-And-Forget capture pattern

Use this pattern when the user wants to write casual fragments over time and have the assistant later connect them into suggestions, tasks, calendar events, issues, or reminders.

Examples:

```text
Earlier note: 子どもに踏まれてメガネがボロボロ
Later note: GW中に使えるJINSの10%オフクーポンもらった
Suggestion: JINSクーポン使ってメガネ買い替えるのどうですか？Tasksに入れます？
```

Design principles:

- Treat casual notes as possible unresolved flags, not immediate tasks.
- Link later notes to prior unresolved notes when there is a useful action opportunity.
- Ask lightly before turning a suggestion into an external action.
- Store enough context for execution, but avoid saving every passing thought.
- Close, dismiss, or suppress notes when the user rejects them or they expire.
- Prefer semi-automatic capture first ("これ保存しときます？") before fully automatic capture, to tune noise.

### Store design guidance

Do not use Hermes standard memory as the main store for Write-And-Forget life/task logs. Standard memory is for stable preferences, durable rules, and environment facts. It is too small and too globally injected for high-volume note/event state.

Recommended initial architecture:

```text
SQLite or Postgres
  notes
  entities
  note_entities
  relations
  suggestions
  actions
  followups

Search
  SQLite FTS5 initially
  optional embeddings/sqlite-vec later

LLM
  extract save-worthy notes
  classify entities/topics
  judge relationships
  draft suggestions
```

For the first practical MVP, keep it brutally local and boring:

- Store the DB under a private runtime path such as `/opt/data/waf/waf.db`, not in the Git repo.
- Provide a tiny CLI/tool surface first: `capture`, `search`, and `status`.
- Use JSON output so Hermes tools, cron jobs, and future MCP wrappers can consume it reliably.
- Use SQLite FTS5; for mixed Japanese/English short notes, prefer the `trigram` tokenizer over default `unicode61` to avoid obvious substring-search misses.
- Add a `suggestions` table early as a Phase 2 landing zone, but do not generate external writes in Phase 1.
- Test both CLI output and raw SQLite state. Also smoke-test with a temp DB path via `--db` or `WAF_DB`.

Use RDB/SQLite for status and workflow state:

- open / suggested / actioned / dismissed / closed
- due dates and expiry dates
- follow-up time
- Google Task ID / Calendar event ID / GitHub issue number
- suppression windows to avoid nagging

Knowledge graph / Mem0 / Zep / Graphiti can be future upgrades, but should not be first-line for a personal Write-And-Forget assistant. They add operational weight and still need separate workflow state. Start with SQLite + FTS5 + LLM classification; add embeddings or graph memory only when volume/relationship complexity justifies it.

## Pitfalls

- Do not put everything into Google Calendar; deadline-only items belong in Tasks.
- Do not put heavy technical work into Tasks; use GitHub issues.
- Do not rely only on Hermes reminders for errands the user may need on a phone.
- Do not dump private task context into GitHub issues unless it belongs there.
- Do not create noisy recurring reminders without a clear stop condition.
- Do not stuff transient life logs into Hermes standard memory; use a dedicated Write-And-Forget store.
- Do not start with a heavy knowledge graph stack just because it sounds agentic; SQLite + FTS5 is the sane first version.
