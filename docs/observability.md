# Hermes OpenTelemetry integration

This repository exports approved content-free Hermes telemetry to the separate `local-obserbablity` stack. It does not own an observability backend or expose Grafana.

## Pinned build inputs

| Component | Pin |
|---|---|
| Hermes base image | `nousresearch/hermes-agent@sha256:00f57d79b2b20745a4f2c47bd26135f0473100ca23103ffc3eb3f89f3f6cef50` |
| `briancaffey/hermes-otel` | release 0.11.0, commit `0180c5e63b9d035ee0754d9a0d75c3499a8def26` |
| OpenTelemetry Python packages | 1.44.0 |
| PyYAML | 6.0.3 |

The Compose defaults for the other external service images are digest-pinned as well; environment overrides must remain pinned in production.

The Docker build clones exactly the reviewed plugin commit into Hermes' bundled plugin directory and installs dependencies into `/opt/hermes/.venv`. No running container installs plugin code or Python packages.

## Data and network path

```text
Hermes main / owashota
  -> external Docker network local-observability-net
  -> http://otel-router:4318
  -> separate observability router
       -> private storage
       -> shared Hermes-only storage
```

Hermes never connects directly to shared Grafana or storage. The external network must be created by the standalone observability project before Compose validates or starts these services.

## Privacy configuration

Each instance mounts its own reviewed plugin YAML. Environment variables repeat the critical privacy values as defense in depth:

- input/output previews off;
- conversation history off;
- full prompts and responses off;
- general log capture off;
- sender ID on for per-Discord-user accounting;
- live dashboard storage off;
- synchronous session-end flush off to prevent collector downtime blocking a turn.

Only stable operational metadata, model/provider, token counts, timings, errors, tool names/outcomes, instance identity, and Discord sender identity are approved. Never commit a real sender ID, raw trace export, or ID-to-name mapping.

## Build and enable

Prepare the standalone observability project first. Then:

```bash
docker compose build hermes hermes-owashota
./scripts/enable-hermes-otel.sh
docker compose up -d --no-build hermes hermes-owashota
```

The enable helper uses Hermes' supported `plugins enable --no-allow-tool-override` command. It creates one local rollback copy of each existing Hermes config before changing only the plugin allow-list. It does not install into a running container.

Do not execute this against a dirty or unreviewed checkout. Production rollout must use the separate Phase 1 branch/worktree and must preserve the currently running data mounts and secret environment.

## Verification

Before real Discord gate H7:

```bash
docker compose run --rm --no-deps hermes hermes plugins list
docker compose run --rm --no-deps hermes-owashota hermes plugins list
```

Verify `hermes_otel` is enabled and reports no load error. Then inspect startup logs without copying trace payloads. Both gateways must stay healthy when the collector is stopped.

At H7, use one real non-sensitive Discord turn per instance and verify on the owner-only observability side:

- `service.name=backup-secretary-hermes`;
- `service.namespace=backup-secretary`;
- `service.instance.id=main` or `owashota`;
- `hermes.sender.id` and `user.id=discord:<same sender>`;
- root `agent` span contains rolled-up token attributes;
- prompt, response, conversation history, tool arguments/results, and general logs are absent.

The same approved Hermes traces must appear in private and shared storage, while personal Codex traces must remain absent from shared storage.

## Rollback

Stop only the two gateways, disable the plugin using Hermes' supported CLI or restore each local `config.yaml.phase1-otel-backup`, and recreate the prior pinned image. Do not delete the backup until both gateways answer normally.

The observability stack can be stopped independently. Its unavailability is not a reason to roll back Hermes unless a reproduced plugin defect affects message handling.
