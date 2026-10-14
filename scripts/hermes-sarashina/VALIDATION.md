# Validation — 2026-10-15 JST

Scope: the existing `hermes-owashota` service in `backup-secretary`, starting
from repository revision `2042775c76eb69404cc4900cea2f81c38b2b235c`.
Runtime image:
`sha256:3aac4b05df4e7e51f36a10be7e5e09fe0354c6f7a3faf6ac4bac5b5022721193`.
The image has no `/opt/hermes/.git`, so no runtime Git revision is asserted.

## Confirmed

- All 18 offline compatibility/lifecycle tests passed in the actual container
  as UID/GID 1000:1000. These include native Hermes provider resolution,
  AIAgent with its real file tool and SDK stream, feature-configuration
  preservation, failed-probe isolation, pacing, restore order and orphan handling.
- All 3 independent memory-only key-handoff tests passed.
- Live greeting: HTTP 200, valid nonempty assistant response, requested model.
- Live function call: HTTP 200 SSE, valid function name/arguments.
- Live tool result: HTTP 200 SSE, completed answer using the locally computed
  sum. The probe used only fixed, non-confidential inputs; response bodies and
  credentials were not saved.
- Final switch: controller active, named-profile gateway PID 873728, original
  gateway absent. Discord connected at `2026-10-14T15:06:27Z`; its writer PID
  and start time matched the live named gateway. No Discord test post was sent.
- Real rollback via `control.py restore` returned to Codex, including a fresh
  Discord connection; reactivation then returned the bot to Sarashina.
- Original config, SOUL, `.env` and auth hashes matched the preparation baseline.
  Toolsets, platform toolsets, MCP, memory, auxiliary models, approvals,
  delegation, STT, terminal, Discord and compression settings were preserved.
  Shared-resource symlinks still resolved to their original resources.
- The other bot remained running/healthy. Windows-native Hermes was not changed.
- An exact-value scan of 44 regular profile/support files found no Sarashina
  credential. Original credentials and the operator's Windows file were neither
  changed nor included in this source bundle.

## Runtime fixes established by the checks

1. HTTP success and a valid response replace the old exact-`OK` greeting check.
   Activation additionally gates on the streamed tool/result round trip.
2. The installed s6 text PID parser fails on `up (pid N pgid N)`. Explicitly
   checking `s6-svstat -o pid` against the live Hermes PID and writing the native
   planned-stop marker allowed the old gateway to stop with exit code 0.
3. A terminated controller can remain as a zombie until reaped. `/proc` start
   time alone incorrectly treated it as alive and blocked retries; Z/X states
   are now rejected.
4. The controller starts its child with `gateway run --no-supervise` so the
   current Hermes CLI does not redirect it into an unregistered s6 service.

## Limits

- Discord connection is verified; end-to-end Discord message/reply testing was
  not performed. Individual production tools, delegation and memory retrieval
  were not all exercised against Sarashina.
- Original local conversation history remains in the original database. The
  named profile has its own database and retains existing shared resources.
- The key is memory-only on the server. Container/host restart does not restore
  Sarashina unattended; inspect status and use the credential-free restore
  command or a new approved key handoff.
- The pre-existing presence plugin continues to display Codex usage.
- The source commit intentionally excludes runtime data/configuration, logs,
  credentials, and the three pre-existing modified configuration/SOUL paths.

API references checked on 2026-10-14:
[chat completions](https://docs.sarashina.ai/api-reference/chat-completions),
[models](https://docs.sarashina.ai/models),
[rate limits](https://docs.sarashina.ai/rate-limits).
