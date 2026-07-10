# envファイル整理

このブランチでは `.env` を2種類に分けます。

```text
.env                                  # Docker Compose用。repo rootに置く。
runtime/main/hermes-data/.env          # hermes-main用。Git管理しない。
runtime/owashota/hermes-data/.env      # hermes-owashota用。Git管理しない。
```

結論として、**root `.env` に秘密情報を置かない**。  
Discord token、LLM API key、OpenViking API key、memory namespace は各Hermesインスタンス直下の `.env` に置きます。

## 1. root `.env`

場所:

```text
.env
```

作成:

```bash
cp .env.example .env
```

役割:

- Docker image名
- ホスト側のmount path
- 公開port
- 各Hermesインスタンスが読む `.env` の場所
- OpenViking containerの基本設定

書いてよいもの:

```text
HERMES_IMAGE
OPENVIKING_IMAGE
HERMES_MAIN_DATA_DIR
HERMES_OWASHOTA_DATA_DIR
HERMES_WORKSPACE_DIR
OPENVIKING_DATA_DIR
HERMES_MAIN_ENV_FILE
HERMES_OWASHOTA_ENV_FILE
HERMES_MAIN_GATEWAY_BIND
HERMES_MAIN_GATEWAY_PORT
HERMES_OWASHOTA_GATEWAY_BIND
HERMES_OWASHOTA_GATEWAY_PORT
OPENVIKING_BIND
OPENVIKING_PORT
OPENVIKING_WITH_BOT
```

書かないもの:

```text
Discord token
LLM API key
OpenViking API key
OpenViking account/user/agent
Hermes provider secret
OAuth token
```

root `.env` は、**コンテナをどう起動するか** だけを決めます。

## 2. `runtime/main/hermes-data/.env`

場所:

```text
runtime/main/hermes-data/.env
```

作成:

```bash
cp runtime/main/hermes-data/.env.example runtime/main/hermes-data/.env
```

役割:

- 個人用Hermes `hermes-main` の秘密情報
- 個人用HermesのOpenViking namespace
- 個人用HermesのOpenViking API key
- 個人用HermesのLLM / Discord token

最低限設定するもの:

```text
OPENVIKING_ACCOUNT=personal
OPENVIKING_USER=yanelmo
OPENVIKING_AGENT=hermes-main
OPENVIKING_API_KEY=replace-me-main
```

LLMやDiscordの実トークンは、Hermes setupや利用するproviderに合わせてこのファイルへ追加します。

## 3. `runtime/owashota/hermes-data/.env`

場所:

```text
runtime/owashota/hermes-data/.env
```

作成:

```bash
cp runtime/owashota/hermes-data/.env.example runtime/owashota/hermes-data/.env
```

役割:

- 身内向けHermes `hermes-owashota` の秘密情報
- 身内向けHermesのOpenViking namespace
- 身内向けHermesのOpenViking API key
- 身内向けHermesのLLM / Discord token

最低限設定するもの:

```text
OPENVIKING_ACCOUNT=owashota
OPENVIKING_USER=owashota
OPENVIKING_AGENT=hermes-owashota
OPENVIKING_API_KEY=replace-me-owashota
```

`hermes-main` と同じ値にしないでください。  
特に `OPENVIKING_ACCOUNT` / `OPENVIKING_USER` / `OPENVIKING_AGENT` / `OPENVIKING_API_KEY` は分けます。

## 4. OpenVikingの `ov.conf`

場所:

```text
runtime/openviking/ov.conf
```

このファイルは `openviking-server init` で作られます。Git管理しません。

OpenViking Docker imageはコンテナ内で `0.0.0.0:1933` をbindするため、`ov.conf` の `server.root_api_key` は必ず設定します。

概念的には以下です。

```json
{
  "server": {
    "root_api_key": "your-secret-root-key"
  }
}
```

Hermes側の `OPENVIKING_API_KEY` には、このOpenViking側で受け付けるAPI keyを入れます。  
複数API keyを発行できる場合は、`hermes-main` と `hermes-owashota` で別keyにします。

## 5. 起動前チェック

最低限、以下3つの `.env` が存在する状態にします。

```bash
test -f .env
test -f runtime/main/hermes-data/.env
test -f runtime/owashota/hermes-data/.env
```

まとめて作るなら:

```bash
cp .env.example .env
cp runtime/main/hermes-data/.env.example runtime/main/hermes-data/.env
cp runtime/owashota/hermes-data/.env.example runtime/owashota/hermes-data/.env
```

## 6. 判断基準

迷ったら以下で判断します。

```text
ホスト側の起動設定か？
  -> root .env

そのHermesインスタンスだけの秘密情報か？
  -> runtime/<instance>/hermes-data/.env

OpenVikingサーバー自体の設定か？
  -> runtime/openviking/ov.conf

Gitで共有したい安定設定か？
  -> config.yaml / SOUL.md
```
