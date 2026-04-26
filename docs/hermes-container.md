# Hermes Agent コンテナ運用メモ

## 目的

Hermes Agent の PoC を、ホスト権限に近い実行を避けながら開始する。

- Hermes gateway / dashboard / CLI setup を Docker Compose で起動する
- 書き込み可能なホスト領域を `runtime/hermes-data` と `workspace` に限定する
- Discord、cron、memory、MCP、ブラウザ系など Hermes 公式イメージに含まれる PoC 機能を使う
- 設定項目と変更時の注意点を明文化する

## 前提

- Docker Engine または Docker Desktop
- Docker Compose v2
- Discord bot token や LLM API key

Hermes 公式 Docker イメージは、設定、API key、sessions、skills、memories、cron、logs を `/opt/data` に保存する。公式ドキュメントでは gateway は `gateway run` で起動する。dashboard は API key と config を表示するため、コンテナ内では `dashboard --host 0.0.0.0 --insecure` で起動し、Docker の port bind を `127.0.0.1` に限定してホストローカルからだけアクセスする。

参考:

- https://hermes-agent.nousresearch.com/docs/user-guide/docker/
- https://hermes-agent.nousresearch.com/docs/user-guide/configuration/
- https://hermes-agent.nousresearch.com/docs/user-guide/security/

## 初期セットアップ

```bash
cp .env.example .env
sed -i "s/^HERMES_UID=.*/HERMES_UID=$(id -u)/" .env
sed -i "s/^HERMES_GID=.*/HERMES_GID=$(id -g)/" .env
mkdir -p runtime/hermes-data workspace
docker compose build hermes
docker compose --profile setup run --rm setup
```

Linux/WSL では、初回起動前に `.env` の `HERMES_UID` / `HERMES_GID` をホストユーザーに合わせる。通常は `id -u` と `id -g` の結果を指定する。この値は `docker compose build hermes` でローカル派生イメージに焼き込み、コンテナ内の `hermes` ユーザーを最初からホスト UID/GID に合わせる。

`HERMES_UID` / `HERMES_GID` を変えた場合は、次の順で作り直す。

```bash
docker compose down
docker compose build --no-cache hermes
docker compose up -d hermes
```

セットアップ wizard で provider、model、Discord gateway などを設定する。secret は `runtime/hermes-data/.env` に保存する運用を基本にし、リポジトリ直下の `.env` には Compose 用の非 secret 設定だけを置く。この Compose 構成では `env_file: .env` は使わず、`.env` は Compose の変数補間にだけ使う。

`docker compose --profile setup run --rm setup` を使わず手動で設定する場合は、一度 Hermes を起動して `runtime/hermes-data/.env` を生成してから、そのファイルに Discord token や LLM API key を記載する。

```bash
docker compose up -d hermes
vim runtime/hermes-data/.env
docker compose restart hermes
```

Discord bot 運用の最小例:

```env
DISCORD_BOT_TOKEN=...
DISCORD_ALLOWED_USERS=123456789012345678
DISCORD_ALLOW_ALL_USERS=false
GATEWAY_ALLOW_ALL_USERS=false
```

`DISCORD_ALLOWED_USERS` は Discord のユーザー名ではなく数値の User ID を指定する。複数人ならカンマ区切りにする。

セットアップ後、必要に応じて `config/hermes-config.poc.yaml` の値を `runtime/hermes-data/config.yaml` に反映する。最低限、PoC では次を維持する。

```yaml
terminal:
  backend: local
  cwd: /workspace
  env_passthrough: []
approvals:
  mode: manual
```

`backend: local` はホストではなく Hermes コンテナ内の local 実行を意味する。この構成では `/var/run/docker.sock` を渡さないため、Hermes からホスト Docker を操作できない。

## 起動

Gateway:

```bash
docker compose up -d hermes
docker compose logs -f hermes
```

Dashboard も使う場合:

```bash
docker compose --profile dashboard up -d
```

Dashboard URL:

```text
http://127.0.0.1:9119
```

dashboard は認証が堅牢ではないため、`HERMES_DASHBOARD_BIND=0.0.0.0` に変更しない。

CLI を一時的に開く場合:

```bash
docker compose --profile cli run --rm cli
```

`cli` profile は `bash` を開く。Hermes CLI を使う場合は venv を有効化する。

```bash
source /opt/hermes/.venv/bin/activate
hermes --help
```

停止:

```bash
docker compose down
```

## 権限境界

Compose では次を設定している。

| 項目 | 設定 | 意図 |
|---|---|---|
| `read_only` | `false` | Hermes 公式イメージの entrypoint とブラウザ/CLI 実行の互換性を優先し、PoC では無効にする |
| bind mount | `/opt/data`, `/workspace` のみ | Hermes の永続データと PoC 作業領域だけをホストに公開する |
| `cap_drop` | `ALL` | Linux capability を一度すべて落とす |
| `cap_add` | `CHOWN`, `SETGID`, `SETUID` | 公式 entrypoint が `/opt/data` の ownership 調整と `hermes` ユーザーへの降格を行うための最小権限 |
| `no-new-privileges` | `true` | setuid 等による権限昇格を抑止する |
| `pids_limit` | `256` | プロセス増殖を制限する |
| `tmpfs` | `/tmp`, `/var/tmp`, `/run` | 一時領域をサイズ制限付きで提供する |
| ports | `127.0.0.1` bind | gateway/dashboard をローカル公開に留める |
| healthcheck | `hermes gateway run` プロセス確認 | Discord gateway は HTTP port を listen しない構成があるため、プロセス生存で確認する |

`workspace` は Hermes がファイル生成や検証に使う許可ディレクトリ。ホストの任意ディレクトリを追加で mount しない。必要になった場合は、読み取り専用なら `:ro` を付け、書き込み可なら用途別の専用ディレクトリを作る。

## 設定項目

| 変数 | 既定値 | 説明 |
|---|---:|---|
| `HERMES_IMAGE` | `backup-secretary/hermes-agent:local` | 起動するローカル派生イメージ |
| `HERMES_BASE_IMAGE` | `nousresearch/hermes-agent:latest` | ローカル派生イメージの元にする Hermes 公式 image。PoC 固定後は tag または digest 固定を推奨 |
| `HERMES_DATA_DIR` | `./runtime/hermes-data` | `/opt/data` に mount する永続データディレクトリ |
| `HERMES_WORKSPACE_DIR` | `./workspace` | `/workspace` に mount する許可作業ディレクトリ |
| `HERMES_UID` | `1000` | ローカル派生イメージ内 `hermes` ユーザーの UID。ホスト側で `runtime/hermes-data` を読めるように `id -u` に合わせる |
| `HERMES_GID` | `1000` | ローカル派生イメージ内 `hermes` グループの GID。ホスト側で `runtime/hermes-data` を読めるように `id -g` に合わせる |
| `HERMES_READ_ONLY` | `false` | root filesystem を読み取り専用にするか。PoC では `false` を維持する |
| `HERMES_GATEWAY_BIND` | `127.0.0.1` | gateway API の bind address |
| `HERMES_GATEWAY_PORT` | `8642` | gateway API の host port |
| `HERMES_DASHBOARD_BIND` | `127.0.0.1` | dashboard の bind address |
| `HERMES_DASHBOARD_PORT` | `9119` | dashboard の host port |
| `HERMES_CPU_LIMIT` | `2` | gateway container の CPU 上限 |
| `HERMES_MEMORY_LIMIT` | `4g` | gateway container のメモリ上限 |
| `HERMES_SHM_SIZE` | `1g` | Playwright/Chromium 用 shared memory |
| `HERMES_DASHBOARD_CPU_LIMIT` | `0.5` | dashboard container の CPU 上限 |
| `HERMES_DASHBOARD_MEMORY_LIMIT` | `512m` | dashboard container のメモリ上限 |

Hermes 本体の secret は原則 `runtime/hermes-data/.env` で管理する。リポジトリ直下の `.env` は Docker Compose の設定用で、`docker compose config` に値が展開表示されるため、Discord token や LLM API key を置かない。また、Compose 用 `.env` を `env_file` としてコンテナへ渡すと `HERMES_UID/GID` が runtime に渡って公式 entrypoint の `usermod` が発火するため、この構成では使わない。

| secret 例 | 用途 |
|---|---|
| `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | LLM provider |
| `DISCORD_BOT_TOKEN` | Discord gateway |
| `DISCORD_ALLOWED_USERS`, `GATEWAY_ALLOWED_USERS` | 利用者 allowlist |

`DISCORD_ALLOW_ALL_USERS=true` や `GATEWAY_ALLOW_ALL_USERS=true` は private PoC でも避ける。Discord はユーザー ID allowlist で開始する。

## 運用チェック

```bash
docker compose config
docker compose pull
docker compose up -d hermes
docker compose ps
docker compose logs --tail 100 hermes
```

PoC 受け入れ時には次を確認する。

- Discord の許可ユーザーだけが応答を得られる
- 定時通知の cron が想定時刻に動く
- memory の参照、保存抑止、削除が操作できる
- Hermes のファイル生成先が `workspace` または `/opt/data` に収まる
- MCP を使う場合、公開 tool と渡す env を最小にする

## 禁止事項

- `/var/run/docker.sock` を mount しない
- ホストの home directory や repository root 全体を mount しない
- `.env`、`runtime/hermes-data/.env`、OAuth token、Discord token を commit しない
- gateway/dashboard port を直接 Internet に公開しない
- `approvals.mode: off` や YOLO mode を常用しない

## ローカルで `runtime/hermes-data` が見えない場合

`runtime/hermes-data` が `nobody:nogroup` の `700` になっている場合、Hermes の entrypoint が `/opt/data` をコンテナ内 UID `10000` に `chown` した結果、ホスト側 UID とずれている。

`.env` に次を設定し、ローカル派生イメージを build してから Hermes を作り直す。

```bash
HERMES_UID=$(id -u)
HERMES_GID=$(id -g)
HERMES_READ_ONLY=false
```

反映:

```bash
docker compose down
docker compose build --no-cache hermes
docker compose up -d hermes
ls -la runtime/hermes-data
```

既に `runtime/hermes-data` が壊れた所有権になっていて削除してよい場合は、コンテナ停止後に作り直す。

```bash
docker compose down
docker run --rm --entrypoint sh -v "$PWD/runtime:/host" nousresearch/hermes-agent:latest -lc 'rm -rf /host/hermes-data && mkdir -p /host/hermes-data && chown '"$(id -u):$(id -g)"' /host/hermes-data && chmod 755 /host/hermes-data'
docker compose build hermes
docker compose up -d hermes
```
