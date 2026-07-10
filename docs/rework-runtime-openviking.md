# Rework: runtime split + OpenViking memory

## Goal

This branch reorganizes Hermes runtime management so that:

- `hermes-main` is the personal always-on Discord gateway.
- `hermes-owashota` is the family/friends Discord gateway.
- Each instance has separate `/opt/data` runtime data.
- Git synchronizes stable configuration, skills, and knowledge.
- OpenViking synchronizes long-term context for the personal Hermes instances.
- Sessions, state databases, logs, secrets, and built-in `memories/` are not synchronized by Git.

## Sync model

### Git

Git is for stable, human-managed files:

- `runtime/main/hermes-data/SOUL.md`
- `runtime/main/hermes-data/config.yaml`
- `runtime/owashota/hermes-data/SOUL.md`
- `runtime/owashota/hermes-data/config.yaml`
- `skills/`
- `knowledge/`
- `compose.yaml`
- `scripts/`
- `docs/`

### OpenViking

OpenViking is for shared long-term context:

- personal user context
- project context extracted from conversations
- cross-session/cross-machine recall for personal Hermes

`hermes-main` connects to OpenViking by default. `hermes-owashota` does not.

This Compose stack uses the official prebuilt OpenViking image from GitHub Container Registry:

```text
ghcr.io/volcengine/openviking:latest
```

OpenViking persistent state is mounted at `/app/.openviking` inside the container.

### Not synchronized

Do not synchronize these:

- `.env`
- `auth.json`
- `state.db*`
- `sessions/`
- `logs/`
- `cache/`
- `home/`
- `.local/`
- `memories/`
- `gateway_state.json`

## First setup

```bash
cp .env.example .env
mkdir -p runtime/main/hermes-data runtime/owashota/hermes-data runtime/openviking workspace
```

Set `HERMES_UID` and `HERMES_GID` in `.env` to your host user IDs on Linux/WSL:

```bash
sed -i "s/^HERMES_UID=.*/HERMES_UID=$(id -u)/" .env
sed -i "s/^HERMES_GID=.*/HERMES_GID=$(id -g)/" .env
```

Run Hermes setup for each gateway when needed:

```bash
docker compose --profile setup run --rm setup-main
docker compose --profile setup run --rm setup-owashota
```

Put secrets in the runtime-local `.env` files, not in repository `.env`:

```text
runtime/main/hermes-data/.env
runtime/owashota/hermes-data/.env
```

## OpenViking setup

Start OpenViking and initialize config:

```bash
docker compose up -d openviking
docker compose exec openviking openviking-server init
docker compose exec openviking openviking-server doctor
curl http://127.0.0.1:1933/health
```

The official image starts the HTTP server on port `1933` and also includes Web Studio at `/studio`. `OPENVIKING_WITH_BOT=0` disables the bundled `vikingbot` gateway for this stack.

Then start the stack:

```bash
make up
```

## Routine operations

Update Git files and sync skills without restarting Hermes:

```bash
make update
# or
scripts/hupdate
```

Use this for `skills/` and `knowledge/` changes.

Deploy with image pull, Hermes rebuild, and restart:

```bash
make deploy
# or
scripts/hdeploy
```

Use this after changing `SOUL.md`, `config.yaml`, `.env`, `compose.yaml`, or Dockerfiles.

## Main PC / WSL CLI

Clone this repository on WSL. Then use:

```bash
scripts/hcoder
```

The script:

1. pulls this repository when the working tree is clean;
2. syncs `skills/` into the local coder Hermes data dir;
3. bootstraps `SOUL.md` and `config.yaml` from `runtime/main/hermes-data` when missing;
4. connects to OpenViking via `OPENVIKING_ENDPOINT`;
5. starts `hermes chat`.

Set server endpoint before use:

```bash
export OPENVIKING_ENDPOINT=http://your-server:1933
```

Use Tailscale/VPN for access outside the server host.
