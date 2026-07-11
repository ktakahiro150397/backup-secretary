# サーバー構築・運用ランブック

mainブランチでHermes 2インスタンスとOpenVikingを構築・更新する手順です。

## 0. 前提

このランブックのコマンド例は Bash 前提です。サーバー上では Linux / WSL のシェルで実行します。

```bash
cd ~/repo/backup-secretary
git status --short
git branch --show-current
```

秘密情報とruntimeデータはGit管理されません。特に次を失わないでください。

```text
runtime/openviking/.env
runtime/openviking/ov.conf
runtime/openviking/workspace/
runtime/main/hermes-data/.env
runtime/main/hermes-data/profiles/*/.env
runtime/owashota/hermes-data/.env
```

既存サーバーでは通常運用時に `make ov-init` を再実行しません。これは新規runtimeの初期化時だけ使います。

## 1. mainをサーバーへ反映

サーバー固有の未コミット変更がないことを確認してから実行します。

```bash
git switch main
git pull --ff-only
docker compose config --quiet
```

## 2. 初回env作成

存在しない場合だけコピーします。既存ファイルを上書きしません。

```bash
test -f .env || cp .env.example .env
test -f runtime/openviking/.env || cp runtime/openviking/.env.example runtime/openviking/.env
test -f runtime/main/hermes-data/.env || cp runtime/main/hermes-data/.env.example runtime/main/hermes-data/.env
test -f runtime/owashota/hermes-data/.env || cp runtime/owashota/hermes-data/.env.example runtime/owashota/hermes-data/.env
```

`runtime/openviking/.env`:

```dotenv
OPENVIKING_ROOT_API_KEY=<root管理キー>
GEMINI_API_KEY=<embedding/VLM用キー>
```

`runtime/main/hermes-data/.env`:

```dotenv
OPENVIKING_ACCOUNT=hermes-main
OPENVIKING_USER=hermes-main
OPENVIKING_AGENT=hermes-main
OPENVIKING_API_KEY=<hermes-mainユーザーキー>
```

`runtime/owashota/hermes-data/.env`:

```dotenv
OPENVIKING_ACCOUNT=hermes-owashota
OPENVIKING_USER=hermes-owashota
OPENVIKING_AGENT=hermes-owashota
OPENVIKING_API_KEY=<hermes-owashotaユーザーキー>
```

LLMやDiscordの秘密情報も各Hermesの `.env` に置きます。rootの `.env` には秘密情報を置きません。

## 3. OpenViking起動

新規runtimeだけ:

```bash
make ov-init
make ov-doctor
```

既存runtime:

```bash
docker compose up -d openviking
make ov-doctor
```

root管理configを作ります。

```bash
make ov-root-config
make ov ARGS="config validate"
make ov ARGS="admin list-accounts --sudo"
```

## 4. account初回作成

未作成の場合だけ実行します。

```bash
make ov ARGS="admin create-account --admin hermes-main hermes-main --sudo"
make ov ARGS="admin create-account --admin hermes-owashota hermes-owashota --sudo"
```

作成時に表示されるユーザーAPIキーは再表示できません。直ちに対応するHermesの `.env` へ保存します。

```bash
make ov ARGS="admin list-accounts --sudo"
make ov ARGS="admin list-users hermes-main --sudo"
make ov ARGS="admin list-users hermes-owashota --sudo"
```

## 5. サブプロファイルuser追加

`hermes-main` account内へ `coder` userを追加する例です。

```bash
make ov-provision-user ACCOUNT=hermes-main NAME=coder
```

期待構成:

```text
hermes-main/
├── hermes-main  admin
└── coder        user
```

発行キーを `runtime/main/hermes-data/profiles/coder/.env` へ保存します。

```dotenv
OPENVIKING_ACCOUNT=hermes-main
OPENVIKING_USER=coder
OPENVIKING_AGENT=coder
OPENVIKING_API_KEY=<coderユーザーキー>
```

確認:

```bash
make ov ARGS="admin list-users hermes-main --sudo"
```

## 6. user別CLI config

root configでuser memoryを扱わず、対象userごとのconfigを作ります。API keyをシェル履歴へ残さないよう、Bash の対話入力で進めます。

`hermes-main` user:

```bash
read -rsp "OpenViking API key for hermes-main: " OV_USER_KEY
echo
printf '%s' "$OV_USER_KEY" | docker compose exec -T openviking \
  /app/.venv/bin/ov config add custom \
  --name hermes-main \
  --url http://127.0.0.1:1933 \
  --api-key-stdin \
  --account hermes-main \
  --user hermes-main \
  --activate --force
unset OV_USER_KEY
make ov ARGS="config validate"
```

`hermes-main` account内の `coder` user:

```bash
read -rsp "OpenViking API key for hermes-main/coder: " OV_USER_KEY
echo
printf '%s' "$OV_USER_KEY" | docker compose exec -T openviking \
  /app/.venv/bin/ov config add custom \
  --name hermes-main-coder \
  --url http://127.0.0.1:1933 \
  --api-key-stdin \
  --account hermes-main \
  --user coder \
  --activate --force
unset OV_USER_KEY
make ov ARGS="config validate"
```

`hermes-owashota` user:

```bash
read -rsp "OpenViking API key for hermes-owashota: " OV_USER_KEY
echo
printf '%s' "$OV_USER_KEY" | docker compose exec -T openviking \
  /app/.venv/bin/ov config add custom \
  --name hermes-owashota \
  --url http://127.0.0.1:1933 \
  --api-key-stdin \
  --account hermes-owashota \
  --user hermes-owashota \
  --activate --force
unset OV_USER_KEY
make ov ARGS="config validate"
```

確認:

```bash
make ov ARGS="config list"
make ov ARGS="config switch hermes-main-coder"
make ov ARGS="config validate"
```

## 7. 既存記憶の初回投入

初回に一度だけ実行します。再投入すると重複する可能性があります。

現在の主な投入元:

```text
runtime/main/hermes-data/memories/USER.md
runtime/main/hermes-data/profiles/coder/memories/MEMORY.md
```

coder memory:

```bash
make ov ARGS="config switch hermes-main-coder"
make ov ARGS="config validate"
docker compose exec -T openviking /bin/sh -c \
  'content=$(cat); exec /app/.venv/bin/ov add-memory "$content"' \
  < runtime/main/hermes-data/profiles/coder/memories/MEMORY.md
make ov ARGS="wait --timeout 180"
make ov ARGS="find '<MEMORY.md内の固有語>' --context-type memory"
```

hermes-main user memory:

```bash
make ov ARGS="config switch hermes-main"
make ov ARGS="config validate"
docker compose exec -T openviking /bin/sh -c \
  'content=$(cat); exec /app/.venv/bin/ov add-memory "$content"' \
  < runtime/main/hermes-data/memories/USER.md
make ov ARGS="wait --timeout 180"
make ov ARGS="find '<USER.md内の固有語>' --context-type memory"
```

検索語は各ファイルに実在する固有語へ置き換えます。

## 8. Hermes設定

各 `config.yaml` で次を有効化します。

```yaml
memory:
  memory_enabled: true
  user_profile_enabled: true
  provider: openviking
```

対象:

```text
runtime/main/hermes-data/config.yaml
runtime/main/hermes-data/profiles/coder/config.yaml
runtime/owashota/hermes-data/config.yaml
```

profileでは `SOUL.md`、`config.yaml`、`.env.example`をGit管理し、実キーを含む `.env` は管理しません。

## 9. 起動・反映

```bash
make pull
make up
make ps
```

mainだけ反映:

```bash
make restart-main
docker compose logs --tail=200 openviking hermes-main
```

対話実行:

```bash
make hermes-main
```

## 10. 疎通・分離確認

```bash
make ov-doctor
make ps
```

coder側:

```bash
make ov ARGS="config switch hermes-main-coder"
make ov ARGS="find '<coder固有語>' --context-type memory"
```

hermes-main側:

```bash
make ov ARGS="config switch hermes-main"
make ov ARGS="find '<main固有語>' --context-type memory"
```

確認基準:

- coder固有記憶はcoder configで取得できる
- main固有記憶はmain configで取得できる
- 相手側の固有記憶は取得できない
- `admin list-users hermes-main --sudo` では2 userと表示される
- Hermesの各profileからも対応する固有記憶を回答できる

## 11. APIキー再発行

古いキーは即時無効になります。

```bash
make ov-regenerate-key ACCOUNT=hermes-main NAME=coder
```

新キーをprofileの `.env` と対応CLI configへ反映後:

```bash
make restart-main
```

## 12. 通常更新

初回構築後はOpenViking初期化、account作成、memory初回投入を繰り返しません。

```bash
git status --short
git switch main
git pull --ff-only
docker compose config --quiet
make pull
make up
make ov-doctor
make ps
```

設定変更時だけ対象を再起動します。
