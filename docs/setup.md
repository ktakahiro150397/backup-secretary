# セットアップ

このブランチは、Hermes 2インスタンスと OpenViking だけを扱います。

## 構成

- `hermes-main`: 個人用
- `hermes-owashota`: 身内向け
- `openviking`: 長期 memory サーバー

SearXNG、Redis、skills、knowledge、既存memory移行、Obsidian連携はこのreworkのスコープ外です。

## envファイルの考え方

このブランチでは `.env` を2種類に分けます。

```text
.env                                  # Docker Compose用。repo rootに置く。
runtime/main/hermes-data/.env          # hermes-main用。Git管理しない。
runtime/owashota/hermes-data/.env      # hermes-owashota用。Git管理しない。
```

root `.env` には秘密情報を置きません。  
Discord token、LLM API key、OpenViking API key、OpenViking namespace は各Hermesインスタンス直下の `.env` に置きます。

詳細は `docs/env.md` を参照してください。

## 初期化

runtimeを作り直す場合は、先に既存containerを停止します。

```bash
docker compose down
rm -rf runtime workspace
git restore runtime workspace
```

`git restore` でGit管理中の `config.yaml`、`SOUL.md`、`.env.example`、`.gitkeep` を戻します。その後、実際のenvを作成します。

```bash
mkdir -p runtime/main/hermes-data runtime/owashota/hermes-data runtime/openviking workspace
cp .env.example .env
cp runtime/main/hermes-data/.env.example runtime/main/hermes-data/.env
cp runtime/owashota/hermes-data/.env.example runtime/owashota/hermes-data/.env
```

> `runtime` を削除すると認証情報、session、実行時に生成されたHermes設定、OpenViking dataも消えます。

## UID/GID

Hermes公式imageは、rootで起動したあと、`HERMES_UID` / `HERMES_GID` を使ってcontainer内の `hermes` ユーザーをホスト側のUID/GIDへ自動的に合わせます。

Composeの `user:` は指定しません。s6-overlayの初期化処理が必要なため、`user:` を指定すると起動に失敗します。

Linux / WSLでは、root `.env` を現在のユーザーに合わせます。

```bash
sed -i "s/^HERMES_UID=.*/HERMES_UID=$(id -u)/" .env
sed -i "s/^HERMES_GID=.*/HERMES_GID=$(id -g)/" .env
```

macOSでBSD版 `sed` を使う場合:

```bash
sed -i '' "s/^HERMES_UID=.*/HERMES_UID=$(id -u)/" .env
sed -i '' "s/^HERMES_GID=.*/HERMES_GID=$(id -g)/" .env
```

この方式により、Hermes自身の初期化処理を壊さずに、bind mountされた `runtime/*/hermes-data` の所有者をホストユーザーへ合わせられます。

### 対応環境

- Linux: 対応
- WSL2 + Docker Desktop: 対応
- macOS + Docker Desktop: 対応
- Windows PowerShellからDocker Desktopを直接使う構成: WSL2経由を推奨

## 設定編集

以下を編集します。

```text
.env
runtime/main/hermes-data/.env
runtime/owashota/hermes-data/.env
```

最低限、2つのインスタンス用 `.env` で以下を別値にしてください。

```text
OPENVIKING_ACCOUNT
OPENVIKING_USER
OPENVIKING_AGENT
OPENVIKING_API_KEY
```

## OpenViking

OpenVikingは公式Docker imageを使います。

```text
ghcr.io/volcengine/openviking:latest
```

永続化先は以下です。

```text
runtime/openviking -> /app/.openviking
```

初期化します。

```bash
make ov-init
make ov-doctor
```

Docker版OpenVikingはコンテナ内で `0.0.0.0:1933` をbindするため、OpenViking側の `ov.conf` には `root_api_key` を設定してください。

### OpenViking CLI

コンテナ内の `ov` CLIはMakeターゲットから実行できます。

```bash
make ov
make ov ARGS="health"
make ov ARGS="status"
make ov-config
make ov-tui
```

`make ov-config` で管理用CLI configを作成します。接続先はコンテナ内から見たOpenViking自身なので `http://127.0.0.1:1933`、root API keyはOpenVikingサーバーに設定した値を使います。CLI configは `runtime/openviking` 配下へ永続化されます。

### accountとuser

記憶を確実に分離するため、Hermesインスタンスごとにaccountを分けます。

```text
hermes-main account
└── hermes-main user

hermes-owashota account
└── hermes-owashota user
```

管理用configを有効にしてaccountを作成します。

```bash
make ov ARGS="admin create-account hermes-main --sudo"
make ov ARGS="admin create-account hermes-owashota --sudo"
make ov ARGS="admin list-accounts --sudo"
```

ユーザーAPI keyは作成・再発行時だけ表示されます。後から同じkeyを表示することはできません。紛失した場合は再発行し、古いkeyは無効になります。

```bash
make ov ARGS="admin regenerate-key hermes-main hermes-main --sudo"
make ov ARGS="admin regenerate-key hermes-owashota hermes-owashota --sudo"
```

発行されたkeyを各Hermesの `.env` に保存し、対象コンテナを再起動します。

### TUIでデータを確認する

管理用root keyのconfigでは、ユーザーnamespaceの内容は表示されません。`make ov-config` でHermesユーザーごとのCLI configを追加します。

```text
Name: hermes-main
URL: http://127.0.0.1:1933
API Key: hermes-main userのAPI key
Account: hermes-main
User: hermes-main
```

対象configへ切り替えてTUIを起動します。

```bash
make ov ARGS="config list"
make ov ARGS="config switch hermes-main"
make ov ARGS="config validate"
make ov-tui
```

`hermes-owashota`も同様に別configを作成します。TUIが空に見える場合は、まずactive configのaccount/userが閲覧対象と一致しているか確認してください。

## Hermes

Hermesは2つの別コンテナとして起動します。

```bash
make pull
make up
```

必要ならsetupを個別に実行します。

```bash
make setup-main
make setup-owashota
```

ローカル端末から対話CLIを起動できます。

```bash
make hermes-main
make hermes-owashota
```

一時コンテナは終了時に削除されますが、設定とsessionは各 `runtime/<instance>/hermes-data` に残ります。

各インスタンスの秘密情報は、Git管理しないruntime側に置きます。

```text
runtime/main/hermes-data/.env
runtime/owashota/hermes-data/.env
```

## memory分離

OpenViking接続情報は、各インスタンス直下の `.env` で分けます。

```text
runtime/main/hermes-data/.env
  OPENVIKING_ACCOUNT=hermes-main
  OPENVIKING_USER=hermes-main
  OPENVIKING_AGENT=hermes-main
  OPENVIKING_API_KEY=...

runtime/owashota/hermes-data/.env
  OPENVIKING_ACCOUNT=hermes-owashota
  OPENVIKING_USER=hermes-owashota
  OPENVIKING_AGENT=hermes-owashota
  OPENVIKING_API_KEY=...
```

最低限、`account` / `user` / `agent` はインスタンスごとに分けます。  
API keyも別にできる場合は必ず別にします。

このブランチでは「記憶が混ざらないこと」の検証を優先し、既存memoryやskillsの初期投入は行いません。
