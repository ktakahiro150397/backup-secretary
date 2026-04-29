User can transfer files from Windows PowerShell/WSL path to the server with scp, e.g. from \\wsl.localhost\Ubuntu\home\takahiro\repo\backup-secretary\tools\twitter: `scp ".\personalization.ja.0001.jsonl" yanelmoserver:~/repo/backup-secretary/runtime/hermes-data/_twitter_data/`.
§
User's Hermes/assistant code is managed in GitHub repo ktakahiro150397/backup-secretary.
§
User runs Hermes and the house-expense app on the same server in separate Docker containers.
§
Hermes issue backlog is saved at /opt/data/plans/hermes-issues-backlog.md; do not create GitHub issues from it without explicit user approval.
§
User is considering an assistant persona/name: fun to talk to + reliable, easy to call/type, hiragana 2–3 chars. Leading candidate: 「みお」; alternatives: 「りん」「なぎ」「ゆい」. Details to be considered in a future issue.
§
Hermes model-routing preference: offload Web-heavy/token-heavy research, URL reading, comparison material gathering, changelog/docs summaries, and rough large-log analysis to Gemma subagents first (currently Gemma 31B proven; Gemma 26B A4B worth testing). Keep GPT-5.5 as main orchestrator for final judgment, synthesis, response shaping, complex design decisions, and risky side-effect actions.
§
Google Tasks API v1 in user's Hermes setup supports list/create/complete/delete after adding tasks scope, but due times set in the app are not exposed via API; treat Google Tasks as date-only and use Calendar for exact times.