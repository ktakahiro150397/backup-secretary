# サーバー置換・構築・運用ランブック

旧 `backup-secretary` をreworkへ置き換え、Hermes 2インスタンスとOpenVikingを構築・更新する手順です。

置換時は旧環境を削除せず、ディレクトリごと退避します。最初にreworkのコードと空のenvファイルだけを配置し、秘密情報と既存データは後から選別して追加します。

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

置換作業では次を守ります。

- reworkのデプロイ対象refをremoteへpushしてから作業する
- `docker compose down` に `--volumes` を付けない
- 旧runtimeや旧 `.env` を新環境へ一括コピーしない
- キー投入前はHermesを起動しない
- 旧環境は切り戻しとデータ選別が終わるまで削除しない

## 1. 旧環境からreworkへの置換

### 1.1 変数設定

サーバー上のBashで実行します。reworkがmainへマージ済みなら `origin/main` を指定します。ブランチを直接検証する場合は、push済みのremote refへ変更します。

```bash
export REPO_DIR="$HOME/repo/backup-secretary"
export DEPLOY_REF="origin/main"
export CUTOVER_ID="$(date -u +%Y%m%dT%H%M%SZ)"
export LEGACY_DIR="$HOME/repo/backup-secretary.legacy-$CUTOVER_ID"
export RECORD_DIR="$HOME/repo/cutover-records/$CUTOVER_ID"
```

### 1.2 置換前インベントリ

旧環境を変更する前に状態を確認・記録します。envの値やファイル本文は表示しません。

```bash
cd "$REPO_DIR"
git status --short --branch
git rev-parse HEAD
docker compose config --services
docker compose ps
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
find runtime -maxdepth 3 -type f -printf '%p\n' 2>/dev/null | sort
test ! -e "$LEGACY_DIR"
```

Compose外の関連コンテナも確認します。現行サーバーでは `dashboard` が旧Compose定義外で稼働していたため、所有元と停止要否を判断してから進みます。

```bash
mkdir -p "$RECORD_DIR"
git status --short --branch > "$RECORD_DIR/git-status.txt"
git rev-parse HEAD > "$RECORD_DIR/git-head.txt"
docker compose ps > "$RECORD_DIR/compose-ps.txt"
docker ps --format '{{json .}}' > "$RECORD_DIR/docker-ps.jsonl"
find runtime -maxdepth 3 -type f -printf '%p\n' 2>/dev/null \
  | sort > "$RECORD_DIR/runtime-files.txt"
```

次を確認してから停止します。

- サーバー固有の追跡対象変更を把握している
- bind mountとnamed volumeの保存先を把握している
- Compose外コンテナの扱いを決めている
- `LEGACY_DIR` が存在しない

### 1.3 旧環境の停止と丸ごと退避

ここからメンテナンス時間です。

```bash
cd "$REPO_DIR"
docker compose down
docker compose ps
```

Compose外コンテナは所有元を確認せず停止・削除しません。旧リポジトリはGit管理外データごと退避します。

```bash
cd "$HOME/repo"
mv backup-secretary "$(basename "$LEGACY_DIR")"
test -d "$LEGACY_DIR/.git"
test ! -e "$REPO_DIR"
chmod -R go-rwx "$LEGACY_DIR"
```

### 1.4 reworkコードの新規配置

```bash
OLD_REMOTE="$(git -C "$LEGACY_DIR" remote get-url origin)"
git clone --no-checkout "$OLD_REMOTE" "$REPO_DIR"
cd "$REPO_DIR"
git fetch --prune origin
git checkout --detach "$DEPLOY_REF"
git status --short --branch
git rev-parse HEAD
```

mainへマージ済みのものを通常運用する場合は、追跡ブランチへ切り替えます。

```bash
git switch main
git pull --ff-only
```

reworkのComposeに `hermes-main`、`hermes-owashota`、`openviking` だけが定義されていることを確認します。

```bash
grep -E '^  [a-zA-Z0-9_-]+:$' compose.yaml
```

### 1.5 コードと空envだけを準備

Composeは `env_file` の存在を検証するため、キー未設定でもexampleからファイルを作ります。旧envはコピーしません。

```bash
cp .env.example .env
install -m 600 runtime/openviking/.env.example runtime/openviking/.env
install -m 600 runtime/main/hermes-data/.env.example runtime/main/hermes-data/.env
install -m 600 runtime/owashota/hermes-data/.env.example runtime/owashota/hermes-data/.env
sed -i "s/^HERMES_UID=.*/HERMES_UID=$(id -u)/" .env
sed -i "s/^HERMES_GID=.*/HERMES_GID=$(id -g)/" .env
docker compose config --quiet
docker compose config --services
```

ここが「reworkコードだけ置換済み、キーとデータは未投入」の安全な停止点です。秘密情報をまだ用意しない場合は、コンテナを起動せずここで終了します。

### 1.6 切り戻し

新環境に問題がある場合は、新Composeを停止して新ディレクトリを退避し、旧ディレクトリを元へ戻します。

```bash
cd "$REPO_DIR"
docker compose down
cd "$HOME/repo"
mv backup-secretary "backup-secretary.failed-$CUTOVER_ID"
mv "$(basename "$LEGACY_DIR")" backup-secretary
cd "$REPO_DIR"
docker compose up -d
docker compose ps
```

旧環境を削除するのは、新環境の安定稼働、キー再発行、必要データの移行、バックアップ確認がすべて完了した後の別作業とします。

## 2. 通常更新時にmainをサーバーへ反映

サーバー固有の未コミット変更がないことを確認してから実行します。

```bash
git switch main
git pull --ff-only
docker compose config --quiet
```

## 3. 秘密情報の後日投入

存在しない場合だけコピーします。既存ファイルを上書きしません。

```bash
test -f .env || cp .env.example .env
test -f runtime/openviking/.env || install -m 600 runtime/openviking/.env.example runtime/openviking/.env
test -f runtime/main/hermes-data/.env || install -m 600 runtime/main/hermes-data/.env.example runtime/main/hermes-data/.env
test -f runtime/owashota/hermes-data/.env || install -m 600 runtime/owashota/hermes-data/.env.example runtime/owashota/hermes-data/.env
```

旧 `.env` を一括コピーせず、必要な値だけを手動で転記または再発行します。

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

値を表示せず、ファイルの存在と権限だけを確認します。

```bash
stat -c '%a %n' runtime/openviking/.env \
  runtime/main/hermes-data/.env \
  runtime/owashota/hermes-data/.env
```

## 4. OpenViking起動

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

## 5. account初回作成

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

## 6. サブプロファイルuser追加

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

## 7. user別CLI config

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

## 8. 既存データの後日移行

新環境が空の状態で安定してから、必要なデータだけを種類ごとに移します。旧runtime全体やOpenViking workspace全体を新runtimeへ上書きコピーしません。

推奨順序:

1. `SOUL.md` と安定した `config.yaml` の差分を目視で反映
2. 必要なprofile定義を追加
3. memoryをuser別CLI config経由で投入
4. 必要なskillsを互換性確認後に追加
5. knowledgeやworkspaceファイルを用途別に追加

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

投入元、対象user、実施日時を移行記録へ残します。

## 9. Hermes設定

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

## 10. 起動・反映

OpenVikingのaccount作成とユーザーAPI key設定が完了するまでHermesを起動しません。

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

## 11. 疎通・分離確認

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

## 12. APIキー再発行

古いキーは即時無効になります。

```bash
make ov-regenerate-key ACCOUNT=hermes-main NAME=coder
```

新キーをprofileの `.env` と対応CLI configへ反映後:

```bash
make restart-main
```

## 13. 通常更新

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
