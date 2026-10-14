# owashota: Sarashina profile and Codex recovery

## Confirmed target

- SSH host: `yanelmoserver`; container: `backup-secretary-hermes-owashota`.
- Discord bot display name: `Hermes【AIエージェント】`.
- Existing profile: container root/default, `/opt/data`, provider `openai-codex`, model `gpt-6-astra`.
- Existing supervisor: s6 service `gateway-default`; Unix UID/GID `1000:1000`.
- Candidate profile: `/opt/data/profiles/owashota-sarashina`.
- Support: `/opt/data/sarashina-support`.
- Host data: `/home/ktakahiro150397/repo/backup-secretary/runtime/owashota/hermes-data`.

The other main container and the Windows native Hermes instance are separate targets. The old inactive `iwashota-sarashina` preparation is superseded and was never activated.

## Preserved configuration

The original config, SOUL, `.env`, auth and uncommitted changes are preserved. The manifest records SHA256 checksums. Existing tools, MCP admin-procedures, `/workspace`, OpenViking memory, delegation, approvals, local STT, vision provider `opencode-go / mimo-v2.5`, plugins, skills, cron and hooks remain configured as before. Shared resources are symlinks to the existing resources. The new profile has a separate local conversation database; returning to Codex uses the original database.

Only the main provider/model/base URL, context window 128000, Sarashina model metadata and unsupported reasoning setting change. The presence plugin continues to display Codex usage.

## Compatibility and limits

The native provider uses a container-only loopback proxy at `127.0.0.1:18761/v1`; no Docker port is published. The proxy forwards exclusively to `https://api.sarashina.ai/v1/chat/completions` with `sarashina3-mini`.

Output is capped at 8000. Unsupported request parameters are removed, `max_tokens` becomes `max_completion_tokens`, tool choice defaults explicitly to `auto`, and an object forcing a function becomes the selected function plus `required`. Text, function calls, tool results and SSE are supported. Direct image payloads are rejected; the existing vision provider remains configured. Requests share spacing of at least 10.1 seconds; HTTP 429 adds a 60.1 second cooldown. Other applications using the same key still count toward the provider's 6 requests/minute limit.

References: [models](https://docs.sarashina.ai/models), [chat completions](https://docs.sarashina.ai/api-reference/chat-completions), [rate limits](https://docs.sarashina.ai/rate-limits).

## Approved data scope

The owner approved the existing-feature context transfer, including system/SOUL/skill instructions, Discord conversation history, OpenViking memory, tool outputs, delegation inputs/results, local transcription text and existing vision-model results. The old local database itself is not copied. This data can include personal or confidential material. Discord test posts are not authorized and must not be sent.

The proxy accepts only the owner's Sarashina bearer credential. It rejects known existing credential values and private-key material in the request body. Headers and bodies are never logged. This guard does not replace the owner's data-scope decision.

## Approved key handoff

The owner authorized using the existing key for this owashota switch. The default input is `owashota-sarashina\.env` beside the Windows helper; on 2026-10-14 the actual file was `owashota-sarashina.env` beside it. Supply that path with `-EnvFile`. Only the credential helper reads its contents. Never print the value, include it in command arguments or logs, or add the file to Git. Code bundles use an explicit allowlist and exclude all credential files.

Run the approved helper in PowerShell:

```powershell
& 'C:\Users\Takahiro\Documents\Codex\2026-10-14\task\Submit-OwashotaSarashinaKey.ps1' -EnvFile 'C:\Users\Takahiro\Documents\Codex\2026-10-14\task\owashota-sarashina.env'
```

This helper reads the dedicated file and sends its value through existing encrypted SSH stdin to `key_entry.py`. No key is put in command arguments or written on the server. It returns promptly after acknowledgement. The task holds the key in memory for at most 30 minutes while waiting. After offline validation, send the nonsecret `proceed` signal. The holder performs the approved synthetic probes and activation. A failed probe keeps Codex running and permits retry using the same in-memory key until expiry. Only safe response metadata is saved. No exact greeting wording is required.

Key-holder status (no secret input/output):

```powershell
ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes yanelmoserver 'docker exec --user 1000:1000 backup-secretary-hermes-owashota /opt/hermes/.venv/bin/python /opt/data/sarashina-support/key_entry.py status'
```

Do not rerun the superseded `Enter-OwashotaSarashinaKey.ps1` instructions. The dedicated Windows credential file remains owner-managed and is neither deleted nor changed. The live gateway/proxy necessarily retain the key in process memory while active. No Sarashina credential is added to the server `.env`, auth store or profile config.

```powershell
ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes yanelmoserver 'docker exec --user 1000:1000 backup-secretary-hermes-owashota /opt/hermes/.venv/bin/python /opt/data/sarashina-support/key_entry.py proceed'
```

## Status and activation checks

```powershell
ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes yanelmoserver 'docker exec --user 1000:1000 backup-secretary-hermes-owashota /opt/hermes/.venv/bin/python /opt/data/sarashina-support/control.py status'
```

Activation verifies prepared checksums, same Unix identity, no duplicate candidate and zero active Codex agents. Before stopping `gateway-default`, it requires HTTP 2xx with a valid nonempty assistant response, a streamed function call with valid arguments, and a streamed final answer using the locally computed tool result. The only tool exercised by the live wire probe adds the fixed integers 2 and 3; no external action occurs. The offline suite additionally exercises Hermes itself with its real file tool and SDK stream. It then starts the named profile and restores Codex if the new process exits or activation fails. Report API success, gateway PID and Discord platform connection independently. Discord status must come from the current gateway writer; no test post is necessary.

## Return to Codex and recovery

No key input is needed:

```powershell
ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes yanelmoserver 'docker exec --user 1000:1000 backup-secretary-hermes-owashota /opt/hermes/.venv/bin/python /opt/data/sarashina-support/control.py restore'
ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes yanelmoserver 'docker exec --user 1000:1000 backup-secretary-hermes-owashota /opt/hermes/.venv/bin/python /opt/data/sarashina-support/control.py status'
```

The controller stops the named Sarashina child, closes the proxy and starts the original s6 service. Original config/SOUL/auth/.env need no restoration. If a turn is still shutting down, `shutdown-pending` waits instead of starting duplicate gateways. The same recovery action handles a validated orphan named-profile PID; conflicting original/named PID identity is refused.

The server never persists the Sarashina key, so unattended Sarashina restart after container/host restart is intentionally unavailable. The candidate's initial desired state is stopped. After a restart or forced controller exit, inspect status and run `restore`; do not assume automatic Codex recovery in every crash scenario. Re-entering Sarashina requires another owner-started handoff if its runtime key has gone.
