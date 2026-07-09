# backup-secretary

Hermes Agent runtime for personal and family/friends Discord assistants.

## Current rework branch

This branch splits runtime data by instance and introduces OpenViking as the shared long-term memory provider for personal Hermes.

- `hermes-main`: personal always-on Discord gateway
- `hermes-owashota`: family/friends Discord gateway
- `openviking`: shared long-term memory provider for personal Hermes
- `skills/`: Git-managed Hermes skills
- `knowledge/`: Git-managed stable knowledge

See [`docs/rework-runtime-openviking.md`](docs/rework-runtime-openviking.md) for setup and operation.

## Quick commands

```bash
cp .env.example .env
make up
make update
make deploy
```

Do not commit secrets or generated runtime data.
